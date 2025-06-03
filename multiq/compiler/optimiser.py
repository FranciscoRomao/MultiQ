import logging
import copy
from qiskit import QuantumCircuit, transpile
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit

from .tile import Tile # Assuming this path is correct

logger = logging.getLogger("multiq")

class InstructionOptimiser:
    def __init__(self):
        """
        Initialises the instruction optimiser.
        """
        pass

    def _gates_to_dag(self, tile: Tile, start_layer: int, window_size: int) -> tuple[DAGCircuit | None, int]:
        """
        Converts a window of gates from the tile's schedule into a Qiskit DAGCircuit.
        Returns the DAG and the actual number of tile layers included in the window.
        """
        if not tile.gate_scheduling or start_layer >= len(tile.gate_scheduling):
            return None, 0

        qc = QuantumCircuit(tile.n_q)
        actual_tile_layers_in_window = 0
        operations_added = False

        for i in range(window_size):
            layer_idx = start_layer + i
            if layer_idx >= len(tile.gate_scheduling):
                break
            actual_tile_layers_in_window += 1

            # Add 2-qubit gates (assuming CZ from tile.gate_scheduling)
            for q_pair in tile.gate_scheduling[layer_idx]:
                qc.cz(q_pair[0], q_pair[1])
                operations_added = True
            
            # Add 1-qubit gates from tile.gate_1q_scheduling (if it's per layer)
            # This part needs careful implementation based on your ZacTile structure
            if hasattr(tile, 'gate_1q_scheduling') and \
               tile.gate_1q_scheduling and \
               layer_idx < len(tile.gate_1q_scheduling):
                for gate_name, q_idx in tile.gate_1q_scheduling[layer_idx]:
                    if gate_name.lower() == 'h': qc.h(q_idx)
                    elif gate_name.lower() == 'x': qc.x(q_idx)
                    # Add other 1Q gates and parameterized gates as needed
                    operations_added = True
        
        if not operations_added:
            return None, actual_tile_layers_in_window

        dag = circuit_to_dag(qc)
        return dag, actual_tile_layers_in_window

    def _apply_rules_to_dag(self, dag_window: DAGCircuit) -> DAGCircuit:
        """
        Applies a set of predefined algebraic transformation rules to the DAG.
        This is a placeholder. A real implementation would use Qiskit transpiler passes
        or custom rule logic.
        """
        try:
            temp_qc = dag_to_circuit(dag_window)
            # Example: light optimization. Basis gates should match your tile's capabilities.
            transpiled_qc = transpile(temp_qc, basis_gates=['cz', 'u3', 'h', 'x'], optimization_level=1) 
            transformed_dag = circuit_to_dag(transpiled_qc)
            return transformed_dag
        except Exception as e:
            logger.warning(f"Error during DAG transformation: {e}")
            return dag_window # Return original if transformation fails

    def _dag_to_tile_schedule(self, tile: Tile, transformed_dag: DAGCircuit, 
                              start_layer: int, original_tile_layers_in_window: int) -> int:
        """
        Converts the transformed DAGCircuit back into the tile's gate_scheduling format.
        This is a complex translation and needs to update tile.gate_scheduling, 
        tile.gate_1q_scheduling, and potentially tile.dict_g_1q_parent.
        Returns the number of new layers added to the tile's schedule for this window.
        Placeholder implementation.
        """
        new_window_gate_schedule_2q = []
        new_window_gate_schedule_1q = []

        for dag_layer_nodes in transformed_dag.layers():
            current_layer_2q_gates = []
            current_layer_1q_gates = []
            for node in dag_layer_nodes['graph'].op_nodes(include_directives=False):
                op = node.op
                q_indices = [q.index for q in node.qargs]

                if op.num_qubits == 2 and op.name == 'cz': # Adapt to your 2Q gate
                    current_layer_2q_gates.append(tuple(sorted(q_indices)))
                elif op.num_qubits == 1:
                    gate_name = op.name # Map back to your tile's 1Q gate names
                    current_layer_1q_gates.append((gate_name, q_indices[0]))
            
            if current_layer_2q_gates or current_layer_1q_gates:
                new_window_gate_schedule_2q.append(current_layer_2q_gates)
                if hasattr(tile, 'gate_1q_scheduling'): # Check if tile uses this
                    new_window_gate_schedule_1q.append(current_layer_1q_gates)
        
        # Remove old layers from the tile's schedule
        for _ in range(original_tile_layers_in_window):
            if start_layer < len(tile.gate_scheduling):
                tile.gate_scheduling.pop(start_layer)
            if hasattr(tile, 'gate_1q_scheduling') and tile.gate_1q_scheduling and \
               start_layer < len(tile.gate_1q_scheduling):
                tile.gate_1q_scheduling.pop(start_layer)

        # Insert new layers
        for i in range(len(new_window_gate_schedule_2q)):
            tile.gate_scheduling.insert(start_layer + i, new_window_gate_schedule_2q[i])
            if hasattr(tile, 'gate_1q_scheduling') and tile.gate_1q_scheduling and \
               i < len(new_window_gate_schedule_1q):
                 tile.gate_1q_scheduling.insert(start_layer + i, new_window_gate_schedule_1q[i])

        # CRITICAL: Update tile.dict_g_1q_parent if its structure is affected.
        # This sketch omits this complex update.

        logger.debug(f"Re-scheduled window at original tile layer {start_layer}. New window depth in tile: {len(new_window_gate_schedule_2q)}")
        return len(new_window_gate_schedule_2q)

    def _calculate_2q_packing_score(self, dag_window: DAGCircuit) -> tuple[int, int]:
        if not dag_window:
            return 0, 0
        total_2q_gates = 0
        for node in dag_window.op_nodes(include_directives=False):
            if node.op.num_qubits == 2:
                total_2q_gates += 1
        effective_layers = dag_window.depth()
        if total_2q_gates == 0:
            return 0, 0 # Or return 0, effective_layers if depth penalty desired for empty 2Q windows
        return total_2q_gates, effective_layers

    def optimise(self, tile: Tile, window_size: int = 3, passes: int = 1):
        if not tile.gate_scheduling:
            logger.info(f"Tile {tile.result_json.get('name', 'N/A')} has no 2Q-gate schedule to optimise.")
            return

        original_total_layers = len(tile.gate_scheduling)
        logger.info(f"Starting instruction optimisation for tile {tile.result_json.get('name', 'N/A')}. "
                    f"Initial layers: {original_total_layers}, Window: {window_size}, Passes: {passes}.")

        for p_num in range(passes):
            logger.debug(f"Optimisation Pass {p_num + 1}/{passes}")
            current_layer_idx = 0
            made_change_in_pass = False
            
            while current_layer_idx <= len(tile.gate_scheduling) - 1: # Iterate carefully
                dag_window, actual_tile_layers_in_window = self._gates_to_dag(tile, current_layer_idx, window_size)
                if dag_window is None or actual_tile_layers_in_window == 0:
                    if current_layer_idx >= len(tile.gate_scheduling) -1 : break # End of schedule
                    current_layer_idx += 1 
                    continue
                
                transformed_dag = self._apply_rules_to_dag(copy.deepcopy(dag_window))

                original_2q_gates, original_effective_layers = self._calculate_2q_packing_score(dag_window)
                transformed_2q_gates, transformed_effective_layers = self._calculate_2q_packing_score(transformed_dag)

                is_beneficial = False
                if transformed_2q_gates > 0:
                    if original_2q_gates == 0:
                        if transformed_effective_layers <= dag_window.depth():
                            is_beneficial = True
                    elif transformed_effective_layers < original_effective_layers and \
                         transformed_2q_gates >= original_2q_gates:
                        is_beneficial = True
                    elif transformed_effective_layers == original_effective_layers and \
                         transformed_2q_gates > original_2q_gates:
                        is_beneficial = True
                elif transformed_2q_gates == original_2q_gates and original_2q_gates > 0: # Both have 2Q gates
                    if transformed_dag.depth() < dag_window.depth(): # Overall DAG depth reduced
                        is_beneficial = True

                if is_beneficial:
                    logger.debug(
                        f"  Window at tile layer {current_layer_idx}: "
                        f"Original (2Q_gates:{original_2q_gates}, eff_layers:{original_effective_layers}, total_depth:{dag_window.depth()}), "
                        f"New (2Q_gates:{transformed_2q_gates}, eff_layers:{transformed_effective_layers}, total_depth:{transformed_dag.depth()}). Applying change."
                    )
                    new_tile_layers_for_window = self._dag_to_tile_schedule(
                        tile, transformed_dag, current_layer_idx, actual_tile_layers_in_window
                    )
                    made_change_in_pass = True
                    # Advance by 1 to allow overlapping windows to catch new opportunities.
                    # Or advance by new_tile_layers_for_window for non-overlapping.
                    current_layer_idx += 1 
                else:
                    current_layer_idx += 1
            
            if not made_change_in_pass and p_num > 0:
                logger.debug(f"No changes made in pass {p_num + 1}. Stopping early.")
                break
        
        final_total_layers = len(tile.gate_scheduling)
        logger.info(f"Finished instruction optimisation for tile {tile.result_json.get('name', 'N/A')}. "
                    f"Final layers: {final_total_layers} (was {original_total_layers}).")

