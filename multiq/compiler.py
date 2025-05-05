from zac.scheduler.scheduler import Scheduler_mixin
from zac.placer.placer import Placer_mixin
from zac.animator.animator import Animator
from zac.verifier.verifier import Verifier_mixin
from zac.ds.architecture import Architecture
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching
import time

import qiskit.qasm2 as qasm2

from configuration import MultiQConfig
from .router import Router_mixin


class ZacTile(Scheduler_mixin, Placer_mixin, Verifier_mixin, Router_mixin):
    def __init__(self, config: MultiQConfig):
        self.config = config
        self.n_q = 0
        self.n_g = 0
        self.g_q = []

        self.dir = "./result/"
        self.architecture = None
        self.result_json = {
            'name': "", 'architecture_spec_path': None, 'instructions': [], "runtime": 0}
        self.runtime_analysis = {}
        self.to_verify = True
        self.trivial_placement = False
        self.routing_strategy = "maximalis_sort"
        self.scheduling_strategy = "asap"
        self.dynamic_placement = True
        self.given_initial_mapping = None
        self.has_dependency = True
        self.l2 = False
        self.use_window = True
        self.reuse = True
        self.resyn = True
        self.common_1q = 0

    def load_program(self, source_file: str):
        self.g_q = []
        self.dict_g_1q_parent = {-1: []}
        n_single_qubit_gate = 0

        cz_circuit = qasm2.load(source_file)
        self.n_q = cz_circuit.num_qubits

        list_qubit_last_2q_gate = [-1 for _ in range(self.n_q)]
        register_idx = dict()
        idx_begin = 0
        for i, qubit in enumerate(cz_circuit.qubits):
            if qubit._register == None:
                qubit._index = i
            elif qubit._register not in register_idx:
                register_idx[qubit._register] = idx_begin
                idx_begin += qubit._register.size
        instruction = cz_circuit.data
        for ins in instruction:
            if ins.operation.num_qubits == 2:
                offset = 0
                if ins.qubits[0]._register != None:
                    offset = register_idx[ins.qubits[0]._register]
                q0 = offset + ins.qubits[0]._index
                offset = 0
                if ins.qubits[1]._register != None:
                    offset = register_idx[ins.qubits[1]._register]
                q1 = offset + ins.qubits[1]._index
                list_qubit_last_2q_gate[q0] = len(self.g_q)
                list_qubit_last_2q_gate[q1] = len(self.g_q)
                if q0 < q1:
                    self.g_q.append([q0, q1])
                else:
                    self.g_q.append([q1, q0])
            elif ins.operation.name != "measure" and ins.operation.name != "barrier":
                offset = 0
                if ins.qubits[0]._register != None:
                    offset = register_idx[ins.qubits[0]._register]
                q0 = offset + ins.qubits[0]._index
                if list_qubit_last_2q_gate[q0] not in self.dict_g_1q_parent:
                    self.dict_g_1q_parent[list_qubit_last_2q_gate[q0]] = []
                self.dict_g_1q_parent[list_qubit_last_2q_gate[q0]].append(
                    (ins.operation.name, q0))
                n_single_qubit_gate += 1

        self.n_g = len(self.g_q)
        self.g_s = tuple(['CRZ' for _ in range(self.n_g)])
        print("[INFO]           number of qubits: {}".format(self.n_q))
        print("[INFO]           number of two-qubit gates: {}".format(len(self.g_q)))
        print(
            "[INFO]           number of single-qubit gates: {}".format(n_single_qubit_gate))

    def solve(self, save_file: bool = True):
        self.code_filename = self.dir + \
            f"code/{self.result_json['name']}_code.json"
        # member to hold intermedite results
        self.gate_scheduling = None
        self.gate_scheduling_idx = None
        self.gate_1q_scheduling = None
        self.reuse_qubit = None
        self.qubit_mapping = []

        # todo: check if the program input is valid, i.e., #q < #p
        t_s = time.time()
        # gate scheduling with graph coloring
        print("[INFO] ZAC: Run scheduling")
        self.scheduling()

        if self.reuse:
            self.collect_reuse_qubit()
        else:
            self.reuse_qubit = [set()
                                for _ in range(len(self.gate_scheduling))]

        self.place_qubit_initial()

        self.place_qubit_intermedeiate()

        self.route_qubit()
        self.runtime_analysis["total"] = time.time() - t_s

        if self.to_verify:
            print("[INFO] ZAC: Start Verification")
            self.verify_scheduling(self.gate_scheduling_idx)
            self.verify_qubit_mapping(0)

    def collect_reuse_qubit(self):
        """
        collect qubits that will remain in Rydberg zone between two Rydberg stages
        """
        self.reuse_qubit = []
        qubit_is_used = [[-1 for i in range(self.n_q)]
                         for j in range(len(self.gate_scheduling))]
        for gate_idx, gate in enumerate(self.gate_scheduling[0]):
            for q in gate:
                qubit_is_used[0][q] = gate_idx

        extra_reuse_qubit = 0
        for i in range(1, len(self.gate_scheduling)):
            # print("previous gate")
            # print(self.gate_scheduling[i - 1])
            # print("current gate")
            # print(self.gate_scheduling[i])
            # m_j_k = gate j can use qubit of gate k
            self.reuse_qubit.append(set())
            matrix = [[0 for k in range(len(self.gate_scheduling[i - 1]))]
                      for j in range(len(self.gate_scheduling[i]))]
            for gate_idx, gate in enumerate(self.gate_scheduling[i]):
                if qubit_is_used[i - 1][gate[0]] != -1 and qubit_is_used[i - 1][gate[0]] == qubit_is_used[i - 1][gate[1]]:
                    self.reuse_qubit[-1].add(gate[0])
                    self.reuse_qubit[-1].add(gate[1])
                    # print("YYYYYY")
                else:
                    for q in gate:
                        if qubit_is_used[i - 1][q] > -1:
                            matrix[gate_idx][qubit_is_used[i - 1][q]] = 1
                            extra_reuse_qubit += 1
                for q in gate:
                    qubit_is_used[i][q] = gate_idx
            # print(matrix)
            sparse_matrix = csr_matrix(matrix)
            matching = maximum_bipartite_matching(
                sparse_matrix, perm_type='column')
            for gate_idx, reuse_gate in enumerate(matching):
                if reuse_gate == -1:
                    continue
                extra_reuse_qubit -= 1
                gate = self.gate_scheduling[i][gate_idx]
                for q in gate:
                    if qubit_is_used[i - 1][q] == reuse_gate:
                        self.reuse_qubit[-1].add(q)
        #     print("cur_reuse_qubit:", extra_reuse_qubit)
        # print("extra_reuse_qubit: ", extra_reuse_qubit)
        assert (extra_reuse_qubit >= 0)
        self.extra_reuse_qubit = extra_reuse_qubit
        # print("reuse qubit")
        # print(self.reuse_qubit[-1])
        # input()
        self.reuse_qubit.append(set())

    def parse_setting(self, setting: dict):
        if "name" in setting:
            self.result_json['name'] = setting["name"]
        if "dir" in setting:
            self.dir = setting["dir"]
        if "dependency" in setting:
            self.has_dependency = setting["dependency"]
        if "routing_strategy" in setting:
            self.routing_strategy = setting["routing_strategy"]
        if "trivial_placement" in setting:
            self.trivial_placement = setting["trivial_placement"]
        if "dynamic_placement" in setting:
            self.dynamic_placement = setting["dynamic_placement"]
        if "use_window" in setting:
            self.use_window = setting["use_window"]
        if "use_verifier" in setting:
            self.to_verify = setting["use_verifier"]
        if "window_size" in setting:
            self.window_size = setting["window_size"]
        if "l2" in setting:
            self.l2 = setting["l2"]
        if "reuse" in setting:
            self.reuse = setting["reuse"]
        if "scheduling" in setting:
            self.scheduling_strategy = setting["scheduling"]
        if "resyn" in setting:
            self.resyn = setting["resyn"]

    def set_architecture(self, arch: Architecture):
        self.architecture = arch


class Compiler():
    """class to solve QLS problem."""

    def __init__(self, arch: Architecture):
        self.architecture = arch
        self.tiles: ZacTile = []
        self.config: MultiQConfig = None

        # global aod
        self.aod_end_time = [(0, i) for i in range(len(arch.dict_AOD))]
        self.aod_dependency = [0 for i in range(len(arch.dict_AOD))]

    def route_global_layer(self, layer_id: int):
        pass

    def route_global_batch(self):
        layer: int = 0
        # interference graph for each individual tile at a specific layer
        graphs: list[(int, list, list)] = []
        while any([len(t.gate_scheduling) > 0 for t in self.tiles]):

            iteration = 0
            unprocessed_nodes = {set() for _ in range(len(self.tiles))}

            for tile_id, tile in enumerate(self.tiles):
                for gate in tile.scheduling_layer[layer]:
                    for q in gate:
                        if tile.final_mapping[q] != tile.gate_mapping[q]:
                            unprocessed_nodes[tile_id].add(q)

            while any([len(unproc) > 0 for unproc in unprocessed_nodes]):

                for tile_id, tile in enumerate(self.tiles):
                    # node is a movement (q_x, site_x, q_y, site_y)
                    nodes, edges = tile.construct_interference_graph(layer)
                    graphs.append((tile_id, nodes, edges))
                    tile.gate_scheduling.pop(0)

                combined_nodes, combined_edges = self.combine_graphs(graphs)
                combined_edges.append(self.tilewise_violations(combined_nodes))

                independent_set_indices = Router_mixin.maximalis_solve(
                    combined_nodes, combined_edges)
                independent_nodes = [combined_nodes[i]
                                     for i in independent_set_indices]

                processed_nodes = {set() for _ in range(len(self.tiles))}
                for i_node in independent_nodes:
                    tile_id, movement = i_node
                    processed_nodes[tile_id].add(movement)

                for tile_id, tile in enumerate(self.tiles):
                    tile.process_movement_layer(
                        processed_nodes[tile_id], self.qubit_mapping[2 * layer], self.qubit_mapping[2 * layer + 1])
                iteration += 1

            for t in self.tiles:
                t.process_gate_layer(layer, self.qubit_mapping[2 * layer + 1])
            layer += 1

    def combine_graphs(self, graphs: list[(int, list, list)]):
        combined_nodes = []
        combined_edges = []

        tile = 0
        for id, nodes, edges in graphs:
            n_nodes = len(nodes)  # number of movements in one tile
            combined_nodes.append(nodes)
            # An edge is a pair of indices. Need to adjust new indices for each subgraph
            combined_edges.append([(i + tile, j + tile) for i, j in edges])
            tile += n_nodes

        return combined_nodes, combined_edges

    def tilewise_violations(self, nodes):
        """ Compute the incompatibilities between tiles """
        violations = []
        for i in range(len(nodes)):
            for j in range(i+1, len(nodes)):
                _, vector_a = nodes[i]
                _, vector_b = nodes[j]
                if not self.tilewise_compatible(vector_a, vector_b):
                    violations.append((i, j))

    # Across multiple tiles, only moves that share row coords can be done in parallel

    def tilewise_compatible(a, b) -> bool:
        # a = (start_row, end_row, start_col, end_col)
        if a[0] != b[0]:
            return False
        if a[1] != b[1]:
            return False

    # def parse_setting(self, setting: dict):
    #     self.config = MultiQConfig.from_config(setting)

    def set_architecture_spec_path(self, path: str):
        self.result_json['architecture_spec_path'] = path

    def set_initial_mapping(self, mapping):
        # todo: check if the given mapping is valid
        self.given_initial_mapping = mapping

    def compile(self):
        for tile in self.tiles:
            t_s = time.time()
            # gate scheduling with graph coloring
            tile.scheduling()
            if tile.reuse:
                tile.collect_reuse_qubit()
            else:
                tile.reuse_qubit = [set()
                                    for _ in range(len(self.gate_scheduling))]
            tile.place_qubit_initial()
            tile.place_qubit_intermedeiate()

        # Routing must be done globally
        self.route_global_batch()
            
    def set_programs(self, source_files: list[str]):
        for source_file in source_files:
            tile = ZacTile()
            zac_settings = {
                "routing_strategy": "maximalis",
                "scheduling": "asap",
                "trivial_placement": False,
                "dynamic_placement": True,
                "use_window": True,
                "window_size": 1000,
                "reuse": True
            }
            tile.parse_setting(zac_settings)
            tile.set_architecture(self.architecture)
            tile.load_program(source_file)
            self.tiles.append(tile)
