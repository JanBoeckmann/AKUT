import networkx as nx
import numpy as np
import matplotlib as plt
from akut.ipEquilibriumWaterLevels import *
from akut.linearEquationSolverForFlows import *

'''
    Input:  region:         as usual String containing region (see database tables) 
            nodesPosition:  dictionary with ids as keys and tuple of position as value
            nodesRelevant:  dictionary with ids as keys and relevantForGraph as value (0,1)
            geodesicHeight: dictionary with ids as keys and geodesic height as value
'''

class instanceGraph:
    def __init__(self,region, nodesPosition, nodesRelevant, geodesigHeight, massnahmenOnNode, gridSize, allAuffangbecken, allLeitgraeben, all_buildings, rain, timeSteps, which_DGM_from):
        self.region = region
        self.nodesPosition = nodesPosition
        self.position_to_id = self.compute_position_to_id()
        self.nodesRelevant = nodesRelevant
        geodesigHeight.update((x, y/1000) for x, y in geodesigHeight.items())
        self.geodesicHeight = geodesigHeight
        self.massnahmenOnNode = massnahmenOnNode
        self.gridSize = gridSize
        self.allAuffangbecken = allAuffangbecken
        self.allLeitgraeben = allLeitgraeben
        self.all_buildings = all_buildings
        timeSteps = timeSteps / 60
        rain = rain / 1000 / 10000 * 3600
        self.rain = rain * timeSteps
        self.timeSteps = 1
        self.which_DGM_from = which_DGM_from
        self.fullGraph = self.computeFullGraph()
        #self.draw_graph()

    def compute_position_to_id(self):
        position_to_id = dict()
        for key, val in self.nodesPosition.items():
            position_to_id[val] = key
        return position_to_id

    def computeFullGraph(self):
        def addSingleEdgeForNodePair(firstNode, secondNode):
            if G.has_node(secondNode) and not (G.has_edge(firstNode, secondNode) or G.has_edge(secondNode, secondNode)):
                if self.geodesicHeight[allNodeIds[firstNode]] > self.geodesicHeight[allNodeIds[secondNode]]:
                    G.add_edge(firstNode, secondNode)
                else:
                    G.add_edge(secondNode, firstNode)

        def addEdgesForNode(node):
            addSingleEdgeForNodePair(node, (node[0] + 1, node[1]))
            addSingleEdgeForNodePair(node, (node[0] - 1, node[1]))
            addSingleEdgeForNodePair(node, (node[0], node[1] + 1))
            addSingleEdgeForNodePair(node, (node[0], node[1] - 1))

        def check_if_node_exists_and_if_it_is_in_correct_resolution(node_to_check, resolution_to_check):
            ret_bool = False
            if G.has_node(node_to_check):
                if self.which_DGM_from[self.position_to_id[node_to_check]] == resolution_to_check:
                    ret_bool = True
            return ret_bool

        def add_edges_for_25(node, resolution):
            if resolution == 25:
                nodes_to_check = [(node[0] + 25, node[1], "E", 25),
                                  (node[0] - 25, node[1], "W", 25),
                                  (node[0], node[1] + 25, "N", 25),
                                  (node[0], node[1] - 25, "S", 25)]
            elif resolution == 5:
                nodes_to_check = [(node[0] + 5, node[1], "E", 5),
                                  (node[0] - 5, node[1], "W", 5),
                                  (node[0], node[1] + 5, "N", 5),
                                  (node[0], node[1] - 5, "S", 5)]
            elif resolution == 1:
                nodes_to_check = [(node[0] + 1, node[1], "E", 1),
                                  (node[0] - 1, node[1], "W", 1),
                                  (node[0], node[1] + 1, "N", 1),
                                  (node[0], node[1] - 1, "S", 1)]
            while nodes_to_check:
                currently_checked_node = nodes_to_check.pop()
                current_node_coordinates = (currently_checked_node[0], currently_checked_node[1])
                if check_if_node_exists_and_if_it_is_in_correct_resolution(current_node_coordinates, currently_checked_node[3]):
                    addSingleEdgeForNodePair(node, current_node_coordinates)
                else:
                    if currently_checked_node[2] == "E" and currently_checked_node[3] == 25:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] - 10, currently_checked_node[1] + 10 - 5 * i, "E", 5))
                    elif currently_checked_node[2] == "E" and currently_checked_node[3] == 5:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] - 2, currently_checked_node[1] + 2 - 1 * i, "E", 1))
                    elif currently_checked_node[2] == "W" and currently_checked_node[3] == 25:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 10, currently_checked_node[1] + 10 - 5 * i, "W", 5))
                    elif currently_checked_node[2] == "W" and currently_checked_node[3] == 5:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 2, currently_checked_node[1] + 2 - 1 * i, "W", 1))
                    elif currently_checked_node[2] == "N" and currently_checked_node[3] == 25:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 10 - 5 * i, currently_checked_node[1] - 10, "N", 5))
                    elif currently_checked_node[2] == "N" and currently_checked_node[3] == 5:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 2 - 1 * i, currently_checked_node[1] - 2, "N", 1))
                    elif currently_checked_node[2] == "S" and currently_checked_node[3] == 25:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 10 - 5 * i, currently_checked_node[1] + 10, "S", 5))
                    elif currently_checked_node[2] == "S" and currently_checked_node[3] == 5:
                        for i in range(5):
                            nodes_to_check.append((currently_checked_node[0] + 2 - 1 * i, currently_checked_node[1] + 2, "S", 1))

        G = nx.DiGraph()
        for indexId in self.nodesPosition:
            G.add_node((self.nodesPosition[indexId][0], self.nodesPosition[indexId][1]), utm=(self.nodesPosition[indexId][0], self.nodesPosition[indexId][1]), relevant=self.nodesRelevant[indexId], nodeId=indexId, connectedToRelevantNodes=0, geodesicHeight=self.geodesicHeight[indexId], massnahmenOnNode=self.massnahmenOnNode[indexId])

        allNodeIds = nx.get_node_attributes(G, "nodeId")

        for node in G.nodes:
            add_edges_for_25(node, self.which_DGM_from[self.position_to_id[node]])

        return G

    def draw_graph(self):
        test_graph = self.fullGraph.copy()
        nodes_to_iterate_over = self.fullGraph.nodes()
        for node in nodes_to_iterate_over:
            if self.which_DGM_from[self.position_to_id[node]] == 25 or self.which_DGM_from[self.position_to_id[node]] == 5:
                test_graph.remove_node(node)

        position = {}

        for node in self.fullGraph:
            position[node] = node
        nx.draw(test_graph, pos=position)
        plt.pyplot.show()

    def computeRelevantGraph(self):
        nodesQueue = [x for x,y in self.fullGraph.nodes(data=True) if y["relevant"] == 1]
        relevantGraph = self.fullGraph.copy()
        nodeAttributes = nx.get_node_attributes(self.fullGraph, "relevant")
        nodeConnected = nx.get_node_attributes(self.fullGraph, "connectedToRelevantNodes")
        #Fill node Attributes (relevant)
        while len(nodesQueue) > 0:
            actualNode = nodesQueue.pop()
            for child in self.fullGraph.successors(actualNode):
                if nodeAttributes[child] == 0:
                    nodesQueue.append(child)
                    nodeAttributes[child] = 1
        nx.set_node_attributes(relevantGraph, nodeAttributes, "relevant")

        #fill Connected
        reversedGraph = self.fullGraph.reverse(copy=True)
        nodesRelevantQueue = [x for x,y in relevantGraph.nodes(data=True) if y["relevant"] == 1]
        for relevantNode in nodesRelevantQueue:
            nodeConnected[relevantNode] = 1
        while len(nodesRelevantQueue) > 0:
            actualNode = nodesRelevantQueue.pop()
            for child in reversedGraph.successors(actualNode):
                if nodeConnected[child] == 0:
                    nodesRelevantQueue.append(child)
                    nodeConnected[child] = 1

        nx.set_node_attributes(relevantGraph, nodeConnected, "connectedToRelevantNodes")
        return relevantGraph

    def computeListOfRelevantAndConnectedNodes(self):
        relevantGraph = self.computeRelevantGraph()
        relevantNodes = [x for x,y in relevantGraph.nodes(data=True) if y["relevant"] == 1]
        connectedNodes = [x for x,y in relevantGraph.nodes(data=True) if y["connectedToRelevantNodes"] == 1]
        return relevantNodes, connectedNodes

    def computeInstanceGraph(self):
        def compute_area():
            area_computed = dict()
            for node in graphForIP:
                if node == (-1, -1):
                    area_computed[node] = numberOfConcatenatedNodes[node] * 625
                else:
                    area_computed[node] = pow(self.which_DGM_from[self.position_to_id[node]], 2)
            return area_computed

        relevantGraph = self.computeRelevantGraph()
        listOfRelevantNodes, listOfConnectedNodes = self.computeListOfRelevantAndConnectedNodes()
        auxiliaryGraph = relevantGraph.subgraph(listOfConnectedNodes).reverse(copy=True)
        boundaryNodes = []
        for node in listOfRelevantNodes:
            boundaryBool = 1
            for child in auxiliaryGraph.successors(node):
                if not child in listOfRelevantNodes:
                    boundaryBool = 0
            for parent in auxiliaryGraph.predecessors(node):
                if not parent in listOfRelevantNodes:
                    boundaryBool = 0
            if boundaryBool == 0:
                boundaryNodes.append(node)

        boundaryNumberOfInflowNodes = dict()
        totalNumberOfInflowIntoBoundary = 0
        nodesToRemoveForAuxiliaryGraph = [x for x in listOfRelevantNodes if x not in boundaryNodes]
        auxiliaryGraph.remove_nodes_from(nodesToRemoveForAuxiliaryGraph)
        for node in boundaryNodes:
            numberOfInflowNodes = len(list(nx.dfs_preorder_nodes(auxiliaryGraph, node)))
            boundaryNumberOfInflowNodes[node] = numberOfInflowNodes
            totalNumberOfInflowIntoBoundary = totalNumberOfInflowIntoBoundary + numberOfInflowNodes

        connectedGraph = relevantGraph.subgraph(listOfConnectedNodes)
        graphForIP = connectedGraph.subgraph(listOfRelevantNodes).copy()
        edgeProportion = dict()
        numberOfConcatenatedNodes = dict()
        for actualNode in graphForIP.nodes():
            numberOfOutEdges = len(graphForIP.out_edges(actualNode))
            total_geodesic_height_difference = 0
            total_proportion = 0
            for successor in graphForIP.successors(actualNode):
                total_geodesic_height_difference = total_geodesic_height_difference + self.geodesicHeight[self.position_to_id[actualNode]] - self.geodesicHeight[self.position_to_id[successor]]
            for successor in graphForIP.successors(actualNode):
                if total_geodesic_height_difference > 0:
                    edgeProportion[(actualNode, successor)] = (self.geodesicHeight[self.position_to_id[actualNode]] - self.geodesicHeight[self.position_to_id[successor]]) / total_geodesic_height_difference
                    if self.geodesicHeight[self.position_to_id[actualNode]] == self.geodesicHeight[self.position_to_id[successor]]:
                        edgeProportion[(actualNode, successor)] = 0.01 #if heights are exactly the same, we allow for a very small flow such that we won't divide by 0 in the IP
                else:
                    edgeProportion[(actualNode, successor)] = 1 / numberOfOutEdges
                if self.which_DGM_from[self.position_to_id[actualNode]] > self.which_DGM_from[self.position_to_id[successor]]:
                    edgeProportion[(actualNode, successor)] = edgeProportion[(actualNode, successor)] * self.which_DGM_from[self.position_to_id[successor]] / self.which_DGM_from[self.position_to_id[actualNode]]
                total_proportion = total_proportion + edgeProportion[(actualNode, successor)]
            for successor in graphForIP.successors(actualNode):
                edgeProportion[(actualNode, successor)] = edgeProportion[(actualNode, successor)] / total_proportion
            numberOfConcatenatedNodes[actualNode] = 1


        graphForIP.add_node((-1, -1)) #supernode
        for boundaryNode in boundaryNodes:
            graphForIP.add_edge((-1, -1), boundaryNode)
            edgeProportion[((-1, -1), boundaryNode)] = boundaryNumberOfInflowNodes[boundaryNode] / totalNumberOfInflowIntoBoundary * self.which_DGM_from[self.position_to_id[boundaryNode]] / 25

        nx.set_edge_attributes(graphForIP, edgeProportion, 'edgeProportion')
        geodesicHeight = nx.get_node_attributes(graphForIP, 'geodesicHeight')
        maxGeodesicHeight = 0
        for key, value in geodesicHeight.items():
            if value > maxGeodesicHeight:
                maxGeodesicHeight = value
        geodesicHeight[(-1, -1)] = maxGeodesicHeight + 9999
        numberOfConcatenatedNodes[(-1, -1)] = len(listOfConnectedNodes) - len(listOfRelevantNodes)
        nx.set_node_attributes(graphForIP, geodesicHeight, "geodesicHeight")
        nx.set_node_attributes(graphForIP, numberOfConcatenatedNodes, "concatenatedNodes")

        area = compute_area()
        nx.set_node_attributes(graphForIP, area, "area")

        return graphForIP

    def callIPWithEquilibriumWaterLevels(self, graphForIP, initialSolution, optimization_parameters, threshold_for_gefahrenklasse, massnahmen_kataster, all_kataster):
        ratios = nx.get_edge_attributes(graphForIP, "edgeProportion")
        geodesicHeight = nx.get_node_attributes(graphForIP, "geodesicHeight")
        area = nx.get_node_attributes(graphForIP, "area")
        massnahmenOnNode = nx.get_node_attributes(graphForIP, "massnahmenOnNode")
        myIP = ipEquilibriumWaterLevels(ratios, geodesicHeight, area, self.timeSteps, self.rain, massnahmenOnNode, self.allAuffangbecken, self.allLeitgraeben, self.all_buildings, optimization_parameters, initialSolution, threshold_for_gefahrenklasse, massnahmen_kataster, all_kataster)
        flooded = myIP.handOverFloodedNodesToDatabase()
        waterHeight = myIP.handOverWaterHeightToDatabase()
        auffangbecken_solution = myIP.handOverAuffangbeckenHeightToDatabase()
        leitgraeben_solution = myIP.handOverLeitgraebenHeightToDatabase()
        handlungsbedarf = myIP.handOverHandlungsbedarfToDatabase()
        flow_through_nodes = myIP.flow_through_nodes
        flow_through_nodes_for_db = dict()
        dictionaryForDatabase = {}
        dict_water_height = dict()
        for timeStep in flooded:
            dictionaryForDatabase[timeStep] = {}
            dict_water_height[timeStep] = {}
            for id, position in self.nodesPosition.items():
                if position in flooded[timeStep]:
                    dictionaryForDatabase[timeStep][id] = flooded[timeStep][position]
                    dict_water_height[timeStep][id] = waterHeight[timeStep][position]
                if position in flow_through_nodes:
                    flow_through_nodes_for_db[id] = flow_through_nodes[position]
        return dictionaryForDatabase, dict_water_height, auffangbecken_solution, leitgraeben_solution, flow_through_nodes_for_db, handlungsbedarf

    def computeInitialSolution(self, buildAuffangbecken):
        def recomputeGeodesicHeight():
            for n in graphWithGeodesicHeightAfterAuffangbeckenBuilt.nodes:
                if n != (-1, -1):
                    for massnahme in massnahmenOnNode[n]:
                        if massnahmenOnNode[n][massnahme]["type"] == "auffangbecken" and buildAuffangbecken[massnahmenOnNode[n][massnahme]["id"]] == 1:
                            geodesicHeight[n] = geodesicHeight[n] - self.allAuffangbecken[massnahmenOnNode[n][massnahme]["id"]]["depth"]
            nx.set_node_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, geodesicHeight, "geodesicHeight")

        def recomputeEdgeDirection():
            edgesToReverse = []
            for e in graphWithGeodesicHeightAfterAuffangbeckenBuilt.edges:
                if geodesicHeight[e[0]] < geodesicHeight[e[1]]:
                    edgesToReverse.append(e)
            for e in edgesToReverse:
                myratios[(e[1], e[0])] = myratios[e]
                del myratios[e]
                graphWithGeodesicHeightAfterAuffangbeckenBuilt.add_edge(e[1], e[0])
                graphWithGeodesicHeightAfterAuffangbeckenBuilt.remove_edge(e[0], e[1])
            nx.set_edge_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, myratios, "edgeProportion")

        def initialiseGraph():
            return graphWithGeodesicHeightAfterAuffangbeckenBuilt.copy(), myarea.copy(), myratios.copy()

        def getRootNode(G):
            indegreeZero = [n for n, d in G.in_degree() if d == 0]
            return indegreeZero

        def getleaves(graph):
            outdegreeZero = [n for n, d in graph.out_degree() if d == 0]
            return outdegreeZero

        def initialiseFlows(G):
            H = G.copy()
            initialFlows = {}
            while len(H.nodes) > 0:
                listOfNodes = getRootNode(H)
                while len(listOfNodes) > 0:
                    actualNode = listOfNodes.pop()
                    parents = G.predecessors(actualNode)
                    flowValue = self.rain * modArea[actualNode]
                    for p in parents:
                        flowValue = flowValue + initialFlows[p] * modRatios[(p, actualNode)]
                    initialFlows[actualNode] = flowValue
                    H.remove_node(actualNode)
            return initialFlows

        def inititialiseWaterAmounts(G):
            initialWaterAmounts = {}
            for n in G.nodes:
                initialWaterAmounts[n] = 0
            return initialWaterAmounts

        def getLowestParent(G, node):
            parents = G.predecessors(node)
            myParent = None
            for p in parents:
                if myParent is None:
                    myParent = p
                elif geodesicHeight[myParent] > geodesicHeight[p]:
                    myParent = p
            return myParent

        def calculateLeavesFloodingTimes(G):
            actualLeaves = getleaves(G)
            leavesFloodingTimes = {}
            for l in actualLeaves:
                floodingTime = (geodesicHeight[getLowestParent(G, l)] - geodesicHeight[l] - waterAmounts[i - 1][l] / modArea[l]) * modArea[l] / flows[i][l]
                leavesFloodingTimes[l] = floodingTime
            firstFloodedLeave = min(leavesFloodingTimes, key=leavesFloodingTimes.get)
            return leavesFloodingTimes, firstFloodedLeave

        def setWaterLevels():
            newWaterAmounts = {}
            for n in modGraph.nodes:
                newWaterAmounts[n] = 0
            for l in getleaves(modGraph):
                newWaterAmounts[l] = waterAmounts[i - 1][l] + minimumFloodTime * flows[i][l]
            waterAmounts[i] = newWaterAmounts

        def updateGraph(lastStep):
            actualParent = getLowestParent(modGraph, firstFloodedLeave)
            ratiosSum = 0
            for c in modGraph.successors(actualParent):
                if c != firstFloodedLeave:
                    ratiosSum = ratiosSum + modRatios[(actualParent, c)]

            if ratiosSum != 0:
                for c in modGraph.successors(actualParent):
                    if c != firstFloodedLeave:
                        modRatios[(actualParent, c)] = modRatios[(actualParent, c)] / ratiosSum
                    else:
                        del modRatios[(actualParent, c)]
            if not lastStep:
                modArea[actualParent] = modArea[actualParent] + modArea[firstFloodedLeave]
                del modArea[firstFloodedLeave]
            else:
                print("Last Flooded Leave " + str(firstFloodedLeave))
            for p in modGraph.predecessors(firstFloodedLeave):
                if p != actualParent:
                    modGraph.add_edge(p, actualParent)
                    modRatios[(p, actualParent)] = modRatios[(p, firstFloodedLeave)]
                    del modRatios[(p, firstFloodedLeave)]
            modGraph.remove_node(firstFloodedLeave)
            updateFlows(actualParent)

        def updateFlows(parentNode):
            newFlows = flows[i].copy()
            del newFlows[firstFloodedLeave]

            listOfNodes = [parentNode]
            remember_recomputed_nodes = set()
            while len(listOfNodes) > 0:
                actualNode = listOfNodes.pop()
                if actualNode not in remember_recomputed_nodes:
                    parents = modGraph.predecessors(actualNode)
                    flowValue = self.rain * modArea[actualNode]
                    for p in parents:
                        flowValue = flowValue + newFlows[p] * modRatios[(p, actualNode)]
                    newFlows[actualNode] = flowValue
                    children = modGraph.successors(actualNode)
                    for c in children:
                        listOfNodes.append(c)
                    remember_recomputed_nodes.add(actualNode)
            flows[i + 1] = newFlows

        def waterAmountsLastEntryCorrection():
            numberOfFloodedNodes = len(waterAmounts) - 2
            if (sumOfFloodingTimes > self.timeSteps):
                summedFloodingTimes = np.cumsum(floodingTimes)
                timeLeftInLastStep = self.timeSteps - summedFloodingTimes[-2]
                fractionOfLastStep = timeLeftInLastStep / floodingTimes[-1]
                lastEntry = waterAmounts[numberOfFloodedNodes + 1]
                for key in lastEntry:
                    waterAmounts[numberOfFloodedNodes + 1][key] = waterAmounts[numberOfFloodedNodes][key] + (waterAmounts[numberOfFloodedNodes + 1][key] - waterAmounts[numberOfFloodedNodes][key]) * fractionOfLastStep

        def computeWaterHeightInOriginalGraph():
            lastWaterAmounts = waterAmounts[len(waterAmounts) - 1]
            waterHeight = {}
            graphOfFloodedNodes = graphWithGeodesicHeightAfterAuffangbeckenBuilt.copy()
            listOfNonFloodedNodesWithWaterLevelsGreaterZero = []
            floodedNodesCopy = floodedNodes.copy()
            for n in lastWaterAmounts:
                waterHeight[n] = lastWaterAmounts[n] / modArea[n]
                graphOfFloodedNodes.remove_node(n)
                if waterHeight[n] > 0:
                    listOfNonFloodedNodesWithWaterLevelsGreaterZero.append(n)

            for n in listOfNonFloodedNodesWithWaterLevelsGreaterZero:
                undirectedInducedGraph = graphWithGeodesicHeightAfterAuffangbeckenBuilt.copy()
                undirectedInducedGraph = undirectedInducedGraph.to_undirected()
                nodesToRemove = []
                for v in undirectedInducedGraph.nodes():
                    if geodesicHeight[n] < geodesicHeight[v]:
                        nodesToRemove.append(v)
                undirectedInducedGraph.remove_nodes_from(nodesToRemove)
                setOfNodesInComponent = nx.node_connected_component(undirectedInducedGraph, n)
                for v in setOfNodesInComponent:
                    if v != n:
                        waterHeight[v] = waterHeight[n] + (geodesicHeight[n] - geodesicHeight[v])
                        if v in floodedNodesCopy:
                            floodedNodesCopy.remove(v)
            floodedNodesCopy.remove(lastFloodedLeave)
            already_added_nodes = set()
            while len(floodedNodesCopy) > 0:
                newFloodedNodesCopy = []
                for v in floodedNodesCopy:
                    lowestParent = getLowestParent(graphWithGeodesicHeightAfterAuffangbeckenBuilt, v)
                    if lowestParent in waterHeight:
                        waterHeight[v] = waterHeight[lowestParent] + (geodesicHeight[lowestParent] - geodesicHeight[v])
                        # already_added_nodes.add(v)
                    else:
                        if v not in already_added_nodes:
                            newFloodedNodesCopy.append(v)
                            already_added_nodes.add(v)
                floodedNodesCopy = newFloodedNodesCopy
            return waterHeight

        def computeFloodedInOriginalGraph():
            floodedInOriginalGraph = {}
            for key, val in waterHeight.items():
                if val > 0:
                    floodedInOriginalGraph[key] = 1
                else:
                    floodedInOriginalGraph[key] = 0
            return floodedInOriginalGraph

        graphWithGeodesicHeightAfterAuffangbeckenBuilt = self.computeInstanceGraph()
        geodesicHeight = nx.get_node_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, "geodesicHeight")
        massnahmenOnNode = nx.get_node_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, "massnahmenOnNode")
        myarea = nx.get_node_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, "concatenatedNodes")
        myratios = nx.get_edge_attributes(graphWithGeodesicHeightAfterAuffangbeckenBuilt, "edgeProportion")
        if buildAuffangbecken is not None:
            recomputeGeodesicHeight()
        recomputeEdgeDirection()
        myarea.update((x, y * pow(self.gridSize, 2)) for x, y in myarea.items())
        modGraph, modArea, modRatios = initialiseGraph()
        flows = {}
        flows[1] = initialiseFlows(modGraph)
        waterAmounts = {}
        waterAmounts[0] = inititialiseWaterAmounts(modGraph)
        floodingTimes = []
        sumOfFloodingTimes = 0
        floodedNodes = []
        lastFloodedLeave = (1, 1)

        i = 1
        while len(modGraph.nodes) > 2 and sumOfFloodingTimes < self.timeSteps:
            leavesFloodingTimes, firstFloodedLeave = calculateLeavesFloodingTimes(modGraph)
            minimumFloodTime = leavesFloodingTimes[firstFloodedLeave]
            setWaterLevels()
            floodedNodes.append(firstFloodedLeave)
            floodingTimes.append(minimumFloodTime)
            sumOfFloodingTimes = sumOfFloodingTimes + minimumFloodTime
            print(sumOfFloodingTimes)
            if sumOfFloodingTimes > self.timeSteps:
                updateGraph(True)
                lastFloodedLeave = firstFloodedLeave
            else:
                updateGraph(False)
            i = i + 1
        print("end while")
        waterAmountsLastEntryCorrection()
        waterHeight = computeWaterHeightInOriginalGraph()
        # floodedInOriginalGraph = computeFloodedInOriginalGraph()

        #now recalculate flows from scratch with information about flooded nodes
        floodedNodes.remove(lastFloodedLeave)
        #equationSolver = linearEquationSolverForFlows(graphWithGeodesicHeightAfterAuffangbeckenBuilt, waterHeight, self.rain, self.timeSteps, self.gridSize)
        #waterHeight = equationSolver.solveLinearEquationSystem()
        return floodingTimes, waterAmounts, modGraph, modArea, floodedNodes, waterHeight