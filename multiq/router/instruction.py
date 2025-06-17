from copy import deepcopy
from itertools import chain

class Instructions_mixin:
    PARKING_DIST = 1

    def write_rearrangement_instruction(self, inst_idx: int, aod_qubits: list, begin_location: list, end_location: list, dependency: dict):
        inst = {
            "type": "rearrangeJob",
            "id": inst_idx,
            "aod_id": 0,
            "aod_qubits": aod_qubits,
            "begin_locs": begin_location,
            "end_locs": end_location,
            "dependency": dependency
        }
        inst["insts"] = self.expand_arrangement(inst)
        self.result_json['instructions'].append(inst)

    def flatten_rearrangment_instruction(self):
        for inst in self.result_json['instructions']:
            if inst["type"] == "rearrangeJob":
                inst["aod_qubits"] = list(
                    chain.from_iterable(inst["aod_qubits"]))
                inst["begin_locs"] = list(
                    chain.from_iterable(inst["begin_locs"]))
                inst["end_locs"] = list(chain.from_iterable(inst["end_locs"]))

    def expand_arrangement(self, inst: dict):
        details = []  # all detailed instructions

        # ---------------------- find out number of cols ----------------------
        all_col_x = []  # all the x coord of qubits
        coords = []  # coords of qubits, shape is same as "begin_locs"
        # these coords are going to be updated as we construct the detail insts

        for locs in inst["begin_locs"]:
            coords_row = []
            for loc in locs:
                exact_location = self.architecture.exact_SLM_location(
                    loc[1], loc[2], loc[3])
                coords_row.append({
                    "id": loc[0],
                    "x": exact_location[0],
                    "y": exact_location[1],
                })

                all_col_x.append(exact_location[0])

            coords.append(coords_row)

        init_coords = deepcopy(coords)

        all_col_x = sorted(all_col_x)

        # assign AOD column ids based on all x coords needed
        col_x_to_id = {all_col_x[i]: i for i in range(len(all_col_x))}
        # ---------------------------------------------------------------------

        # -------------------- activation and parking -------------------------
        all_col_idx_sofar = []  # which col has been activated
        for row_id, locs in enumerate(inst["begin_locs"]):  # each row

            row_y = self.architecture.exact_SLM_location(
                locs[0][1],
                locs[0][2],
                locs[0][3],
            )[1]
            row_loc = [locs[0][1], locs[0][2]]

            # before activation, adjust column position. This is necessary
            # whenever cols are parked (the `parking` movement below).
            shift_back = {
                "type": "move",
                "move_type": "before",
                "row_id": [],
                "row_y_begin": [],
                "row_y_end": [],
                "row_loc_begin": [],
                "row_loc_end": [],
                "col_id": [],
                "col_x_begin": [],
                "col_x_end": [],
                "col_loc_begin": [],
                "col_loc_end": [],
                "begin_coord": deepcopy(coords),
                "end_coord": [],
            }

            # activate one row and some columns
            activate = {
                "type": "activate",
                "row_id": [row_id, ],
                "row_y": [row_y, ],
                "row_loc": [row_loc, ],
                "col_id": [],
                "col_x": [],
                "col_loc": [],
            }

            for j, loc in enumerate(locs):
                col_x = self.architecture.exact_SLM_location(
                    loc[1],
                    loc[2],
                    loc[3],
                )[0]
                col_loc = [loc[1], loc[3]]
                col_id = col_x_to_id[col_x]
                if col_id not in all_col_idx_sofar:
                    # the col hasn't been activated, so there's no shift back
                    # and we need to activate it at `col_x`.`
                    all_col_idx_sofar.append(col_id)
                    activate["col_id"].append(col_id)
                    activate["col_x"].append(col_x)
                    activate["col_loc"].append(col_loc)
                else:
                    # the col has been activated, thus parked previously and we
                    # need the shift back, but we do not activate again.
                    shift_back["col_id"].append(col_id)
                    shift_back["col_x_begin"].append(col_x + self.PARKING_DIST)
                    shift_back["col_x_end"].append(col_x)
                    shift_back["col_loc_begin"].append([-1, -1])
                    shift_back["col_loc_end"].append(col_loc)
                    # since there's a shift, update the coords of the qubit
                    coords[row_id][j]["x"] = col_x

            shift_back["end_coord"] = deepcopy(coords)

            if len(shift_back["col_id"]) != 0:
                details.append(shift_back)
            details.append(activate)

            if row_id < len(inst["begin_locs"]) - 1:
                # parking movement after the activation
                # parking is required if we have activated some col, and there is
                # some qubit we don't want to pick up at the intersection of this
                # col and some future row to activate. We just always park here.
                # the last parking is not needed since there's a big move after it.
                parking = {
                    "type": "move",
                    "move_type": "after",
                    "row_id": [row_id, ],
                    "row_y_begin": [row_y, ],
                    "row_y_end": [row_y + self.PARKING_DIST],
                    "row_loc_begin": [row_loc],
                    "row_loc_end": [[-1, -1]],
                    "col_id": [],
                    "col_x_begin": [],
                    "col_x_end": [],
                    "col_loc_begin": [],
                    "col_loc_end": [],
                    "begin_coord": deepcopy(coords),
                    "end_coord": [],
                }
                for j, loc in enumerate(locs):
                    col_x = self.architecture.exact_SLM_location(
                         loc[1],
                         loc[2],
                         loc[3])[0]
                    col_loc = [loc[1], loc[3]]
                    col_id = col_x_to_id[col_x]
                    # all columns used in this row are parked after the activation
                    parking["col_id"].append(col_id)
                    parking["col_x_begin"].append(col_x)
                    parking["col_x_end"].append(col_x + self.PARKING_DIST)
                    parking["col_loc_begin"].append(col_loc)
                    parking["col_loc_end"].append([-1, -1])
                    coords[row_id][j]["x"] = parking["col_x_end"][-1]
                    coords[row_id][j]["y"] = parking["row_y_end"][0]
                parking["end_coord"] = deepcopy(coords)
                details.append(parking)
        # ---------------------------------------------------------------------

        # ------------------------- big move ----------------------------------
        big_move = {
            "type": "move:big",
            "move_type": "big",
            "row_id": [],
            "row_y_begin": [],
            "row_y_end": [],
            "row_loc_begin": [],
            "row_loc_end": [],
            "col_id": [],
            "col_x_begin": [],
            "col_x_end": [],
            "col_loc_begin": [],
            "col_loc_end": [],
            "begin_coord": deepcopy(coords),
            "end_coord": [],
        }

        for row_id, (begin_locs, end_locs) in enumerate(zip(
            inst["begin_locs"], inst["end_locs"],
        )):

            big_move["row_id"].append(row_id)
            big_move["row_y_begin"].append(
                coords[row_id][0]["y"]
            )
            if init_coords[row_id][0]["y"] == coords[row_id][0]["y"]:
                # AOD row is align with SLM row
                big_move["row_loc_begin"].append(
                    [begin_locs[0][1], begin_locs[0][2]])
            else:
                big_move["row_loc_begin"].append([-1, -1])

            big_move["row_y_end"].append(
                self.architecture.exact_SLM_location(
                    end_locs[0][1],
                    end_locs[0][2],
                    end_locs[0][3],
                )[1]
            )
            big_move["row_loc_end"].append([end_locs[0][1], end_locs[0][2]])

            for j, (begin_loc, end_loc) in enumerate(zip(begin_locs, end_locs)):
                col_x = self.architecture.exact_SLM_location(
                    begin_loc[1],
                    begin_loc[2],
                    begin_loc[3],
                )[0]
                col_id = col_x_to_id[col_x]

                if col_id not in big_move["col_id"]:
                    # the movement of this rol has not been recorded before
                    big_move["col_id"].append(col_id)
                    big_move["col_x_begin"].append(coords[row_id][j]["x"])
                    if init_coords[row_id][j]["x"] == coords[row_id][j]["x"]:
                        # AOD col is align with SLM col
                        big_move["col_loc_begin"].append(
                            [begin_loc[1], begin_loc[3]])
                    else:
                        big_move["col_loc_begin"].append([-1, -1])
                    big_move["col_x_end"].append(
                        self.architecture.exact_SLM_location(
                            end_loc[1],
                            end_loc[2],
                            end_loc[3],
                        )[0]
                    )
                    big_move["col_loc_end"].append([end_loc[1], end_loc[3]])

                # whether or not the movement of this col has been considered
                # before, we need to update the coords of the qubit.
                coords[row_id][j]["x"] = self.architecture.exact_SLM_location(
                    end_loc[1],
                    end_loc[2],
                    end_loc[3],
                )[0]
                coords[row_id][j]["y"] = self.architecture.exact_SLM_location(
                    end_locs[0][1],
                    end_locs[0][2],
                    end_locs[0][3],
                )[1]

        big_move["end_coord"] = deepcopy(coords)
        details.append(big_move)
        # ---------------------------------------------------------------------

        # --------------------------- deactivation ----------------------------
        details.append({
            "type": "deactivate",
            "row_id": [i for i in range(len(inst["begin_locs"]))],
            "col_id": [i for i in range(len(all_col_x))],
        })
        # ---------------------------------------------------------------------

        for inst_counter, detail_inst in enumerate(details):
            detail_inst["id"] = inst_counter

        return details


    def write_gate_instruction(self, inst_idx: int, rydberg_idx: int, result_gate: list, dependency: dict):
        self.result_json['instructions'].append(
            {
                "type": "rydberg",
                "id": inst_idx,
                "zone_id": rydberg_idx,
                "gates": result_gate,
                "dependency": dependency
            }
        )

    def write_1q_gate_instruction(self, inst_idx: int, result_gate: list, dependency: dict, gate_mapping: list):
        locs = []
        for gate in result_gate:
            locs.append((gate["q"], gate_mapping[gate["q"]][0],
                        gate_mapping[gate["q"]][1], gate_mapping[gate["q"]][2]))

        self.result_json['instructions'].append(
            {
                "type": "1qGate",
                "unitary": "u3",
                "id": inst_idx,
                "locs": locs,
                "gates": result_gate,
                "dependency": dependency
            }
        )

    def write_row1q_gate_instruction(self, row_idx: int, inst_idx: int, result_gate: list, dependency: dict, gate_mapping: list):
        locs = []
        for gate in result_gate:
            locs.append((gate["q"], gate_mapping[gate["q"]][0],
                        gate_mapping[gate["q"]][1], gate_mapping[gate["q"]][2]))

        self.result_json['instructions'].append(
            {
                "type": "row1qGate",
                "unitary": "u3",
                "id": inst_idx,
                "row": row_idx,
                "locs": locs,
                "gates": result_gate,
                "dependency": dependency
            }
        )
