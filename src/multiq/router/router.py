
from .graph import GraphOperations_mixin
from .instruction import Instructions_mixin


class Router_mixin(GraphOperations_mixin, Instructions_mixin):

    def get_duration(self, inst: dict):
        """Return the duration of a rearrangeJob and set begin and end times on its detail instructions."""
        list_detail_inst = inst["insts"]
        duration = 0

        for detail_inst in list_detail_inst:
            inst_type = detail_inst["type"].split(":")[0]
            detail_inst["begin_time"] = duration
            if inst_type == "activate" or inst_type == "deactivate":
                duration += self.architecture.time_atom_transfer
                detail_inst["end_time"] = duration
            elif inst_type == "move":
                move_duration = 0
                for row_begin, row_end in zip(detail_inst["row_y_begin"], detail_inst["row_y_end"]):
                    for col_begin, col_end in zip(detail_inst["col_x_begin"], detail_inst["col_x_end"]):
                        tmp = self.architecture.movement_duration(
                            col_begin, row_begin, col_end, row_end)
                        if move_duration < tmp:
                            move_duration = tmp

                detail_inst["end_time"] = move_duration + duration
                duration += move_duration
            else:
                raise ValueError

        return duration

    def get_begin_time(self, cur_inst_idx: int, dependency: dict):
        """Earliest start time of an instruction given its dependencies."""
        begin_time = 0
        for dependency_type in dependency:
            if isinstance(dependency[dependency_type], int):
                inst_idx = dependency[dependency_type]
                if begin_time < self.result_json['instructions'][inst_idx]["end_time"]:
                    begin_time = self.result_json['instructions'][inst_idx]["end_time"]
            else:
                if dependency_type == "site":
                    for inst_idx in dependency[dependency_type]:
                        if self.result_json['instructions'][inst_idx]["type"] == "rearrangeJob":
                            # Time when the dependency finishes picking up atoms.
                            atom_transfer_finish_time = 0.0

                            for detail_inst in self.result_json['instructions'][inst_idx]["insts"]:
                                inst_type = detail_inst["type"].split(":")[0]
                                if inst_type == "activate":
                                    atom_transfer_finish_time = max(
                                        detail_inst["end_time"], atom_transfer_finish_time)

                            # Time when this instruction starts dropping atoms.
                            atom_transfer_begin_time = 0
                            for detail_inst in self.result_json['instructions'][cur_inst_idx]["insts"]:
                                inst_type = detail_inst["type"].split(":")[0]
                                if inst_type == "deactivate":
                                    atom_transfer_begin_time = max(
                                        detail_inst["begin_time"], atom_transfer_begin_time)
                            tmp_begin_time = atom_transfer_finish_time - atom_transfer_begin_time
                            if begin_time < tmp_begin_time:
                                begin_time = tmp_begin_time
                        else:
                            begin_time = max(
                                begin_time, self.result_json['instructions'][inst_idx]["end_time"])
                else:
                    for inst_idx in dependency[dependency_type]:
                        try:
                            begin_time = max(
                                begin_time, self.result_json['instructions'][inst_idx]["end_time"])
                        except:
                            print("instruction has no end_time",
                                  self.result_json['instructions'][inst_idx])
                            raise

        return begin_time

    def process_2q_gate_layer(self, layer: int, gate_mapping: list) -> int:
        """Generate the gate instructions for one 2q layer."""
        list_gate_idx = self.gate_scheduling_idx[layer]
        initial_instr_idx = len(self.result_json['instructions'])

        list_gate = self.gate_scheduling[layer]
        dict_gate_zone = dict()
        for i in range(len(list_gate)):
            slm_idx = gate_mapping[list_gate[i][0]][0]
            zone_idx = self.architecture.dict_SLM[slm_idx].entanglement_id
            if zone_idx not in dict_gate_zone:
                dict_gate_zone[zone_idx] = [i]
            else:
                dict_gate_zone[zone_idx].append(i)
        for rydberg_idx in dict_gate_zone:
            result_gate = [{"id": list_gate_idx[i], "q0": list_gate[i][0],
                            "q1": list_gate[i][1]} for i in dict_gate_zone[rydberg_idx]]
            set_qubit_dependency = set()
            inst_idx = len(self.result_json['instructions'])
            for gate_idx in dict_gate_zone[rydberg_idx]:
                gate = list_gate[gate_idx]
                set_qubit_dependency.add(self.qubit_dependency[gate[0]])
                self.qubit_dependency[gate[0]] = inst_idx
                set_qubit_dependency.add(self.qubit_dependency[gate[1]])
                self.qubit_dependency[gate[1]] = inst_idx
            dependency = {"qubit": [],
                          "rydberg": self.rydberg_dependency[rydberg_idx]}
            self.rydberg_dependency[rydberg_idx] = inst_idx
            dependency["qubit"] = list(set_qubit_dependency)
            self.write_gate_instruction(
                inst_idx, rydberg_idx, result_gate, dependency)

        return initial_instr_idx

    def process_1q_gate_layer(self, layer: int, gate_mapping: list):
        
        list_1q_gate = self.gate_1q_scheduling[layer]

        inst_idx = len(self.result_json['instructions'])
        result_gate = []
        set_qubit_dependency = set()
        for gate_info in list_1q_gate:
            set_qubit_dependency.add(self.qubit_dependency[gate_info[1]])
            self.qubit_dependency[gate_info[1]] = inst_idx
            result_gate.append({
                "name": gate_info[0],
                "q": gate_info[1]
            })
        dependency = {"qubit": []}
        dependency["qubit"] = list(set_qubit_dependency)

        if len(result_gate) > 0:
            self.write_1q_gate_instruction(
                inst_idx, result_gate, dependency, gate_mapping)

    def process_movement_layer(self, set_aod_qubit: set, initial_mapping: list, final_mapping: list):
        """Generate row-by-row atom transfer instructions."""
        # Qubits in the same row are picked up together.
        pickup_dict = {}
        for q in set_aod_qubit:
            _, y = self.architecture.exact_SLM_location_tuple(
                initial_mapping[q])
            if y in pickup_dict:
                pickup_dict[y].append(q)
            else:
                pickup_dict[y] = [q]
        list_aod_qubits = []
        list_end_location = []
        list_begin_location = []
        dependency = {
            "qubit": [],
            "site": [],
        }

        inst_idx = len(self.result_json['instructions'])

        set_qubit_dependency = set()
        set_site_dependency = set()
        for dict_key in pickup_dict:
            list_aod_qubits.append(pickup_dict[dict_key])
            row_begin_location = []
            row_end_location = []
            for q in pickup_dict[dict_key]:
                row_begin_location.append(
                    [q, initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2]])
                row_end_location.append(
                    [q, final_mapping[q][0], final_mapping[q][1], final_mapping[q][2]])

                site_key = (
                    final_mapping[q][0], final_mapping[q][1], final_mapping[q][2])
                if site_key in self.site_dependency:
                    set_site_dependency.add(self.site_dependency[site_key])
                site_key = (
                    initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2])
                self.site_dependency[site_key] = inst_idx

                set_qubit_dependency.add(self.qubit_dependency[q])
                self.qubit_dependency[q] = inst_idx
            list_begin_location.append(row_begin_location)
            list_end_location.append(row_end_location)
        dependency["qubit"] = list(set_qubit_dependency)
        dependency["site"] = list(set_site_dependency)
        self.write_rearrangement_instruction(
            inst_idx, list_aod_qubits, list_begin_location, list_end_location, dependency)

        return inst_idx

    def construct_reverse_layer(self, id_layer_start: int, initial_mapping: list, final_mapping: list):
        """Build the reverse movement layer from the forward one."""
        id_layer_end = len(self.result_json['instructions'])
        for layer in range(id_layer_start, id_layer_end):
            if self.result_json['instructions'][layer]["type"] == "rydberg":
                break
            else:

                inst_idx = len(self.result_json['instructions'])
                dependency = {
                    "qubit": [],
                    "site": [],
                }
                set_qubit_dependency = set()
                set_site_dependency = set()
                list_aod_qubits = self.result_json['instructions'][layer]["aod_qubits"]
                list_end_location = []
                list_begin_location = []

                for sub_list_qubits in list_aod_qubits:
                    row_begin_location = []
                    row_end_location = []
                    for q in sub_list_qubits:
                        row_begin_location.append(
                            [q, initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2]])
                        row_end_location.append(
                            [q, final_mapping[q][0], final_mapping[q][1], final_mapping[q][2]])
                        site_key = (
                            final_mapping[q][0], final_mapping[q][1], final_mapping[q][2])
                        if site_key in self.site_dependency:
                            set_site_dependency.add(
                                self.site_dependency[site_key])
                        site_key = (
                            initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2])
                        self.site_dependency[site_key] = inst_idx
                        set_qubit_dependency.add(self.qubit_dependency[q])
                        self.qubit_dependency[q] = inst_idx

                    list_begin_location.append(row_begin_location)
                    list_end_location.append(row_end_location)
                dependency["qubit"] = list(set_qubit_dependency)
                dependency["site"] = list(set_site_dependency)
                self.write_rearrangement_instruction(inst_idx,
                                                     list_aod_qubits,
                                                     list_begin_location,
                                                     list_end_location,
                                                     dependency)
