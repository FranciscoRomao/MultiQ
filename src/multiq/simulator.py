import json
from multiq.configuration import MultiQConfig
from math import e

class Simulator():
    """Compute circuit fidelity from a compiled code file."""

    def __init__(self, config:MultiQConfig):
        self.fidelity_2q_gate = config.fidelity_2q_gate
        self.fidelity_2q_gate_for_idle = 1 - (1-self.fidelity_2q_gate)/2
        self.fidelity_1q_gate = config.fidelity_1q_gate
        self.fidelity_atom_transfer = config.fidelity_atom_transfer
        self.time_coherence = config.time_coherence # us
        self.time_atom_transfer = config.time_atom_transfer # us
        self.time_rydberg = config.time_rydberg # us
        self.time_1q_gate = config.time_1q_gate # us

        self.entanglement_zone = set()
        self.n_aod = 0
        
        self.n_qubit = 0
        self.list_instrcution = []

        self.cir_fidelity = 1
        self.cir_fidelity_2q_gate = 1
        self.cir_fidelity_2q_gate_for_idle = 1
        self.cir_fidelity_1q_gate = 1
        self.cir_fidelity_atom_transfer = 1
        self.cir_fidelity_coherence = 1
        self.cir_qubit_busy_time = []
        self.on_going_1qrow_gate = False
    
    def parse(self, code_file: str):
        with open(code_file, 'r') as f:
            result = json.load(f)
        self.list_instrcution = result["instructions"]
        if self.list_instrcution[0]["type"] == "init":
            self.n_qubit = len(self.list_instrcution[0]['init_locs'])
        else:
            assert(0)

    def process_rydberg(self, instruction, set_qubit_in_rydberg):
        list_gates = instruction["gates"]
        if len(list_gates) == 0:
            return
        self.cir_fidelity_2q_gate *= pow(self.fidelity_2q_gate, len(list_gates))
        for i in set_qubit_in_rydberg:
            self.cir_qubit_busy_time[i] += self.time_rydberg
    
    def process_1q_gate(self, instruction):
        list_gates = instruction["gates"]
        if len(list_gates) == 0:
            return
        self.cir_fidelity_1q_gate *= pow(self.fidelity_1q_gate, len(list_gates))
        for gate_info in list_gates:
            self.cir_qubit_busy_time[gate_info["q"]] += self.time_1q_gate

    def process_row1q_gate(self, instruction):
        list_gates = instruction["gates"]
        if len(list_gates) == 0:
            return
        # Row 1q gates have the same fidelity as single 1q gates, applied in parallel.
        self.cir_fidelity_1q_gate *= pow(self.fidelity_1q_gate, len(list_gates))
        for gate_info in list_gates:
            self.cir_qubit_busy_time[gate_info["q"]] += self.time_1q_gate

    def process_arrangement(self, instruction, set_qubit_in_rydberg):
        # Each transfer is a pick up and a drop off.
        time_atom_transfer = self.time_atom_transfer * 2
        num_transfer = 0
        list_aod_qubits = instruction["aod_qubits"]
        num_transfer += len(list_aod_qubits)
        for q in list_aod_qubits:
            self.cir_qubit_busy_time[q] += time_atom_transfer
        self.cir_fidelity_atom_transfer *= pow(self.fidelity_atom_transfer, 2*num_transfer)
        list_qubit_end_location = instruction["end_locs"]

    def simulate(self):
        self.cir_fidelity = 1
        self.cir_fidelity_2q_gate = 1
        self.cir_fidelity_2q_gate_for_idle = 1
        self.cir_fidelity_1q_gate = 1
        self.cir_fidelity_atom_transfer = 1
        self.cir_fidelity_coherence = 1
        self.cir_qubit_busy_time = [0 for i in range(self.n_qubit)]

        circuit_end_time = 0
        self.single_qubit_extra_time = 0
        set_qubit_in_rydberg = set()
        for i, instruction in enumerate(self.list_instrcution):
            if instruction["type"] == "init":
                continue
            elif instruction["type"] == "rydberg":
                self.process_rydberg(instruction, set_qubit_in_rydberg)
            elif instruction["type"] == "rearrangeJob":
                self.process_arrangement(instruction, set_qubit_in_rydberg)
            elif instruction["type"] == "1qGate":
                self.process_1q_gate(instruction)
            elif instruction["type"] == "row1qGate":
                self.process_row1q_gate(instruction)
            else:
                raise ValueError("Wrong instruction type")
            instruction_end_time = instruction["end_time"]
            if circuit_end_time < instruction_end_time:
                circuit_end_time = instruction_end_time
        circuit_end_time += self.single_qubit_extra_time
        for t in self.cir_qubit_busy_time:
            idle_t = circuit_end_time - t
            self.cir_fidelity_coherence *= e**(-idle_t/float(self.time_coherence))
            
        self.cir_fidelity = self.cir_fidelity_1q_gate * self.cir_fidelity_2q_gate * self.cir_fidelity_2q_gate_for_idle \
                            * self.cir_fidelity_atom_transfer * self.cir_fidelity_coherence
        results = { "cir_fidelity" : self.cir_fidelity,
                    "cir_fidelity_1q_gate": self.cir_fidelity_1q_gate,
                    "cir_fidelity_2q_gate": self.cir_fidelity_2q_gate,
                    "cir_fidelity_2q_gate_for_idle": self.cir_fidelity_2q_gate_for_idle,
                    "cir_fidelity_atom_transfer": self.cir_fidelity_atom_transfer,
                    "cir_fidelity_coherence": self.cir_fidelity_coherence,
                    "cir_duration": circuit_end_time}
        return results
        

