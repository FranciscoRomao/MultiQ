
import networkx as nx

from multiq.types.movement import Movement



class GraphOperations_mixin:
    PARKING_DIST = 1

    # TODO merge forward and reverse
    def nx_reverse_interference_graph(self, layer: int):
        if layer + 2 >= len(self.qubit_mapping):
            return None, None

        # odd indices inside entanglement zone
        gate_mapping = self.qubit_mapping[2 * layer + 1]
        final_mapping = self.qubit_mapping[2 * layer + 2]

        qubits_in_layer = []  # consist of qubits to be moved
        for gate in self.gate_scheduling[layer]:
            for q in gate:
                # exclude 1q gates or no moves
                if final_mapping[q] != gate_mapping[q]:
                    qubits_in_layer.append(q)

         # graph constructions
        vectors = self.graph_construction(
            qubits_in_layer, final_mapping, gate_mapping)
        graph = self.nx_graph(vectors)

        return graph, vectors

    def nx_interference_graph(self, layer: int):
        # even indices in storage
        initial_mapping = self.qubit_mapping[2 * layer]
        # odd indices inside entanglement zone
        gate_mapping = self.qubit_mapping[2 * layer + 1]

        qubits_in_layer = []  # consist of qubits to be moved
        for gate in self.gate_scheduling[layer]:
            for q in gate:
                # exclude 1q gates or no moves
                if initial_mapping[q] != gate_mapping[q]:
                    assert (initial_mapping[q][0] ==
                            0 or gate_mapping[q][0] == 0)
                    qubits_in_layer.append(q)

         # graph constructions
        vectors = self.graph_construction(
            qubits_in_layer, initial_mapping, gate_mapping)
        graph = self.nx_graph(vectors)

        return graph, vectors

    def graph_construction(self, remain_graph: list, initial_mapping: list, final_mapping: list):
        vectors = []
        if self.use_window:
            vector_length = min(self.window_size, len(remain_graph))
        else:
            vector_length = len(remain_graph)

        vectors = [Movement(0, 0, 0, 0, 0) for _ in range(vector_length)]

        for i, q in enumerate(remain_graph):
            (q_x, q_y) = self.architecture.exact_SLM_location_tuple(
                initial_mapping[q])
            (site_x, site_y) = self.architecture.exact_SLM_location_tuple(
                final_mapping[q])
            vectors[i] = Movement(q, q_x, site_x, q_y, site_y)
        return vectors

    def nx_graph(self, vectors: list) -> nx.Graph:
        G = nx.Graph()
        # each node represents an index into `vectors`
        G.add_nodes_from(range(len(vectors)))

        for i in range(len(vectors)):
            for j in range(i+1, len(vectors)):
                if not self.compatible_2D(vectors[i], vectors[j]):
                    G.add_edge(i, j)
        return G

    def collect_violation(self, vectors: list) -> list[(int, int)]:
        violations = []
        for i in range(len(vectors)):
            for j in range(i+1, len(vectors)):
                if not self.compatible_2D(vectors[i], vectors[j]):
                    violations.append((i, j))
        return violations

    def compatible_2D(self, a: Movement, b: Movement) -> bool:
        """
        check if move a and b can be performed simultaneously
        """

        a_x1, a_y1, a_x2, a_y2 = a.start_x, a.start_y, a.end_x, a.end_y
        b_x1, b_y1, b_x2, b_y2 = b.start_x, b.start_y, b.end_x, b.end_y

        # x-axis
        if a_x1 == b_x1 and a_y1 != b_y1:
            return False
        if a_y1 == b_y1 and a_x1 != b_x1:
            return False
        if a_x1 < b_x1 and a_y1 >= b_y1:
            return False
        if a_x1 > b_x1 and a_y1 <= b_y1:
            return False

        # y-axis
        if a_x2 == b_x2 and a_y2 != b_y2:
            return False
        if a_y2 == b_y2 and a_x2 != b_x2:
            return False
        if a_x2 < b_x2 and a_y2 >= b_y2:
            return False
        if a_x2 > b_x2 and a_y2 <= b_y2:
            return False
        return True
