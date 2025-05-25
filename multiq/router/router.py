import time

from .graph import GraphOperations_mixin
from .instruction import Instructions_mixin


from multiq.types.movement import Movement


class Router_mixin(GraphOperations_mixin, Instructions_mixin):

    def get_duration(self, inst: dict):
        """
            Calculate the total time required for the instructions in a rearrangeJob. Populates 
            the detail instructions inside a job with begin and end times.
        Args:
            inst (dict): instructions list
        Raises:
            ValueError: _description_
        Returns:
            _type_: duration of the instruction
        """
        list_detail_inst = inst["insts"]
        duration = 0
        # # # !
        # a = 0.00275
        # d = 10
        # unit_move = math.sqrt(d/a)
        # t = unit_move + 2 * self.architecture.time_atom_transfer
        # return t

        for detail_inst in list_detail_inst:
            inst_type = detail_inst["type"].split(":")[0]
            detail_inst["begin_time"] = duration
            if inst_type == "activate" or inst_type == "deactivate":
                duration += self.architecture.time_atom_transfer
                # NB: set time
                detail_inst["end_time"] = duration
            elif inst_type == "move":
                move_duration = 0
                for row_begin, row_end in zip(detail_inst["row_y_begin"], detail_inst["row_y_end"]):
                    for col_begin, col_end in zip(detail_inst["col_x_begin"], detail_inst["col_x_end"]):
                        tmp = self.architecture.movement_duration(
                            col_begin, row_begin, col_end, row_end)
                        if move_duration < tmp:
                            move_duration = tmp

                # NB: set time
                detail_inst["end_time"] = move_duration + duration
                duration += move_duration
            else:
                raise ValueError

        return duration

    # def aod_assignment(self, id_layer_start: int, aod_begin_time: float):
    #     """
    #         Assign begin and end times to the operations given that aod_begin_time is the earliest time
    #         the AoD laser can be used.
    #     """

    #     # [rearrangeJobs, otherJobs]
    #     list_instruction_duration = [[], []]
    #     id_layer_end = len(self.result_json['instructions'])
    #     duration_idx = 0
    #     list_gate_layer_idx = []

    #     aod_end_time = 0.0

    #     for idx in range(id_layer_start, id_layer_end):
    #         if self.result_json['instructions'][idx]["type"] != "rearrangeJob":
    #             # subsequent ops go into list_instr_durcation[1]
    #             duration_idx = 1
    #             list_gate_layer_idx.append(idx)
    #             continue

    #         # get duration of rearrangeJob
    #         duration = self.get_duration(self.result_json['instructions'][idx])
    #         list_instruction_duration[duration_idx].append((duration, idx))

    #     # sort rearrangeJobs from shortest to longest
    #     list_instruction_duration[0] = sorted(
    #         list_instruction_duration[0], reverse=True)
    #     list_instruction_duration[1] = sorted(
    #         list_instruction_duration[1], reverse=True)

    #     for i in range(2):
    #         # for rearrange instructions
    #         for item in list_instruction_duration[i]:
    #             duration = item[0]
    #             inst = self.result_json['instructions'][item[1]]
    #             begin_time = max(aod_begin_time, self.get_begin_time(
    #                 item[1], inst["dependency"]))
    #             end_time = begin_time + duration
    #             inst["dependency"]["aod"] = -1
    #             # self.aod_dependency[aod_id] = item[1]
    #             inst["begin_time"] = begin_time
    #             inst["end_time"] = end_time
    #             inst["aod_id"] = 0  # Fixed to 0. Using only one AoD for now
    #             aod_end_time = end_time

    #             for detail_inst in inst["insts"]:
    #                 detail_inst["begin_time"] += begin_time
    #                 detail_inst["end_time"] += begin_time
    #             if self.result_json["runtime"] < end_time:
    #                 self.result_json["runtime"] = end_time

    #         # for gate/rydberg instructions
    #         if i == 0:
    #             for gate_layer_idx in list_gate_layer_idx:
    #                 # laser scheduling
    #                 inst = self.result_json['instructions'][gate_layer_idx]
    #                 begin_time = self.get_begin_time(
    #                     gate_layer_idx, inst["dependency"])
    #                 if inst["type"] == "rydberg":
    #                     end_time = begin_time + self.architecture.time_rydberg
    #                 else:
    #                     # for sequential gate execution
    #                     end_time = begin_time + \
    #                         (self.architecture.time_1qGate *
    #                          len(inst["gates"])) + self.common_1q

    #                 if self.result_json["runtime"] < end_time:
    #                     self.result_json["runtime"] = end_time
    #                 inst["begin_time"] = begin_time
    #                 inst["end_time"] = end_time
    #     return aod_end_time

    def get_begin_time(self, cur_inst_idx: int, dependency: dict):
        """ 
            Iterate through the dependencies and find out the earliest time
            from which this operation can conceivably start. 
        """
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
                            # find the time that the instruction finish atom transfer
                            # !
                            atom_transfer_finish_time = 0.0

                            for detail_inst in self.result_json['instructions'][inst_idx]["insts"]:
                                inst_type = detail_inst["type"].split(":")[0]
                                if inst_type == "activate":
                                    atom_transfer_finish_time = max(
                                        detail_inst["end_time"], atom_transfer_finish_time)

                            # find the time until dropping of the qubits
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

    def process_gate_layer(self, layer: int, gate_mapping: list):
        """
        generate a layer for gate execution
        """

        # print("process gate layer")
        list_gate_idx = self.gate_scheduling_idx[layer]
        # print("list_gate_idx:", list_gate_idx)
        # print("gate_mapping:", gate_mapping)
        # print("gate scheduling", self.gate_scheduling)

        initial_instr_idx = len(self.result_json['instructions'])

        list_gate = self.gate_scheduling[layer]
        list_1q_gate = self.gate_1q_scheduling[layer]
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
                # collect qubit dependency
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

        # process single-qubit gates
        inst_idx = len(self.result_json['instructions'])
        result_gate = []
        set_qubit_dependency = set()
        for gate_info in list_1q_gate:
            # collect qubit dependency
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

        return initial_instr_idx

    def process_movement_layer(self, set_aod_qubit: set, initial_mapping: list, final_mapping: list):
        # print("process movement layer. initial mapping:", initial_mapping)
        # print("process movement layer. set_aod_dict:", set_aod_qubit)
        """
        generate layers for row-by-row based atom transfer
        """
        # seperate qubits in list_aod_qubit into multiple lists where qubits in one list can pick up simultaneously
        # we use row-based pick up
        pickup_dict = {}  # key: array and row, value: a list of qubit in the same row
        for q in set_aod_qubit:
            x, y = self.architecture.exact_SLM_location_tuple(
                initial_mapping[q])
            if y in pickup_dict:
                pickup_dict[y].append(q)
            else:
                pickup_dict[y] = [q]
        list_aod_qubits = []  # row-by-row grouped qubits
        list_end_location = []
        list_begin_location = []
        dependency = {
            "qubit": [],
            "site": [],
        }

        # process aod dependency
        inst_idx = len(self.result_json['instructions'])

        set_qubit_dependency = set()
        set_site_dependency = set()
        for dict_key in pickup_dict:
            # collect set of aod qubits to pick up
            list_aod_qubits.append(pickup_dict[dict_key])
            row_begin_location = []
            row_end_location = []
            for q in pickup_dict[dict_key]:
                # collect qubit begin location
                row_begin_location.append(
                    [q, initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2]])
                # collect qubit end location
                row_end_location.append(
                    [q, final_mapping[q][0], final_mapping[q][1], final_mapping[q][2]])

                # process site dependency
                site_key = (
                    final_mapping[q][0], final_mapping[q][1], final_mapping[q][2])
                if site_key in self.site_dependency:
                    set_site_dependency.add(self.site_dependency[site_key])
                site_key = (
                    initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2])
                self.site_dependency[site_key] = inst_idx

                # collect qubit dependency
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
        """
        construct reverse movement layer by processing the forward movement
        """
        id_layer_end = len(self.result_json['instructions'])
        for layer in range(id_layer_start, id_layer_end):
            if self.result_json['instructions'][layer]["type"] == "rydberg":
                # we have reached the end of the move instructions and found a gate instruction
                break
            else:
                # process a rearrangement layer

                # the new instruction ID
                inst_idx = len(self.result_json['instructions'])
                # dependencies for this operation
                dependency = {
                    "qubit": [],
                    "site": [],
                }
                # process aod dependency
                set_qubit_dependency = set()
                set_site_dependency = set()
                list_aod_qubits = self.result_json['instructions'][layer]["aod_qubits"]
                list_end_location = []
                list_begin_location = []

                # for each grouped qubit row
                for sub_list_qubits in list_aod_qubits:
                    row_begin_location = []
                    row_end_location = []
                    for q in sub_list_qubits:
                        # current position is result of forward mapping
                        row_begin_location.append(
                            [q, initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2]])
                        # end position is the new final mapping
                        row_end_location.append(
                            [q, final_mapping[q][0], final_mapping[q][1], final_mapping[q][2]])
                        # process site dependency
                        # transitively add dependencies
                        site_key = (
                            final_mapping[q][0], final_mapping[q][1], final_mapping[q][2])
                        if site_key in self.site_dependency:
                            set_site_dependency.add(
                                self.site_dependency[site_key])
                        site_key = (
                            initial_mapping[q][0], initial_mapping[q][1], initial_mapping[q][2])
                        self.site_dependency[site_key] = inst_idx
                        # collect qubit dependency
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
