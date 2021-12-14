import networkx as nx

class GraphSaver:
    def __init__(self, graph):
        self.graph = graph


    def transform_node_names_to_string(self):
        node_name_mapping = dict()
        for n in self.graph.nodes():
            node_name_mapping[n] = ",".join([str(s) for s in n])
        drawn_graph = self.graph.copy()
        drawn_graph = nx.relabel_nodes(drawn_graph, node_name_mapping)
        return drawn_graph

    def save_graph_as_gml(self, filename):
        drawn_graph = self.transform_node_names_to_string()
        drawn_graph.remove_node("-1,-1")
        for (n1, n2, d) in drawn_graph.edges(data=True):
            d.clear()
        nx.write_edgelist(drawn_graph, filename)