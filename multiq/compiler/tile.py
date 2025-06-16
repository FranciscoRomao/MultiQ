import json

from zac.scheduler.scheduler import Scheduler_mixin
from zac.placer.placer import Placer_mixin
from zac.verifier.verifier import Verifier_mixin
from zac.ds.architecture import Architecture
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

import qiskit.qasm2 as qasm2
from qiskit import transpile

from multiq.configuration import MultiQConfig
from multiq.router.router import Router_mixin


class Tile(Scheduler_mixin, Placer_mixin, Verifier_mixin, Router_mixin):
    def __init__(self, config: MultiQConfig):
        self.config = config
        self.n_q = 0
        self.n_g = 0
        self.g_q = []

        self.source_name = ""
        self.dir = "./result/"
        self.architecture = None

        # initialise the compiler's instructions output
        self.result_json = {
            'name': "", 'architecture_spec_path': None, 'instructions': [], "runtime": 0}

        self.runtime_analysis = {}
        self.to_verify = True
        self.trivial_placement = config.trivial_placement
        self.routing_strategy = config.routing_strategy
        self.scheduling_strategy = config.scheduling_strategy
        self.dynamic_placement = config.dynamic_placement
        self.given_initial_mapping = None
        self.has_dependency = config.has_dependency
        self.l2 = config.l2
        self.use_window = config.use_window
        self.reuse = config.reuse
        self.resyn = config.resyn
        self.common_1q = 0

        self.gate_scheduling = None
        self.gate_scheduling_idx = None
        self.gate_1q_scheduling = None
        self.reuse_qubit = None
        self.qubit_mapping = []

        self.width = 0 # in number of grid cells!
        self.height = 1

    def prepare_routing(self):
        """ Clear the dependency tracking datastructures for routing. """

        # last instruction ID which accessed a particular qubit
        self.qubit_dependency = [0 for _ in range(self.n_q)]
        self.site_dependency = dict()
        # instr_id of instruction which last used rydberg
        self.rydberg_dependency = [0 for _ in range(
            len(self.architecture.entanglement_zone))]

    def load_program(self, source_file: str):
        """ Load QASM source from source_file and apply Qiskit optimisations. """
        self.source_name = source_file

        self.g_q = []
        # -1 means no dependency and can be applied at initialisation
        self.dict_g_1q_parent = {-1: []}
        n_single_qubit_gate = 0

        cz_circuit = qasm2.load(source_file)
        cz_circuit = transpile(cz_circuit, basis_gates=["cz", "id", "u2", "u1", "u3"],
                               optimization_level=3,
                               seed_transpiler=0)

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
        # we can only do this once we have n_q
        self._set_architecture()

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
            # m_j_k = gate j can use qubit of gate k
            self.reuse_qubit.append(set())
            matrix = [[0 for k in range(len(self.gate_scheduling[i - 1]))]
                      for j in range(len(self.gate_scheduling[i]))]
            for gate_idx, gate in enumerate(self.gate_scheduling[i]):
                if qubit_is_used[i - 1][gate[0]] != -1 and qubit_is_used[i - 1][gate[0]] == qubit_is_used[i - 1][gate[1]]:
                    self.reuse_qubit[-1].add(gate[0])
                    self.reuse_qubit[-1].add(gate[1])
                else:
                    for q in gate:
                        if qubit_is_used[i - 1][q] > -1:
                            matrix[gate_idx][qubit_is_used[i - 1][q]] = 1
                            extra_reuse_qubit += 1
                for q in gate:
                    qubit_is_used[i][q] = gate_idx
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
        assert (extra_reuse_qubit >= 0)
        self.extra_reuse_qubit = extra_reuse_qubit
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

    def _set_architecture(self):
        # just use n_q as the number of cols in the tile for now
        with open("zac_config/toy_architecture.json", "r") as f:
            arch_json = json.load(f)
            # TODO: design a smarter tile size. Right now it's just the #qubits, making the top row always full.
            arch_json["storage_zones"][0]["slms"][0]["c"] = self.n_q
            self.width = self.n_q

            arch = Architecture(arch_json)
            arch.preprocessing()
            self.architecture = arch