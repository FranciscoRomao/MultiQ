
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

    def compatible_2D(self, a: Movement, b: Movement) -> bool:
        """
        check if move a and b can be performed simultaneously
        """
        if a.start_x == b.start_x and a.end_x != b.end_x:
            return False
        if a.end_x == b.end_x and a.start_x != b.start_x:
            return False
        if a.start_x < b.start_x and a.end_x >= b.end_x:
            return False
        if a.start_x > b.start_x and a.end_x <= b.end_x:
            return False

        if a.start_y == b.start_y and a.end_y != b.end_y:
            return False
        if a.end_y == b.end_y and a.start_y != b.start_y:
            return False
        if a.start_y < b.start_y and a.end_y >= b.end_y:
            return False
        if a.start_y > b.start_y and a.end_y <= b.end_y:
            return False


        return True
