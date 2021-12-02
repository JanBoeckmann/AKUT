import gurobipy as gurobi
import networkx as nx
import operator
import matplotlib as plt
import datetime

class ipEquilibriumWaterLevels:
    def __init__(self, ratios, geodesicHeight, area, timeSteps, rain, massnahmenOnNode, allAuffangbecken, allLeitgraeben, all_buildings, optimization_parameters, initialSolution, threshold_for_gefahrenklasse, massnahmen_kataster, all_kataster):
        print("started: " + str(datetime.datetime.now()))
        self.ratios = ratios
        self.geodesicHeight = geodesicHeight
        self.area = area
        self.timeSteps = timeSteps
        self.rain = rain
        print("Regenmenge:", self.rain)
        self.massnahmenOnNode = massnahmenOnNode
        self.allAuffangbecken = allAuffangbecken
        self.allLeitgraeben = allLeitgraeben
        self.all_buildings = all_buildings
        self.optimization_parameters = optimization_parameters
        self.initialSolution = initialSolution
        self.epsilon = 0.01
        self.threshold_for_gefahrenklasse = threshold_for_gefahrenklasse
        self.massnahmen_kataster = massnahmen_kataster
        self.all_kataster = all_kataster
        self.all_kataster_green, self.all_kataster_yellow, self.all_kataster_red, self.all_kataster_black = self.compute_kataster_categories()
        # print("entering function createGraph")
        self.originalGraph = self.createGraph()
        self.original_undirected_graph = self.originalGraph.to_undirected()
        # print("entering function compute_total_volume")
        self.total_volume = self.compute_total_volume()
        self.objectiveValuePerNode = self.computeObjectiveValuePerNode()
        self.nodeContainsAuffangbecken = self.computeNodeContainsAuffangbecken()
        self.nodeContainsLeitgraben = self.computeNodeContainsLeitgraben()
        if "genauigkeitDerGeodaetischenHoeheIncm" in self.optimization_parameters:
            self.compound_exactness = self.optimization_parameters["genauigkeitDerGeodaetischenHoeheIncm"] / 100
        else:
            self.compound_exactness = 0.05 #in Meters
        # print("compute compounded graph")
        self.cc_graph, self.cc_area, self.cc_geodesic_height, self.cc_ratios, self.connected_components_as_mapping_with_representation, self.mapping_representator_per_node = self.compute_compounded_graph()
        # print(self.cc_ratios)
        self.extendedGraph = self.createExtendedGraph()
        self.printSolutions = False
        self.flooded, self.activeNodes, self.waterHeight, self.auffangbecken_solution, self.leitgraeben_solution, self.flow_through_nodes, self.handlungsbedarf = self.solve()
        self.backwards_transformation_to_original_graph()

        print("solved: " + str(datetime.datetime.now()))
        self.print_outputs()


    def print_outputs(self):
        print("Anzahl der Gebäude:", len(self.all_buildings))
        print("Fläche aller Knoten:", sum(self.cc_area.values()))
        print("Anzahl der Knoten vor concatenate: ", self.originalGraph.number_of_nodes())
        print("Anzahl der Knoten nach concatenate: ", self.cc_graph.number_of_nodes())
        print("Fläche des source node:", self.cc_area[(-1, -1)])
        heights = list(self.cc_geodesic_height.values())
        heights.remove(max(heights)) #remove height of (-1, -1)
        print("Maximaler Höhenunterschied aller Knoten außer source node:", max(heights) - min(heights))
        print("Anazhl der Knoten vor concatenate: ", self.originalGraph.number_of_nodes())

    def myround(self, x, base=5):
        return base * round(x / base)

    def createGraph(self):
        myGraph = nx.DiGraph()
        for i in self.geodesicHeight.keys():
            myGraph.add_node(i)
        myGraph.add_edges_from(self.ratios.keys())

        return myGraph

    def getRootNode(self, G):
        indegreeZero = [n for n, d in G.in_degree() if d == 0]
        return indegreeZero

    def compute_total_volume(self):
        total_volume = 0
        for n in self.originalGraph.nodes:
            total_volume = total_volume + self.rain * self.area[n]
        return total_volume

    def getNodesInAscendingGeodesicHeight(self):
        sortedNodes = sorted(self.geodesicHeight.items(), key=operator.itemgetter(1))
        return sortedNodes

    def getParentNodeWithMinimumGeodesicHeight(self, graph, node):
        parentNode = (0, 0)
        geodesicHeight = 9999999
        for p in graph.predecessors(node):
            if self.geodesicHeight[p] < geodesicHeight:
                parentNode = p
                geodesicHeight = self.geodesicHeight[p]
        return parentNode

    def compute_compounded_graph(self):
        def dict_compare(d1, d2):
            d1_keys = set(d1.keys())
            d2_keys = set(d2.keys())
            shared_keys = d1_keys.intersection(d2_keys)
            same = set(o for o in shared_keys if d1[o] == d2[o])
            return same

        def split_up_into_groups_of_massnahmen():
            all_nodes_as_set = set()
            for n in self.originalGraph.nodes:
                if n != (-1, -1):
                    all_nodes_as_set.add(n)
            nodes_paired_after_same_combination_of_massnahmen = []
            new_combination_of_massnahmen = set()
            for n in all_nodes_as_set:
                if self.massnahmenOnNode[n] == '':
                    new_combination_of_massnahmen.add(n)
            all_nodes_as_set = all_nodes_as_set - new_combination_of_massnahmen
            nodes_paired_after_same_combination_of_massnahmen.append(new_combination_of_massnahmen)
            while all_nodes_as_set:
                actual_node = all_nodes_as_set.pop()
                new_combination_of_massnahmen = set()
                new_combination_of_massnahmen.add(actual_node)
                for n in all_nodes_as_set:
                    if len(self.massnahmenOnNode[actual_node]) == len(self.massnahmenOnNode[n]):
                        add_node_n_to_component = True
                        for key_actual, m_actual in self.massnahmenOnNode[actual_node].items():
                            found_massnahme_in_node_n = False
                            for key_n, m_n in self.massnahmenOnNode[n].items():
                                if len(dict_compare(m_actual, m_n)) == 2:
                                    found_massnahme_in_node_n = True
                            if not found_massnahme_in_node_n:
                                add_node_n_to_component = False
                        if add_node_n_to_component:
                            new_combination_of_massnahmen.add(n)
                nodes_paired_after_same_combination_of_massnahmen.append(new_combination_of_massnahmen)
                all_nodes_as_set = all_nodes_as_set - new_combination_of_massnahmen
            print("end while in create compounded graph")
            return nodes_paired_after_same_combination_of_massnahmen

        def compute_connected_components():
            nodes_paired_after_same_combination_of_massnahmen = split_up_into_groups_of_massnahmen()
            print("length of nodes_paired_after_same_combination_of_massnahmen:", len(nodes_paired_after_same_combination_of_massnahmen))
            connected_components = []
            for comb in nodes_paired_after_same_combination_of_massnahmen:
                nodes_grouped_by_geodesic_height = dict()

                for n in comb:
                    rounded_geodesic_height = self.myround(self.geodesicHeight[n], self.compound_exactness)
                    if rounded_geodesic_height in nodes_grouped_by_geodesic_height.keys():
                        nodes_grouped_by_geodesic_height[rounded_geodesic_height].add(n)
                    else:
                        nodes_grouped_by_geodesic_height[rounded_geodesic_height] = set()
                        nodes_grouped_by_geodesic_height[rounded_geodesic_height].add(n)
                connected_components_in_this_combination = []
                for gh in nodes_grouped_by_geodesic_height.keys():
                    induced_subgraph = self.original_undirected_graph.subgraph(nodes_grouped_by_geodesic_height[gh])
                    connected_components_in_this_combination.append(nx.connected_components(induced_subgraph))
                connected_components_in_this_combination_without_single_nodes = []
                for c in connected_components_in_this_combination:
                    for sc in c:
                        if len(sc) > 1:
                            connected_components_in_this_combination_without_single_nodes.append(sc)
                if connected_components_in_this_combination_without_single_nodes:
                    connected_components = connected_components + connected_components_in_this_combination_without_single_nodes
            return connected_components

        def connected_components_to_mapping():
            connected_components_as_mapping_with_representation = dict()
            for c in connected_components:
                representative_node = c.pop()
                connected_components_as_mapping_with_representation[representative_node] = c
                c.add(representative_node)
            return connected_components_as_mapping_with_representation

        connected_components = compute_connected_components()
        connected_components_as_mapping_with_representation = connected_components_to_mapping()

        # print("test1")

        mapping_representator_per_node =dict()
        for representator_node, rest_of_cc in connected_components_as_mapping_with_representation.items():
            for n in rest_of_cc:
                mapping_representator_per_node[n] = representator_node

        # print("test2")

        cc_graph = self.originalGraph.copy()
        cc_geodesic_height = self.geodesicHeight.copy()
        cc_area = self.area.copy()
        cc_ratios = dict()

        # print("test3")
        print(len(connected_components_as_mapping_with_representation))

        #merge nodes in cc_graph, adjust area and geodesic height
        i = 0
        for representator_node, rest_of_cc in connected_components_as_mapping_with_representation.items():
            i = i+1
            # print(i)
            for n in rest_of_cc:
                cc_graph = nx.contracted_nodes(cc_graph, representator_node, n, self_loops=False)
                cc_area[representator_node] = cc_area[representator_node] + cc_area[n]
                if n != representator_node:
                    del cc_area[n]
                    del cc_geodesic_height[n]
            cc_geodesic_height[representator_node] = self.myround(cc_geodesic_height[representator_node], self.compound_exactness)

        # print("test4")

        for e in self.originalGraph.edges:
            original_start_node = e[0]
            original_end_node = e[1]
            if original_start_node in mapping_representator_per_node:
                new_start_node = mapping_representator_per_node[original_start_node]
            else:
                new_start_node = original_start_node
            if original_end_node in mapping_representator_per_node:
                new_end_node = mapping_representator_per_node[original_end_node]
            else:
                new_end_node = original_end_node
            if (new_start_node, new_end_node) in cc_ratios:
                cc_ratios[(new_start_node, new_end_node)] = cc_ratios[(new_start_node, new_end_node)] + self.ratios[(original_start_node, original_end_node)]
            else:
                cc_ratios[(new_start_node, new_end_node)] = self.ratios[(original_start_node, original_end_node)]

        return cc_graph, cc_area, cc_geodesic_height, cc_ratios, connected_components_as_mapping_with_representation, mapping_representator_per_node

    def createExtendedGraph(self):
        myExtendedGraph = self.cc_graph.copy()
        for e in self.cc_graph.edges:
            myExtendedGraph.add_edge(e[1], e[0])
            self.cc_ratios[(e[1], e[0])] = self.cc_ratios[e]
        return myExtendedGraph

    def drawExtendedGraph(self):
        nx.draw(self.extendedGraph)
        plt.pyplot.show()

    def computeObjectiveValuePerNode(self):
        objectiveValuePerNode = dict()
        for n in self.originalGraph.nodes:
            if n == (-1, -1):
                objectiveValuePerNode[n] = 0
            else:
                objectiveValue = 0
                if self.massnahmenOnNode[n]:
                    for key, massnahme in self.massnahmenOnNode[n].items():
                        if massnahme["type"] == "building":
                            objectiveValue = objectiveValue + 1
                objectiveValuePerNode[n] = objectiveValue
        return objectiveValuePerNode

    def computeNodeContainsAuffangbecken(self):
        nodeContainsAuffangbecken = dict()
        for n in self.originalGraph.nodes:
            if n == (-1, -1):
                nodeContainsAuffangbecken[n] = 0
            else:
                containsAuffangbecken = 0
                if self.massnahmenOnNode[n]:
                    for key, massnahme in self.massnahmenOnNode[n].items():
                        if massnahme["type"] == "auffangbecken":
                            containsAuffangbecken = massnahme["id"]
                nodeContainsAuffangbecken[n] = containsAuffangbecken
        return nodeContainsAuffangbecken

    def computeNodeContainsLeitgraben(self):
        nodeContainsLeitgraben = dict()
        for n in self.originalGraph.nodes:
            if n == (-1, -1):
                nodeContainsLeitgraben[n] = 0
            else:
                containsLeitgraben = 0
                if self.massnahmenOnNode[n]:
                    for key, massnahme in self.massnahmenOnNode[n].items():
                        if massnahme["type"] == "leitgraben":
                            containsLeitgraben = massnahme["id"]
                nodeContainsLeitgraben[n] = containsLeitgraben
        return nodeContainsLeitgraben

    def compute_kataster_categories(self):
        all_kataster_green = set()
        all_kataster_yellow = set()
        all_kataster_red = set()
        all_kataster_black = set()
        for kataster in self.all_kataster:
            if self.all_kataster[kataster]['additionalCost'] == 0:
                all_kataster_green.add(kataster)
            elif self.all_kataster[kataster]['additionalCost'] == 1:
                all_kataster_yellow.add(kataster)
            elif self.all_kataster[kataster]['additionalCost'] == 2:
                all_kataster_red.add(kataster)
            elif self.all_kataster[kataster]['additionalCost'] == 3:
                all_kataster_black.add(kataster)
        return all_kataster_green, all_kataster_yellow, all_kataster_red, all_kataster_black

    def solve(self):
        def getTotalArea():
            totalArea = 0
            for n in self.cc_graph.nodes:
                totalArea = totalArea + self.cc_area[n]
            return totalArea

        def declareVariables():
            #flows
            for e in self.extendedGraph.edges:
                for t in range(1, self.timeSteps + 1):
                    flows[e, t] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="f_" + str(e[0]) + "_" + str(e[1]) + "^" + str(t))

            #excess
            for n in self.extendedGraph.nodes:
                for t in range(1, self.timeSteps + 1):
                    excess[n, t] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="F_" + str(n) + "^" + str(t))

            #waterHeight
            for n in self.extendedGraph.nodes:
                for t in range(0, self.timeSteps + 1):
                    waterHeight[n, t] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="h_" + str(n) + "^" + str(t))

            #waterAmount
            for n in self.extendedGraph.nodes:
                for t in range(0, self.timeSteps + 1):
                    waterAmount[n, t] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="y_" + str(n) + "^" + str(t))

            # flooded Nodes
            for n in self.extendedGraph.nodes:
                for t in range(0, self.timeSteps + 1):
                    floodedNodes[n, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="x_" + str(n) + "^" + str(t))

            #activeArc
            for e in self.extendedGraph.edges:
                for t in range(1, self.timeSteps + 1):
                    activeArc[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="a_" + str(e[0]) + "_" + str(e[1]) + "^" + str(t))

            #fullArc
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    fullArc[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="gamma_" + str(e[0]) + "_" + str(e[1]) + "^" + str(t))

            #deactivateArc
            for e in removableEdges:
                for t in range(1, self.timeSteps + 1):
                    deactivateArc[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="d_" + str(e[0]) + "_" + str(e[1]) + "^" + str(t))

            #decisionVariableForAuffangbecken
            for auffangbeckenId in self.allAuffangbecken:
                decisionAuffangbecken[auffangbeckenId] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="auffangbecken_" + str(auffangbeckenId))

            #decisionVariableForLeitgraeben
            for leitgrabenId in self.allLeitgraeben:
                decisionLeitgraben[leitgrabenId] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="leitgraben_" + str(leitgrabenId))

            # height_difference_through_auffangbecken
            for auffangbeckenId in self.allAuffangbecken:
                height_difference_through_auffangbecken[auffangbeckenId] = myModel.addVar(lb=-gurobi.GRB.INFINITY, vtype=gurobi.GRB.CONTINUOUS, name="height_difference_through_auffangbecken_" + str(auffangbeckenId))

            # height_difference_through_leitgraben
            for leitgrabenId in self.allLeitgraeben:
                height_difference_through_leitgraben[leitgrabenId] = myModel.addVar(lb=-gurobi.GRB.INFINITY, vtype=gurobi.GRB.CONTINUOUS, name="height_difference_through_leitgraben_" + str(leitgrabenId))

            #geodesicHeightAsVariable
            for n in self.extendedGraph.nodes:
                geodesicHeightAsVariable[n] = myModel.addVar(vtype=gurobi.GRB.CONTINUOUS, name="g_" + str(n))

            #vertiefung
            for n in self.extendedGraph.nodes:
                vertiefung[n] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="vertiefung_" + str(n))

            # maximum_geodesic_height_on_node
            for n in self.extendedGraph.nodes:
                maximum_geodesic_height_on_node[n] = myModel.addVar(vtype=gurobi.GRB.CONTINUOUS, name="maximum_geodesic_height_on_node_" + str(n))

            # minimum_geodesic_height_on_node
            for n in self.extendedGraph.nodes:
                minimum_geodesic_height_on_node[n] = myModel.addVar(lb=-gurobi.GRB.INFINITY, vtype=gurobi.GRB.CONTINUOUS, name="minimum_geodesic_height_on_node_" + str(n))

            #binary help variable for using indicator constraints for flow distribution
            for e in self.extendedGraph.edges:
                for t in range(1, self.timeSteps + 1):
                    binaryHelpForFlowDistribution[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="helpFlowDistribution_" + str(e) + "^" + str(t))

            #original Direction
            for e in self.cc_graph.edges:
                originalDirection[e] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="o_" + str(e))

            #binary help for original and full
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    binaryHelpForOriginal1AndFull1[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="hO1F1_" + str(e) + "^" + str(t))
                    binaryHelpForOriginal1AndFull0[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="hO1F0_" + str(e) + "^" + str(t))
                    binaryHelpForOriginal0AndFull1[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="hO0F1_" + str(e) + "^" + str(t))
                    binaryHelpForOriginal0AndFull0[e, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="hO0F0_" + str(e) + "^" + str(t))

            #binary for flooded building
            for b in self.all_buildings:
                for t in range(1, self.timeSteps + 1):
                    max_water_level[b, t] = myModel.addVar(vtype=gurobi.GRB.CONTINUOUS, name="max_water_level_" + str(b) + "^" + str(t))
                    schadensklasse = self.all_buildings[b]["schadensklasse"]
                    for k in range(1, 5):
                        danger_class[k, b, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="damage_class_" + str(k) + "_" + str(b) + "^" + str(t), obj=self.optimization_parameters["gefahrenklasse" + str(k) + "schadensklasse" + str(schadensklasse)] * self.optimization_parameters["gewichtung" + self.all_buildings[b]["akteur"]])
                    danger_class[0, b, t] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="damage_class_0_" + str(b) + "^" + str(t))

            #allowed to build on kataster
            for k in self.all_kataster:
                kataster_allowed[k] = myModel.addVar(vtype=gurobi.GRB.BINARY, name="kataster_allowed" + str(k))

        def addConstraints():
            #constraint for the excess
            for n in self.extendedGraph.nodes:
                for t in range(1, self.timeSteps + 1):
                    myModel.addConstr(excess[n, t], gurobi.GRB.EQUAL,  gurobi.quicksum(flows[e, t] for e in self.extendedGraph.in_edges(n)) - gurobi.quicksum(flows[e, t] for e in self.extendedGraph.out_edges(n)) + self.rain * self.cc_area[n], name="excess_" + str(n) + "_" + str(t))

            # #Constraint for geodesic Height as variable with Auffangbecken and Leitgraben
            # for n in self.extendedGraph.nodes:
            #     if self.nodeContainsAuffangbecken[n] != 0:
            #         myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, self.cc_geodesic_height[n] - self.allAuffangbecken[self.nodeContainsAuffangbecken[n]]["depth"] * decisionAuffangbecken[self.nodeContainsAuffangbecken[n]], name="geodesicHeightAsVariable_" + str(n))
            #     elif self.nodeContainsLeitgraben[n] != 0:
            #         sign = 1
            #         if self.allLeitgraeben[self.nodeContainsLeitgraben[n]]["leitgrabenOderBoeschung"] == "boeschung":
            #             sign = -1
            #         myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, self.cc_geodesic_height[n] - sign*self.allLeitgraeben[self.nodeContainsLeitgraben[n]]["depth"] * decisionLeitgraben[self.nodeContainsLeitgraben[n]], name="geodesicHeightAsVariable_" + str(n))
            #     else:
            #         myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, self.cc_geodesic_height[n], name="geodesicHeightAsVariable_" + str(n))

            #set height_difference_through_auffangbecken
            for a in self.allAuffangbecken:
                myModel.addConstr(height_difference_through_auffangbecken[a], gurobi.GRB.EQUAL, -1 * self.allAuffangbecken[a]["depth"] * decisionAuffangbecken[a], name="height_difference_through_auffangbecken_" + str(a))

            #set height_difference_through_leitgraben (for both leitgraeben and boeschungen)
            for l in self.allLeitgraeben:
                sign = -1
                if self.allLeitgraeben[l]["leitgrabenOderBoeschung"] == "boeschung":
                    sign = 1
                myModel.addConstr(height_difference_through_leitgraben[l], gurobi.GRB.EQUAL, sign * self.allLeitgraeben[l]["depth"] * decisionLeitgraben[l], name="height_difference_through_leitgraben_" + str(l))

            #set vertiefung to 1 if there is a auffangbecken or leitgraben built
            for n in self.extendedGraph.nodes:
                if n != (-1, -1):
                    auffangbecken_on_node = []
                    leitgraeben_on_node = []
                    boeschungen_on_node = []
                    for m in self.massnahmenOnNode[n]:
                        if self.massnahmenOnNode[n][m]["type"] == 'auffangbecken':
                            auffangbecken_on_node.append(self.massnahmenOnNode[n][m]["id"])
                        if self.massnahmenOnNode[n][m]["type"] == 'leitgraben':
                            if self.allLeitgraeben[self.massnahmenOnNode[n][m]["id"]]["leitgrabenOderBoeschung"] == "leitgraben":
                                leitgraeben_on_node.append(self.massnahmenOnNode[n][m]["id"])
                            else:
                                boeschungen_on_node.append(self.massnahmenOnNode[n][m]["id"])
                    #force vertiefung to 0 if no auffangbecken or leitgraben is built
                    myModel.addConstr(vertiefung[n], gurobi.GRB.LESS_EQUAL, gurobi.quicksum(decisionAuffangbecken[a] for a in auffangbecken_on_node) + gurobi.quicksum(decisionLeitgraben[l] for l in leitgraeben_on_node))
                    #force vertiefung to 1 if auffangbecken or leitgraben is built
                    for a in auffangbecken_on_node:
                        myModel.addConstr(vertiefung[n], gurobi.GRB.GREATER_EQUAL, decisionAuffangbecken[a])
                    for l in leitgraeben_on_node:
                        myModel.addConstr(vertiefung[n], gurobi.GRB.GREATER_EQUAL, decisionLeitgraben[l])

                    # if vertiefung is 1, the minimum possible geodesic height wins
                    # myModel.addGenConstrIndicator(vertiefung[n], True, geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, minimum_geodesic_height_on_node[n], name="IndicatorConstraintForGeodesicHeightOfVertiefungIs1_" + str(n))
                    #
                    # # if vertiefung is 0, the maximum possible geodesic height wins
                    # myModel.addGenConstrIndicator(vertiefung[n], False, geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, maximum_geodesic_height_on_node[n], name="IndicatorConstraintForGeodesicHeightOfVertiefungIs0_" + str(n))

                    # candidates_for_max_height = [self.cc_geodesic_height[n] + self.allLeitgraeben[b]["depth"] * decisionLeitgraben[b] for b in boeschungen_on_node] + [self.cc_geodesic_height[n]]
                    # candidates_for_min_height = [self.cc_geodesic_height[n] - self.allAuffangbecken[a]["depth"] * decisionAuffangbecken[a] for a in auffangbecken_on_node] + [self.cc_geodesic_height[n] - self.allLeitgraeben[l]["depth"] * decisionLeitgraben[l] for l in leitgraeben_on_node] + [self.cc_geodesic_height[n]]
                    candidates_for_max_height = [height_difference_through_leitgraben[b] for b in boeschungen_on_node] + [0]
                    candidates_for_min_height = [height_difference_through_auffangbecken[a] for a in auffangbecken_on_node] + [height_difference_through_leitgraben[l] for l in leitgraeben_on_node] + [0]

                    max_geodesic_height_gain = max([self.allLeitgraeben[b]["depth"] for b in boeschungen_on_node] + [0])
                    max_geodesic_height_reduction = max([self.allLeitgraeben[l]["depth"] for l in leitgraeben_on_node] + [self.allAuffangbecken[a]["depth"] for a in auffangbecken_on_node] + [0])

                    #set maximum and minimum possible geodesic height
                    myModel.addConstr(maximum_geodesic_height_on_node[n] == gurobi.max_(candidates_for_max_height), name='maximum_geodesic_height_on_node_' + str(n))
                    myModel.addConstr(minimum_geodesic_height_on_node[n] == gurobi.min_(candidates_for_min_height), name='minimum_geodesic_height_on_node_' + str(n))

                    # those hold in general
                    myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.GREATER_EQUAL, self.cc_geodesic_height[n] + minimum_geodesic_height_on_node[n])
                    myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.LESS_EQUAL, self.cc_geodesic_height[n] + maximum_geodesic_height_on_node[n])

                    #if vertiefung = 1, force geodesic height to minimal value. This constraint is deactivated if vertiefung  = 0
                    myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.LESS_EQUAL, self.cc_geodesic_height[n] + minimum_geodesic_height_on_node[n] + (1-vertiefung[n]) * (max_geodesic_height_gain + max_geodesic_height_reduction))

                    # if vertiefung = 0, force geodesic height to maximal value. This constraint is deactivated if vertiefung  = 1
                    myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.GREATER_EQUAL, self.cc_geodesic_height[n] + maximum_geodesic_height_on_node[n] - (vertiefung[n]) * (max_geodesic_height_gain + max_geodesic_height_reduction))


                # set geodesic height of (-1, -1) to its height in the cc_graph
                else:
                    myModel.addConstr(geodesicHeightAsVariable[n], gurobi.GRB.EQUAL, self.cc_geodesic_height[n], name="geodesicHeightAsVariable_" + str(n))

            #for debugging purposes. Set this parameter to true if every massnahme should be built
            build_everything = False
            if build_everything:
                for a in self.allAuffangbecken:
                    myModel.addConstr(decisionAuffangbecken[a] == 1)

                for l in self.allLeitgraeben:
                    myModel.addConstr(decisionLeitgraben[l] == 1)


            #update constraint for water amounts
            for n in self.extendedGraph.nodes:
                for t in range(1, self.timeSteps + 1):
                    myModel.addConstr(waterAmount[n, t], gurobi.GRB.EQUAL, waterAmount[n, t-1] + excess[n, t], name="updateWaterAmountsInNextTimeStep_" + str(n) + "_" + str(t))

            #initial constraint for water amounts
            for n in self.extendedGraph.nodes:
                myModel.addConstr(waterAmount[n, 0], gurobi.GRB.EQUAL, 0, name="initialConstraintForWaterAmounts_" + str(n))

            #constraint for water height
            for n in self.extendedGraph.nodes:
                for t in range(0, self.timeSteps + 1):
                    myModel.addConstr(waterHeight[n, t] * self.cc_area[n], gurobi.GRB.EQUAL, waterAmount[n, t], name="ConnectWaterHeightToWaterAmount_" + str(n) + "_" + str(t))

            # constraint for floodedNodes
            for n in self.extendedGraph.nodes:
                for t in range(0, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(floodedNodes[n, t], False, waterHeight[n, t], gurobi.GRB.EQUAL, 0, name="IndicatorConstraintForFloodedNodes_" + str(n) + "_" + str(t))

            #deactivating edges and active edges
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    if e in removableEdges:
                        myModel.addConstr(activeArc[e, t] + activeArc[(e[1], e[0]), t], gurobi.GRB.EQUAL, 1 - deactivateArc[e, t], name="deactivateArcs_" + str(e) + "_" + str(t))
                    else:
                        myModel.addConstr(activeArc[e, t] + activeArc[(e[1], e[0]), t], gurobi.GRB.EQUAL, 1, name="deactivateArcs_" + str(e) + "_" + str(t))

            #constraints for flows: no flow on inactive arc
            for e in self.extendedGraph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(activeArc[e, t], False, flows[e, t], gurobi.GRB.LESS_EQUAL, 0, name="IndicatorNoFlowOnInactiveArc_" + str(e) + "_" + str(t))

            #binary help for flow distribution
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addConstr(binaryHelpForFlowDistribution[e, t], gurobi.GRB.GREATER_EQUAL, activeArc[e, t] - fullArc[e, t], name="BinaryHelpVariableForFlowDistribution_" + str(e) + "_" + str(t))
                    myModel.addConstr(binaryHelpForFlowDistribution[e, t], gurobi.GRB.LESS_EQUAL, activeArc[e, t], name="BinaryHelpVariableForFlowDistribution_" + str(e) + "_" + str(t))
                    myModel.addConstr(binaryHelpForFlowDistribution[e, t], gurobi.GRB.LESS_EQUAL, 1 - fullArc[e, t], name="BinaryHelpVariableForFlowDistribution_" + str(e) + "_" + str(t))
                    myModel.addConstr(binaryHelpForFlowDistribution[(e[1], e[0]), t], gurobi.GRB.GREATER_EQUAL, activeArc[(e[1], e[0]), t] - fullArc[e, t], name="BinaryHelpVariableForFlowDistributionReversed_" + str(e) + "_" + str(t))
                    myModel.addConstr(binaryHelpForFlowDistribution[(e[1], e[0]), t], gurobi.GRB.LESS_EQUAL, activeArc[(e[1], e[0]), t], name="BinaryHelpVariableForFlowDistributionReversed_" + str(e) + "_" + str(t))
                    myModel.addConstr(binaryHelpForFlowDistribution[(e[1], e[0]), t], gurobi.GRB.LESS_EQUAL, 1 - fullArc[e, t], name="BinaryHelpVariableForFlowDistributionReversed_" + str(e) + "_" + str(t))

            # Ratios of Flows
            for n in self.extendedGraph.nodes:
                for t in range(1, self.timeSteps + 1):
                    successors = []
                    for s in self.extendedGraph.successors(n):
                        successors.append(s)
                    if len(successors) >= 2:
                        for p1 in range(len(successors)):
                            for p2 in range(p1 + 1, len(successors)):
                                # #old constraints
                                myModel.addGenConstrIndicator(binaryHelpForFlowDistribution[(n, successors[p2]), t], True, flows[(n, successors[p1]), t] - (self.cc_ratios[(n, successors[p1])] / self.cc_ratios[(n, successors[p2])] * flows[(n, successors[p2]), t]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")
                                myModel.addGenConstrIndicator(binaryHelpForFlowDistribution[(n, successors[p1]), t], True, flows[(n, successors[p2]), t] - (self.cc_ratios[(n, successors[p2])] / self.cc_ratios[(n, successors[p1])] * flows[(n, successors[p1]), t]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")

                                # myModel.addGenConstrIndicator(binaryHelpForFlowDistribution[(n, successors[p2]), t], True, round(self.cc_ratios[(n, successors[p2])], 6) * 1e+6 * flows[(n, successors[p1]), t] - (round(self.cc_ratios[(n, successors[p1])], 6) * 1e+6 * flows[(n, successors[p2]), t]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")
                                # myModel.addGenConstrIndicator(binaryHelpForFlowDistribution[(n, successors[p1]), t], True, round(self.cc_ratios[(n, successors[p1])], 6) * 1e+6 * flows[(n, successors[p2]), t] - (round(self.cc_ratios[(n, successors[p2])], 6) * 1e+6 * flows[(n, successors[p1]), t]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")

            #originalDirection
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(originalDirection[e], True, geodesicHeightAsVariable[e[0]] - geodesicHeightAsVariable[e[1]], gurobi.GRB.GREATER_EQUAL, 0, name="originalDirectionForcedToBe0")
                    myModel.addGenConstrIndicator(originalDirection[e], False, geodesicHeightAsVariable[e[0]] - geodesicHeightAsVariable[e[1]], gurobi.GRB.LESS_EQUAL, 0, name="originalDirectionForcedToBe1")

            #set help variable for original and full
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    #11
                    myModel.addConstr(binaryHelpForOriginal1AndFull1[e, t], gurobi.GRB.GREATER_EQUAL, -1 + originalDirection[e] + fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal1AndFull1[e, t], gurobi.GRB.LESS_EQUAL, fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal1AndFull1[e, t], gurobi.GRB.LESS_EQUAL, originalDirection[e])
                    #10
                    myModel.addConstr(binaryHelpForOriginal1AndFull0[e, t], gurobi.GRB.GREATER_EQUAL, originalDirection[e] - fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal1AndFull0[e, t], gurobi.GRB.LESS_EQUAL, 1 - fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal1AndFull0[e, t], gurobi.GRB.LESS_EQUAL, originalDirection[e])
                    # 01
                    myModel.addConstr(binaryHelpForOriginal0AndFull1[e, t], gurobi.GRB.GREATER_EQUAL, - originalDirection[e] + fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal0AndFull1[e, t], gurobi.GRB.LESS_EQUAL, fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal0AndFull1[e, t], gurobi.GRB.LESS_EQUAL, 1 - originalDirection[e])
                    # 00
                    myModel.addConstr(binaryHelpForOriginal0AndFull0[e, t], gurobi.GRB.GREATER_EQUAL, 1 - originalDirection[e] - fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal0AndFull0[e, t], gurobi.GRB.LESS_EQUAL, 1 - fullArc[e, t])
                    myModel.addConstr(binaryHelpForOriginal0AndFull0[e, t], gurobi.GRB.LESS_EQUAL, 1 - originalDirection[e])

            #constraints for full arc
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    #originalDirection
                    myModel.addGenConstrIndicator(binaryHelpForOriginal1AndFull1[e, t], True, waterHeight[e[1], t] - (geodesicHeightAsVariable[e[0]] - geodesicHeightAsVariable[e[1]]), gurobi.GRB.GREATER_EQUAL, 0, name="fullArcForcedToBe0OriginalDirection")
                    myModel.addGenConstrIndicator(binaryHelpForOriginal1AndFull0[e, t], True, waterHeight[e[1], t] - (geodesicHeightAsVariable[e[0]] - geodesicHeightAsVariable[e[1]]), gurobi.GRB.LESS_EQUAL, 0, name="fullArcForcedToBe1OriginalDirection")

                    #notOriginalDirection
                    myModel.addGenConstrIndicator(binaryHelpForOriginal0AndFull1[e, t], True, waterHeight[e[0], t] - (geodesicHeightAsVariable[e[1]] - geodesicHeightAsVariable[e[0]]), gurobi.GRB.GREATER_EQUAL, 0, name="fullArcForcedToBe1NonOriginalDirection")
                    myModel.addGenConstrIndicator(binaryHelpForOriginal0AndFull0[e, t], True, waterHeight[e[0], t] - (geodesicHeightAsVariable[e[1]] - geodesicHeightAsVariable[e[0]]), gurobi.GRB.LESS_EQUAL, 0, name="fullArcForcedToBe0NonOriginalDirection")

            #constraints for effects of fullArc on the flows (indirect via height)
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(fullArc[e, t], True, geodesicHeightAsVariable[e[0]] + waterHeight[e[0], t] - (geodesicHeightAsVariable[e[1]] + waterHeight[e[1], t]), gurobi.GRB.EQUAL, 0, name="effectsOnFullArcForFlows")

            #Force all water to flow out of higher node as long as there is a non-full arc
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    #new constraint
                    myModel.addGenConstrIndicator(binaryHelpForOriginal1AndFull0[e, t], True, waterHeight[e[0], t], gurobi.GRB.EQUAL, 0, name="noWaterStoredIfThereIsStillAnActiveOutArc")
                    myModel.addGenConstrIndicator(binaryHelpForOriginal0AndFull0[e, t], True, waterHeight[e[1], t], gurobi.GRB.EQUAL, 0, name="noWaterStoredIfThereIsStillAnActiveOutArc")

            #no upwards flow on non-full arcs
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(binaryHelpForOriginal1AndFull0[e, t], True, activeArc[(e[1], e[0]), t], gurobi.GRB.EQUAL, 0, name="noUpwardsFlowOnNonFullArcs")
                    myModel.addGenConstrIndicator(binaryHelpForOriginal0AndFull0[e, t], True, activeArc[e, t], gurobi.GRB.EQUAL, 0, name="noUpwardsFlowOnNonFullArcs")

            # #just for test purposes activate all Auffangbecken
            # for auffangbeckenId in self.allAuffangbecken:
            #     myModel.addConstr(decisionAuffangbecken[auffangbeckenId], gurobi.GRB.EQUAL, 0)

            #flooded building is max of flooded nodes
            for n in self.extendedGraph.nodes:
                if n != (-1, -1):
                    for t in range(1, self.timeSteps + 1):
                        if self.massnahmenOnNode[n]:
                            for key, massnahme in self.massnahmenOnNode[n].items():
                                if massnahme["type"] == "building":
                                    myModel.addConstr(max_water_level[massnahme["id"], t], gurobi.GRB.GREATER_EQUAL, waterHeight[n, t])
            # Danger classes add up to 1
            for b in self.all_buildings:
                for t in range(1, self.timeSteps + 1):
                    myModel.addConstr(gurobi.quicksum(danger_class[k, b, t] for k in range(0, 5)), gurobi.GRB.EQUAL, 1, name="damageClassesAddUpToOne")

            # force danger classes up
            for b in self.all_buildings:
                for t in range(1, self.timeSteps + 1):
                    for k in range(0, 5):
                        myModel.addGenConstrIndicator(danger_class[k, b, t], True, max_water_level[b, t], gurobi.GRB.LESS_EQUAL, self.threshold_for_gefahrenklasse[k])

            # Constraint for budget
            myModel.addConstr(gurobi.quicksum(decisionAuffangbecken[a] * self.allAuffangbecken[a]["cost"] for a in self.allAuffangbecken) + gurobi.quicksum(decisionLeitgraben[l] * self.allLeitgraeben[l]["cost"] for l in self.allLeitgraeben), gurobi.GRB.LESS_EQUAL, self.optimization_parameters["budget"], name="budgetForAuffangbeckenUndLeitgraeben")

            # Upper bound on yellow and red kataster
            myModel.addConstr(gurobi.quicksum(kataster_allowed[k] for k in self.all_kataster_yellow), gurobi.GRB.LESS_EQUAL, self.optimization_parameters["maxAnzahlGelb"], name="maxNumberOfYellow")
            myModel.addConstr(gurobi.quicksum(kataster_allowed[k] for k in self.all_kataster_red), gurobi.GRB.LESS_EQUAL, self.optimization_parameters["maxAnzahlRot"], name="maxNumberOfRed")

            # No Massnahmen on black kataster
            for k in self.all_kataster_black:
                myModel.addConstr(kataster_allowed[k], gurobi.GRB.EQUAL, 0, name="noMassnahmenOnBlack")

            # Massnahmen on green are allowed (you dont necessarily need this constraint)
            for k in self.all_kataster_green:
                myModel.addConstr(kataster_allowed[k], gurobi.GRB.EQUAL, 1, name="massnahmenOnGreen")

            for intersection in self.massnahmen_kataster:
                if intersection[1] == "Leitgraben":
                    myModel.addConstr(kataster_allowed[intersection[3]], gurobi.GRB.GREATER_EQUAL, decisionLeitgraben[intersection[2]])
                elif intersection[1] == "Auffangbecken":
                    myModel.addConstr(kataster_allowed[intersection[3]], gurobi.GRB.GREATER_EQUAL, decisionAuffangbecken[intersection[2]])

            #If Leitgraben has depth 0, decide not to build it (this constraint is not required, but may speed up computations a bit)
            for l in self.allLeitgraeben:
                if self.allLeitgraeben[l]["depth"] == 0:
                    myModel.addConstr(decisionLeitgraben[l], gurobi.GRB.EQUAL, 0, name="LeitgraebenWithDepth0areNotBuild")

            #performance tuning constraints
            for e in self.cc_graph.edges:
                for t in range(1, self.timeSteps + 1):
                    myModel.addGenConstrIndicator(originalDirection[e], True, floodedNodes[e[1], t] - floodedNodes[e[0], t], gurobi.GRB.GREATER_EQUAL, 0, name="performanceConstraint1")
                    myModel.addGenConstrIndicator(originalDirection[e], False, floodedNodes[e[0], t] - floodedNodes[e[1], t], gurobi.GRB.GREATER_EQUAL, 0, name="performanceConstraint1")

            print("Number of Nodes: ", self.cc_graph.number_of_nodes())
            print("Start presolve non-flooded: ", datetime.datetime.now())
            cc_graph_with_maximum_possible_geodesic_height = self.cc_graph.copy()
            cc_maximum_geodesic_height = self.cc_geodesic_height.copy()
            for n in self.cc_graph.nodes:
                if n != (-1, -1):
                    maximum_additional_geodesic_height = 0
                    for massnahme in self.massnahmenOnNode[n]:
                        if self.massnahmenOnNode[n][massnahme]["type"] == "leitgraben":
                            if self.allLeitgraeben[self.massnahmenOnNode[n][massnahme]["id"]]["leitgrabenOderBoeschung"] == "boeschung":
                                if self.allLeitgraeben[self.massnahmenOnNode[n][massnahme]["id"]]["depth"] > maximum_additional_geodesic_height:
                                    maximum_additional_geodesic_height = self.allLeitgraeben[self.massnahmenOnNode[n][massnahme]["id"]]["depth"]
                    cc_maximum_geodesic_height[n] = cc_maximum_geodesic_height[n] + maximum_additional_geodesic_height
            for e in self.cc_graph.edges:
                #have to turn around edges if maximum geodesic height flips around
                if cc_maximum_geodesic_height[e[0]] < cc_maximum_geodesic_height[e[1]]:
                    cc_graph_with_maximum_possible_geodesic_height.remove_edge(e[0], e[1])
                    cc_graph_with_maximum_possible_geodesic_height.add_edge(e[1], e[0])
            counter_presolved_nodes_not_flooded = 0
            undirected_graph = cc_graph_with_maximum_possible_geodesic_height.to_undirected()
            remember_non_flooded_nodes = set()
            for n in self.cc_graph.nodes:
                can_set_the_constraint = True
                volume_needed = 0
                if n != (-1, -1):
                    if self.massnahmenOnNode[n]:
                        for key, massnahme in self.massnahmenOnNode[n].items():
                            if massnahme["type"] == "auffangbecken":
                                if self.allAuffangbecken[massnahme["id"]]["depth"] != 0:
                                    can_set_the_constraint = False
                            if massnahme["type"] == "leitgraben":
                                if self.allLeitgraeben[massnahme["id"]]["depth"] != 0:
                                    can_set_the_constraint = False
                    if can_set_the_constraint:
                        for s in nx.nodes(nx.dfs_tree(cc_graph_with_maximum_possible_geodesic_height, n)):
                            volume_needed = volume_needed + self.cc_area[s] * (cc_maximum_geodesic_height[n] - cc_maximum_geodesic_height[s])
                        if volume_needed > self.total_volume:
                            counter_presolved_nodes_not_flooded = counter_presolved_nodes_not_flooded + 1
                            remember_non_flooded_nodes.add(n)
                            for t in range(1, self.timeSteps + 1):
                                myModel.addConstr(floodedNodes[n, t], gurobi.GRB.EQUAL, 0, name="performanceConstraint2")
                                myModel.addConstr(excess[n, t], gurobi.GRB.EQUAL, 0, name="performanceConstraint2")
                        else:
                            volume_needed = 0
                            nodes_to_remove = []
                            removed_graph = undirected_graph.copy()
                            for u in undirected_graph.nodes:
                                if cc_maximum_geodesic_height[u] >= cc_maximum_geodesic_height[n] and n != u:
                                    nodes_to_remove.append(u)
                            removed_graph.remove_nodes_from(nodes_to_remove)
                            for s in nx.node_connected_component(removed_graph, n):
                                volume_needed = volume_needed + self.cc_area[s] * (cc_maximum_geodesic_height[n] - cc_maximum_geodesic_height[s])
                            if volume_needed > self.total_volume:
                                counter_presolved_nodes_not_flooded = counter_presolved_nodes_not_flooded + 1
                                remember_non_flooded_nodes.add(n)
                                for t in range(1, self.timeSteps + 1):
                                    myModel.addConstr(floodedNodes[n, t], gurobi.GRB.EQUAL, 0, name="performanceConstraint2")
                                    myModel.addConstr(excess[n, t], gurobi.GRB.EQUAL, 0, name="performanceConstraint2")
                            else:
                                for s in nx.node_connected_component(removed_graph, n):
                                    for t in range(1, self.timeSteps + 1):
                                        myModel.addConstr(floodedNodes[n, t], gurobi.GRB.LESS_EQUAL, floodedNodes[s, t], name="performanceConstraint2")
                                        myModel.addGenConstrIndicator(floodedNodes[n, t], True, waterHeight[s, t], gurobi.GRB.GREATER_EQUAL, cc_maximum_geodesic_height[n] - cc_maximum_geodesic_height[s], name="performanceConstraint2")
            print("Number of presolved non-flooded nodes: ", counter_presolved_nodes_not_flooded)
            print("End presolve non-flooded: ", datetime.datetime.now())


            counter_presolved_nodes_flooded = 0
            for n in self.cc_graph.nodes:
                if n != (-1, -1) and n not in remember_non_flooded_nodes:
                    can_set_the_constraint = True
                    if self.cc_graph.out_degree(n) == 0:
                        for m in self.cc_graph.predecessors(n):
                            if m != (-1, -1):
                                if self.massnahmenOnNode[m]:
                                    for key, massnahme in self.massnahmenOnNode[m].items():
                                        if massnahme["type"] == "auffangbecken":
                                            if self.allAuffangbecken[massnahme["id"]]["depth"] != 0:
                                                can_set_the_constraint = False
                                        if massnahme["type"] == "leitgraben":
                                            if self.allLeitgraeben[massnahme["id"]]["depth"] != 0:
                                                can_set_the_constraint = False
                    else:
                        can_set_the_constraint = False
                    if can_set_the_constraint:
                        counter_presolved_nodes_flooded = counter_presolved_nodes_flooded + 1
                        for t in range(1, self.timeSteps + 1):
                            myModel.addConstr(floodedNodes[n, t], gurobi.GRB.EQUAL, 1, name="performanceConstraint3")
            print("Number of presolved flooded nodes: ", counter_presolved_nodes_flooded)

            # this constraint sadly made it slower in the first run. Now with other performance constraints, I think it's a bit faster
            for n in self.cc_graph.nodes:
                for p in self.cc_graph.predecessors(n):
                    for s in self.cc_graph.successors(n):
                        for t in range(1, self.timeSteps + 1):
                            myModel.addConstr(fullArc[(n, s), t], gurobi.GRB.GREATER_EQUAL, fullArc[(p, n), t] - (2 - originalDirection[(p, n)] - originalDirection[(n, s)]), name="performanceConstraint4")

            # presolve Flows out of (-1, -1)
            for s in self.cc_graph.successors((-1, -1)):
                #This constraint is relaxed due to numerical issues. Without the relaxation, it might become infeasible
                myModel.addConstr(flows[((-1, -1), s), 1], gurobi.GRB.GREATER_EQUAL, self.rain * self.cc_area[(-1, -1)] * self.cc_ratios[(-1, -1), s] - 0.01, name="performanceConstraint5")

            # Performance: If a node is flooded, all outgoing arcs must be full
            for n in self.cc_graph.nodes:
                for s in self.cc_graph.successors(n):
                    myModel.addGenConstrIndicator(floodedNodes[n, t], True, fullArc[(n, s), t] - originalDirection[(n, s)], gurobi.GRB.GREATER_EQUAL, 0, name="performanceConstraint6")
                for p in self.cc_graph.predecessors(n):
                    myModel.addGenConstrIndicator(floodedNodes[n, t], True, fullArc[(p, n), t] + originalDirection[(p, n)], gurobi.GRB.GREATER_EQUAL, 1, name="performanceConstraint6")

            # Performance: If a node is not flooded, all ingoing arcs cannot be full
            for n in self.cc_graph.nodes:
                for p in self.cc_graph.predecessors(n):
                    myModel.addGenConstrIndicator(floodedNodes[n, t], False, fullArc[(p, n), t] + originalDirection[(p, n)], gurobi.GRB.LESS_EQUAL, 1, name="performanceConstraint7")
                for s in self.cc_graph.successors(n):
                    myModel.addGenConstrIndicator(floodedNodes[n, t], False, fullArc[(n, s), t] - originalDirection[(n, s)], gurobi.GRB.LESS_EQUAL, 0, name="performanceConstraint7")

        def addInitialSolutionConstraints():
            counter_initial_solution_constraints = 0
            epsilon = 0.00001
            for n in self.initialSolution["waterHeight"]:
                if n != (-1, -1):
                    can_set_the_constraint = True
                    if self.massnahmenOnNode[n]:
                        for key, massnahme in self.massnahmenOnNode[n].items():
                            if massnahme["type"] != "building":
                                can_set_the_constraint = False
                    if self.initialSolution["waterHeight"][n] > epsilon:
                            can_set_the_constraint = False
                    for s in self.cc_graph.successors(n):
                        if self.initialSolution["waterHeight"][s] > epsilon:
                            can_set_the_constraint = False
                    if can_set_the_constraint:
                        counter_initial_solution_constraints = counter_initial_solution_constraints + 1
                        for t in range(1, self.timeSteps + 1):
                            myModel.addConstr(floodedNodes[n, t], gurobi.GRB.EQUAL, 0, name="performanceConstraintInitialSolution")
            print("Number of presolved non-flooded nodes from initial solution: ", counter_initial_solution_constraints)

        def handOverStartSolution():
            if self.initialSolution is not None:
                for n in self.cc_graph:
                    if n != (-1, -1):
                        if self.initialSolution['waterHeight'][n] > self.epsilon:
                            floodedNodes[n, self.timeSteps].start = 1
                        else:
                            floodedNodes[n, self.timeSteps].start = 0


        def putActiveIntoDictionary():
            for t in range(1, self.timeSteps + 1):
                newDict = {}
                for n in self.extendedGraph.nodes:
                    v = myModel.getVarByName("h_" + str(n) + "^" + str(t))
                    if v.x == 0:
                        newDict[n] = 1
                    else:
                        newDict[n] = 0
                activeNodes[t] = newDict

        def putFloodedIntoDictionary():
            for t in range(1, self.timeSteps + 1):
                newDict = {}
                for n in self.extendedGraph.nodes:
                    v = myModel.getVarByName("x_" + str(n) + "^" + str(t))
                    newDict[n] = v.x
                flooded[t] = newDict

        def getNodesWithWaterHeightGreaterZero():
            returnedDict = {}
            for t in range(1, self.timeSteps + 1):
                newDict = {}
                for n in self.extendedGraph.nodes:
                    v = myModel.getVarByName("h_" + str(n) + "^" + str(t))
                    if v.x == 0:
                        newDict[n] = 0
                    else:
                        newDict[n] = 1
                returnedDict[t] = newDict
            return returnedDict

        def putAuffangbeckenIntoDictionary():
            newDict = dict()
            for auffangbeckenId in self.allAuffangbecken:
                v = myModel.getVarByName("auffangbecken_" + str(auffangbeckenId))
                newDict[auffangbeckenId] = v.x
            return newDict

        def putLeitgrabenIntoDictionary():
            newDict = dict()
            for leitgraben_id in self.allLeitgraeben:
                v = myModel.getVarByName("leitgraben_" + str(leitgraben_id))
                newDict[leitgraben_id] = v.x
            return newDict

        def putWaterHeightIntoDictionary():
            for t in range(1, self.timeSteps + 1):
                newDict = {}
                for n in self.extendedGraph.nodes:
                    v = myModel.getVarByName("h_" + str(n) + "^" + str(t))
                    newDict[n] = v.x
                solutionWaterHeight[t] = newDict

        def putFullArcIntoDictionary():
            returnedDict = {}
            for t in range(1, self.timeSteps + 1):
                newDict = {}
                for e in self.cc_graph.edges:
                    v = myModel.getVarByName("gamma_" + str(e[0]) + "_" + str(e[1]) + "^" + str(t))
                    newDict[e] = v.x
                returnedDict[t] = newDict
            return returnedDict

        def compute_flow_through_nodes():
            flow_through_nodes = dict()
            for n in self.extendedGraph.nodes:
                if n != (-1, -1):
                    sum_of_inflows = 0
                    for pred in self.extendedGraph.predecessors(n):
                        #v = myModel.getVarByName("gamma_" + str(pred) + "_" + str(n) + "^" + str(self.timeSteps))
                        sum_of_inflows = sum_of_inflows + flows[(pred, n), self.timeSteps].x
                    flow_through_nodes[n] = sum_of_inflows / self.cc_area[n]
            return flow_through_nodes

        def compute_handlungsbedarf():
            #damage_class
            handlungsbedarf = dict()
            for b in self.all_buildings:
                schadensklasse = self.all_buildings[b]["schadensklasse"]
                gefahrenklasse = 1
                for k in range(0, 5):
                    if danger_class[k, b, self.timeSteps].x == 1:
                        gefahrenklasse = k
                if gefahrenklasse == 0:
                    handlungsbedarf[b] = 0
                else:
                    summe_gefahrenklasse_schadensklasse = schadensklasse + gefahrenklasse
                    if summe_gefahrenklasse_schadensklasse <= 2:
                        handlungsbedarf[b] = 1
                    elif summe_gefahrenklasse_schadensklasse <= 4:
                        handlungsbedarf[b] = 2
                    elif summe_gefahrenklasse_schadensklasse <= 5:
                        handlungsbedarf[b] = 3
                    else:
                        handlungsbedarf[b] = 4
            return handlungsbedarf

        totalArea = getTotalArea()
        myModel = gurobi.Model("myModel")
        myModel.modelSense = gurobi.GRB.MINIMIZE
        flows = {}
        excess = {}
        waterHeight = {}
        waterAmount = {}
        activeArc = {}
        fullArc = {}
        deactivateArc = {}
        floodedNodes = {}
        decisionAuffangbecken = {}
        decisionLeitgraben = {}
        height_difference_through_auffangbecken = {}
        height_difference_through_leitgraben = {}
        geodesicHeightAsVariable = {}
        binaryHelpForFlowDistribution = {}
        originalDirection = {}
        binaryHelpForOriginal1AndFull1 = {}
        binaryHelpForOriginal1AndFull0 = {}
        binaryHelpForOriginal0AndFull1 = {}
        binaryHelpForOriginal0AndFull0 = {}
        max_water_level = {}
        danger_class = {}
        kataster_allowed = {}
        activeNodes = {}
        flooded = {}
        solutionWaterHeight = {}
        removableEdges = []
        vertiefung = {}
        maximum_geodesic_height_on_node = {}
        minimum_geodesic_height_on_node = {}

        declareVariables()
        addConstraints()
        handOverStartSolution()
        if self.initialSolution is not None:
            pass
            #addInitialSolutionConstraints()

        # myModel.setParam("Presolve", 2) #set presolve to aggressive
        myModel.setParam("Cuts", 3) #This is what gurobi proposes to do
        myModel.setParam("BranchDir", -1)
        myModel.setParam("Heuristics", 0.001)
        myModel.setParam("MIPFocus", 1)
        if "mipgap" in self.optimization_parameters and self.optimization_parameters["mipgap"] is not None:
            myModel.setParam("MIPGap", self.optimization_parameters["mipgap"]/100)
        else:
            myModel.setParam("MIPGap", 0.05)
        if "timeout" in self.optimization_parameters and self.optimization_parameters["timeout"] is not None:
            myModel.setParam("TimeLimit", self.optimization_parameters["timeout"] * 60)
        # myModel.tune()

        myModel.optimize()

        debug = False

        if gurobi.GRB.OPTIMAL != 2 or debug:
            myModel.computeIIS()
            myModel.write(filename="myModel.ilp")

        putFloodedIntoDictionary()
        putActiveIntoDictionary()
        auffangbeckenSolution = putAuffangbeckenIntoDictionary()
        leitgraeben_solution = putLeitgrabenIntoDictionary()
        putWaterHeightIntoDictionary()
        solutionFullArcs = putFullArcIntoDictionary()
        waterHeightGreaterZero = getNodesWithWaterHeightGreaterZero()
        flow_through_nodes = compute_flow_through_nodes()
        handlungsbedarf = compute_handlungsbedarf()
        myModel.write(filename="myModel.lp")

        printSolution = False
        if printSolution:
            print(flooded)
            print(activeNodes)

            for v in myModel.getVars():
                print('%s %g' % (v.varName, v.x))
        print("reached end of optimizer")
        return waterHeightGreaterZero, activeNodes, solutionWaterHeight, auffangbeckenSolution, leitgraeben_solution, flow_through_nodes, handlungsbedarf

    def backwards_transformation_to_original_graph(self):
        #self.flooded, self.activeNodes, self.waterHeight, self.auffangbecken_solution, self.leitgraeben_solution, self.flow_through_nodes, self.handlungsbedarf
        for t in self.flooded:
            for n in self.originalGraph:
                if n not in self.flooded[t]:
                    self.flooded[t][n] = self.flooded[t][self.mapping_representator_per_node[n]]

        for t in self.activeNodes:
            for n in self.originalGraph:
                if n not in self.activeNodes[t]:
                    self.activeNodes[t][n] = self.activeNodes[t][self.mapping_representator_per_node[n]]

        for t in self.waterHeight:
            for n in self.originalGraph:
                if n not in self.waterHeight[t]:
                    self.waterHeight[t][n] = self.waterHeight[t][self.mapping_representator_per_node[n]]

        for n in self.originalGraph:
            if n not in self.flow_through_nodes and n != (-1, -1):
                self.flow_through_nodes[n] = self.flow_through_nodes[self.mapping_representator_per_node[n]] * self.area[n] / self.cc_area[self.mapping_representator_per_node[n]]


    def handOverFloodedNodesToDatabase(self):
        return self.flooded

    def handOverWaterHeightToDatabase(self):
        return self.waterHeight

    def handOverAuffangbeckenHeightToDatabase(self):
        return self.auffangbecken_solution

    def handOverLeitgraebenHeightToDatabase(self):
        return self.leitgraeben_solution

    def handOverHandlungsbedarfToDatabase(self):
        return self.handlungsbedarf