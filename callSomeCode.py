from akut.graphPrinter import GraphPrinter
import networkx as nx

gp = GraphPrinter("test2.edgelist", "test2.edgelist")
gp.print_graph_works(800, 1200, "works.html")

gp.print_graph_fail(800, 1200, "fails.html")

# print("cycles in fail graph:", nx.simple_cycles(gp.graph_fail))

# for n in nx.simple_cycles(gp.graph_fail):
#     print(n)