from qiskit.circuit import CommutationChecker, QuantumRegister
from zac.ds.architecture import Architecture
from multiq.configuration import MultiQConfig
from qiskit.circuit.commutation_library import StandardGateCommutations
from qiskit.circuit.quantumcircuit import QuantumCircuit
from qiskit.dagcircuit.dagcircuit import DAGCircuit
from qiskit.converters.circuit_to_dag import circuit_to_dag
from qiskit import transpile
from qiskit.converters.dag_to_circuit import dag_to_circuit
from qiskit.dagcircuit.dagnode import DAGOpNode, DAGInNode, DAGOutNode
from math import ceil, floor
from json import load, dump
from multiq.compiler.tile import Tile
from typing import DefaultDict
import numpy as np
# import random
import copy
import logging
from typing import Any, List
from qiskit.qasm3 import loads, dumps

logger = logging.getLogger("multiq")


class Planner:

    input_circuits: list[QuantumCircuit] = []
    input_dags: list[DAGCircuit] = []
    # For each input circuit this stores the list of execution layers
    input_layers: list[list[Any]] = []
    circuit_files: list[str] = []  # List of input circuit file names

    def __init__(self, config: MultiQConfig):

        self.config = config
        self.util_weight = config.util_weight
        self.perf_weight = config.perf_weight
        self.grid_rows = config.grid_rows
        # self.grid_cols = config.grid_cols
        self.tiles: List[Tile] = []

        if sum([config.util_weight, config.perf_weight]) != 1:
            logging.warning("Weights must sum to 1.")
            # raise ValueError("Planner score weights must sum to 1.")

    def set_input_circuits(self, input_circuits: list[str], optimization_level: int = 3) -> None:

        for i in input_circuits:
            circuit = QuantumCircuit.from_qasm_file(i)
            circuit = transpile(circuit, basis_gates=[
                                'cz', 'rz', 'ry', 'rx'], optimization_level=optimization_level)
            dag = circuit_to_dag(circuit)
            self.circuit_files.append(i)
            self.input_circuits.append(circuit)
            self.input_dags.append(dag)
            self.input_layers.append(self._split_DAG_into_execution_layers(
                dag, self.config.layer_split_window))

    def _fetch_window_from_zero(self, array, window) -> list[Any]:
        # Calculate the end index for the current window
        end_index = window

        # If the window extends beyond the array, adjust it
        if end_index > len(array):
            return copy.deepcopy(array[0:len(array)])
        else:
            return copy.deepcopy(array[0:end_index])

    def _split_DAG_into_execution_layers(self, dag: DAGCircuit, window_size) -> list[Any]:
        removed_nodes = []
        layers = []
        dag_layers = [i for i in dag.multigraph_layers()]

        # Remove DAGInNode and DAGOutNode from the layers
        for layer in dag_layers:
            indexes_to_remove = []
            for index, node in enumerate(layer):
                if isinstance(node, DAGInNode):
                    removed_nodes.append(node)
                    indexes_to_remove.append(index)
                elif isinstance(node, DAGOutNode):
                    indexes_to_remove.append(index)

            for index in reversed(indexes_to_remove):
                layer.pop(index)

            if len(layer) == 0:
                dag_layers.remove(layer)

        # removed_nodes.extend(dag_layers[0]) # Add input nodes to removed nodes
        index = 0

        while len(dag_layers) > 0:
            window_slice = self._fetch_window_from_zero(
                dag_layers, window_size)

            # Starting a new layer
            current_layer = []
            current_window = 0
            multi_qubit_layer = False
            single_qubit_layer = False

            for curr_index, layer in enumerate(window_slice):

                # If there are single qubit gates force them to be layered first
                # Sorting them is not the best solution, but it works for now, it is slow
                # This frees multiple qubits from dependencies on single qubits gates
                # allows for more parallelization in the next layers
                if any(node.num_qubits == 1 for node in layer):
                    layer.sort(key=lambda x: x.num_qubits)

                for node in layer:
                    # If the current layer is empty, we can add the first node and skip the rest of the checks
                    if len(current_layer) == 0:
                        current_layer.append(node)

                        # Remove the node because it was already added to the current layer
                        # and doest need to be checked again
                        dag_layers[index+curr_index].remove(node)
                        removed_nodes.append(node)

                        if not single_qubit_layer:
                            if node.num_qubits == 1:
                                single_qubit_layer = True
                            else:
                                multi_qubit_layer = True
                            continue

                    # If the node we are checking is not compatible with the current layer we skip it
                    elif multi_qubit_layer and node.num_qubits == 1:
                        continue
                    elif single_qubit_layer and node.num_qubits > 1:
                        continue

                    # We need to check that the current node is not dependent on any of the nodes in the current layer
                    # This is because we are trying to parallelize with layers ahead
                    if any(pre_node in current_layer for pre_node in dag.predecessors(node)):
                        continue

                    # Finally, we need to check that all the predecessors of the current node were already removed ("executed")
                    if any(pre_node not in removed_nodes for pre_node in dag.predecessors(node)):
                        continue

                    # If we reach here, the node is compatible with the current layer
                    current_layer.append(node)
                    dag_layers[index+curr_index].remove(node)
                    removed_nodes.append(node)

            layers.append(current_layer)

            if len(dag_layers[index]) == 0:
                dag_layers.pop(index)  # Remove empty layers
        return layers

    def _largest_entanglement_op(self, execution_layers: list[list]) -> int:
        """
        Returns the largest entanglement operation in the layer.
        If there are no entanglement operations, returns 0.
        """
        max_entanglement = 0
        for layer in execution_layers:
            n_entanglement = len(
                [i for i in layer if isinstance(i, DAGOpNode) and i.num_qubits >= 2])
            if n_entanglement > max_entanglement:
                max_entanglement = n_entanglement

        return max_entanglement

    def _generate_arch_json(self, entanglement_rows, entanglement_cols, storage_rows, storage_cols) -> str:
        """
        Generates a JSON representation of the architecture using ZACs format.
        """

        # zone_centering: 1:1 means that the entanglement zone is centered on the storage zone,
        # (1:2) means that the left side (difference between x coordinate of
        # entanglement zone and storage zone) is twice as large as the right side
        zone_centering = self.config.zone_centering

        entanglement_separation = self.config.entanglement_site_separation
        storage_separation = self.config.storage_site_separation
        padding = self.config.arch_padding

        ent_x_dimension = (entanglement_cols-1) * \
            entanglement_separation[0] + 2

        # If there is only one row, the entanglement zone height would be calculated as 0,
        # in that we set to one has the size minimum size just to contain one row of atoms
        ent_y_dimension = (entanglement_rows-1) * \
            entanglement_separation[1] if entanglement_rows > 1 else 1

        sto_x_dimension = (storage_cols-1) * storage_separation[0]
        sto_y_dimension = (storage_rows-1) * storage_separation[1]

        architecture = {
            "name": "tile_architecture",
            "storage_zones": [{
                "zone_id": 0,
                "slms": [{
                    "id": 0,
                    "site_seperation": self.config.storage_site_separation,
                    "r": storage_rows,
                    "c": storage_cols,
                    "location": [max(0, ((ent_x_dimension - sto_x_dimension) * zone_centering[0])/sum(zone_centering)), 0]}],
                "offset": [0, 0],
                "dimension": [sto_x_dimension, sto_y_dimension]}],
            "entanglement_zones": [{
                "zone_id": 0,
                "slms": [{
                    "id": 1,
                    "site_seperation": self.config.entanglement_site_separation,
                    "r": entanglement_rows,
                    "c": entanglement_cols,
                    "location": [max(0, ((sto_x_dimension - ent_x_dimension) * zone_centering[0])/sum(zone_centering)), (storage_rows-1)*3+self.config.zone_separation]},
                    {"id": 2,
                     "site_seperation": self.config.entanglement_site_separation,
                     "r": entanglement_rows,
                     "c": entanglement_cols,
                     "location": [2+max(0, ((sto_x_dimension - ent_x_dimension) * zone_centering[0])/sum(zone_centering)), (storage_rows-1)*3+self.config.zone_separation]}],
                "offset": [0, 0],
                "dimension": [ent_x_dimension, ent_y_dimension]}],
            "aods": [{
                "id": i,
                "site_seperation": self.config.aod_minimum_separation,
                "r": 10,  # Hardcoded for now, it's not being used
                "c": 10  # Hardcoded for now, it's not being used
            } for i in range(self.config.num_aods)
            # {
            #     "id": 1,
            #     "site_seperation": self.config.aod_minimum_separation,
            #     "r": 10,  # Hardcoded for now, it's not being used
            #     "c": 10  # Hardcoded for now, it's not being used
            # }
            ],
            'arch_range': [[0-padding, 0-padding],
                           [max(sto_x_dimension+padding, ent_x_dimension+padding),
                            sto_y_dimension+self.config.zone_separation+ent_y_dimension+padding]],
            'rydberg_range': [[[0, sto_y_dimension+self.config.zone_separation/2],
                               [sto_x_dimension, sto_x_dimension+self.config.zone_separation+ent_y_dimension]]]
        }

        dump(architecture, open(self.config.tmp_arch_file, 'w'), indent=1)

        return self.config.tmp_arch_file

    def set_best_architectures(self) -> List[List[Any]]:
        '''
        Simple version of the best_layouts function.
        It assumes that max fidelity relates to have a width equal to the number of qubits in the circuit.
        Entanglement and storage zone heights is predefined by the architecture and the number of rows in the grid.
        The width of the entanglement zone is defined by the floor of closest it can be to the width of the storage zone
        '''
        for circuit, dag, circuit_file in zip(self.input_circuits, self.input_dags, self.circuit_files):

            tile = Tile(self.config)
            logger.info(
                f"Processing best layout for circuit with #: {circuit.num_qubits} qubits")

            # um
            entanglement_pair_spacing = self.config.entanglement_site_separation[1]
            entanglement_atom_spacing = self.config.entanglement_site_separation[
                0] - entanglement_pair_spacing
            storage_atom_spacing = self.config.storage_site_separation[0]  # um

            per_circuit_entanglement_row_height = (
                self.config.entanglement_height // self.grid_rows) // entanglement_pair_spacing + 1

            execution_layers = self._split_DAG_into_execution_layers(
                dag, self.config.layer_split_window)

            storage_rows = (self.config.qpu_height -
                            self.config.entanglement_height) // self.grid_rows // storage_atom_spacing

            tile.config.storage_zone_rows = storage_rows

            largest_entanglement = self._largest_entanglement_op(
                execution_layers)

            minimun_entanglement_width = (ceil(
                largest_entanglement / per_circuit_entanglement_row_height)-1) * entanglement_pair_spacing + entanglement_atom_spacing

            minimun_storage_width = max(minimun_entanglement_width, (ceil(
                circuit.num_qubits / storage_rows)-1) * storage_atom_spacing)

            best_storage_width = circuit.num_qubits * storage_atom_spacing

            # Weighted average of the best and minimum storage width with the weights defined in the configuration
            selected_storage_width = ceil(
                best_storage_width * self.perf_weight + minimun_storage_width * (1-self.perf_weight) / 2)

            out = self._generate_arch_json(
                entanglement_rows=per_circuit_entanglement_row_height,
                entanglement_cols=int((selected_storage_width+entanglement_pair_spacing) // (
                    entanglement_atom_spacing+entanglement_pair_spacing)),
                storage_rows=storage_rows,
                storage_cols=int(selected_storage_width //
                                 storage_atom_spacing)
            )

            tile._set_architecture(out)
            tile.circuit_file = circuit_file
            tile.circuit = circuit
            tile.best_nlayers = len(execution_layers)
            self.tiles.append(tile)

        return self.tiles
