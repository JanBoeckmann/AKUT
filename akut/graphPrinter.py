import networkx as nx
from pyvis.network import Network


class GraphPrinter:
    def __init__(self, graph_works_filename, graph_fail_filename):
        self.graph_works = self._read_graph_from_file(graph_works_filename)
        self.graph_fail = self._read_graph_from_file(graph_fail_filename)

    def _read_graph_from_file(self, filename):
        return nx.read_edgelist(filename, create_using=nx.DiGraph())

    def print_graph_works(self, visualization_size_x, visualization_size_y, filename):
        net = Network(visualization_size_x, visualization_size_y, directed=True)
        net.toggle_physics(False)
        # drawn_graph = self._hand_over_network_from_nx()

        net.from_nx(self.graph_works)

        xmax = 0
        xmin = 9999999999
        ymax = 0
        ymin = 9999999999
        for n in net.nodes:
            x = int(n["id"].split(",")[0])
            y = int(n["id"].split(",")[1])
            if x > xmax:
                xmax = x
            if x < xmin:
                xmin = x
            if y > ymax:
                ymax = y
            if y < ymin:
                ymin = y

        for n in net.nodes:
            # n["group"] = "source"
            x = int(n["id"].split(",")[0])
            y = int(n["id"].split(",")[1])
            n["x"] = (x - xmin) * 10
            n["y"] = (y - ymin) * 10
            n["label"] = " "

        # net = self._adjust_positions(net)

        net.show(filename)

    def print_graph_fail(self, visualization_size_x, visualization_size_y, filename):
        net = Network(visualization_size_x, visualization_size_y, directed=True)
        net.toggle_physics(False)
        # drawn_graph = self._hand_over_network_from_nx()

        net.from_nx(self.graph_fail)

        net_works = Network(visualization_size_x, visualization_size_y, directed=True)
        # drawn_graph = self._hand_over_network_from_nx()

        net_works.from_nx(self.graph_works)

        xmax = 0
        xmin = 9999999999
        ymax = 0
        ymin = 9999999999
        for n in net.nodes:
            x = int(n["id"].split(",")[0])
            y = int(n["id"].split(",")[1])
            if x > xmax:
                xmax = x
            if x < xmin:
                xmin = x
            if y > ymax:
                ymax = y
            if y < ymin:
                ymin = y

        remember_works_node_names = set()
        for m in net_works.nodes:
            remember_works_node_names.add(m["id"])

        for n in net.nodes:
            # n["group"] = "source"
            x = int(n["id"].split(",")[0])
            y = int(n["id"].split(",")[1])
            n["x"] = (x - xmin) * 10
            n["y"] = (y - ymin) * 10
            n["label"] = " "

            if n["id"] in remember_works_node_names:
                n["group"] = "same"
            else:
                n["group"] = "diff"
                # n["color"] = "red"

            for cycle in nx.simple_cycles(self.graph_fail):
                for cn in cycle:
                    if n["id"] == cn:
                        n["group"] = "cycle"

        # net = self._adjust_positions(net)

        net.show(filename)
