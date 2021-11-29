import networkx as nx
import numpy as np
from akut.ipEquilibriumWaterLevels import *
from akut.linearEquationSolverForFlows import *

'''
    Input:  region:         as usual String containing region (see database tables) 
            nodesPosition:  dictionary with ids as keys and tuple of position as value
            nodesRelevant:  dictionary with ids as keys and relevantForGraph as value (0,1)
            geodesicHeight: dictionary with ids as keys and geodesic height as value
'''

class instanceGraphForDGM25:
    def __init__(self,region, nodesPosition, nodesRelevant, geodesigHeight, massnahmenOnNode, gridSize, allAuffangbecken, rain, timeSteps):
        self.region = region
        self.nodesPosition = nodesPosition
        self.nodesRelevant = nodesRelevant
        geodesigHeight.update((x, y/1000) for x, y in geodesigHeight.items())
        self.geodesicHeight = geodesigHeight
        self.massnahmenOnNode = massnahmenOnNode
        self.gridSize = gridSize
        self.allAuffangbecken = allAuffangbecken
        timeSteps = timeSteps / 60
        rain = rain / 1000 / 10000 * 3600
        self.rain = rain * timeSteps
        print(self.rain)
        self.timeSteps = 1
        self.fullGraph = self.computeFullGraph()

    def computeFullGraph(self):
        def addSingleEdgeForNodePair(firstNode, secondNode):
            if G.has_node(secondNode) and not (G.has_edge(firstNode, secondNode) or G.has_edge(secondNode, secondNode)):
                if self.geodesicHeight[allNodeIds[firstNode]] > self.geodesicHeight[allNodeIds[secondNode]]:
                    G.add_edge(firstNode, secondNode)
                else:
                    G.add_edge(secondNode, firstNode)

        def addEdgesForNode(node):
            addSingleEdgeForNodePair(node, (node[0] + 25, node[1]))
            addSingleEdgeForNodePair(node, (node[0] - 25, node[1]))
            addSingleEdgeForNodePair(node, (node[0], node[1] + 25))
            addSingleEdgeForNodePair(node, (node[0], node[1] - 25))

        G = nx.DiGraph()

        for indexId in self.nodesPosition:
            G.add_node((self.nodesPosition[indexId][0], self.nodesPosition[indexId][1]), utm=(self.nodesPosition[indexId][0], self.nodesPosition[indexId][1]), relevant=self.nodesRelevant[indexId], nodeId=indexId, connectedToRelevantNodes=self.nodesRelevant[indexId], geodesicHeight=self.geodesicHeight[indexId], massnahmenOnNode=self.massnahmenOnNode[indexId])

        allNodeIds = nx.get_node_attributes(G, "nodeId")

        for node in G.nodes:
            addEdgesForNode(node)

        return G

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
            for successor in graphForIP.successors(actualNode):
                edgeProportion[(actualNode, successor)] = 1 / numberOfOutEdges
            numberOfConcatenatedNodes[actualNode] = 1

        graphForIP.add_node((-1, -1)) #supernode
        for boundaryNode in boundaryNodes:
            graphForIP.add_edge((-1, -1), boundaryNode)
            edgeProportion[((-1, -1), boundaryNode)] = boundaryNumberOfInflowNodes[boundaryNode] / totalNumberOfInflowIntoBoundary

        nx.set_edge_attributes(graphForIP, edgeProportion, 'edgeProportion')
        geodesicHeight = nx.get_node_attributes(graphForIP, 'geodesicHeight')
        maxGeodesicHeight = 0
        for key, value in geodesicHeight.items():
            if value > maxGeodesicHeight:
                maxGeodesicHeight = value
        geodesicHeight[(-1, -1)] = maxGeodesicHeight + 1
        numberOfConcatenatedNodes[(-1, -1)] = len(listOfConnectedNodes) - len(listOfRelevantNodes)
        nx.set_node_attributes(graphForIP, geodesicHeight, "geodesicHeight")
        nx.set_node_attributes(graphForIP, numberOfConcatenatedNodes, "concatenatedNodes")

        return graphForIP

    def computeInitialSolution(self, buildAuffangbecken):
        def recomputeGeodesicHeight():
            if buildAuffangbecken is not None:
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
            remember_nodes = set()
            listOfNodes = [parentNode]
            while len(listOfNodes) > 0:
                actualNode = listOfNodes.pop()
                remember_nodes.add(actualNode)
                parents = modGraph.predecessors(actualNode)
                flowValue = self.rain * modArea[actualNode]
                for p in parents:
                    flowValue = flowValue + newFlows[p] * modRatios[(p, actualNode)]
                newFlows[actualNode] = flowValue
                children = modGraph.successors(actualNode)
                for c in children:
                    if c not in remember_nodes:
                        listOfNodes.append(c)
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
                for v in nodesToRemove:
                    undirectedInducedGraph.remove_node(v)
                setOfNodesInComponent = nx.node_connected_component(undirectedInducedGraph, n)
                for v in setOfNodesInComponent:
                    if v != n:
                        waterHeight[v] = waterHeight[n] + (geodesicHeight[n] - geodesicHeight[v])
                        if v in floodedNodesCopy:
                            floodedNodesCopy.remove(v)
            if lastFloodedLeave in floodedNodesCopy:
                floodedNodesCopy.remove(lastFloodedLeave)
            print(floodedNodesCopy)
            remember_flooded_nodes = []
            while len(floodedNodesCopy) > 0 and remember_flooded_nodes != floodedNodesCopy:
                print(floodedNodesCopy)
                newFloodedNodesCopy = []
                for v in floodedNodesCopy:
                    lowestParent = getLowestParent(graphWithGeodesicHeightAfterAuffangbeckenBuilt, v)
                    if lowestParent in waterHeight:
                        waterHeight[v] = waterHeight[lowestParent] + (geodesicHeight[lowestParent] - geodesicHeight[v])
                    else:
                        newFloodedNodesCopy.append(v)
                remember_flooded_nodes = floodedNodesCopy
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
        recomputeGeodesicHeight()
        recomputeEdgeDirection()
        myarea.update((x, y * pow(self.gridSize, 2)) for x, y in myarea.items())

        print("initialize graph")
        modGraph, modArea, modRatios = initialiseGraph()
        flows = {}
        flows[1] = initialiseFlows(modGraph)
        waterAmounts = {}
        waterAmounts[0] = inititialiseWaterAmounts(modGraph)
        floodingTimes = []
        sumOfFloodingTimes = 0
        floodedNodes = []
        lastFloodedLeave = (1, 1)

        print("enter while loop for computing next flooded leave")
        i = 1
        while len(modGraph.nodes) > 2 and sumOfFloodingTimes < self.timeSteps:
            leavesFloodingTimes, firstFloodedLeave = calculateLeavesFloodingTimes(modGraph)
            minimumFloodTime = leavesFloodingTimes[firstFloodedLeave]
            setWaterLevels()
            floodedNodes.append(firstFloodedLeave)
            floodingTimes.append(minimumFloodTime)
            sumOfFloodingTimes = sumOfFloodingTimes + minimumFloodTime
            if sumOfFloodingTimes > self.timeSteps:
                updateGraph(True)
                lastFloodedLeave = firstFloodedLeave
            else:
                updateGraph(False)
            i = i + 1
        print("end while")
        print("correct last entry")
        waterAmountsLastEntryCorrection()
        print("compute water height in original graph")
        waterHeight = computeWaterHeightInOriginalGraph()
        print(" finished computing water height in original graph")
        floodedInOriginalGraph = computeFloodedInOriginalGraph()

        #now recalculate flows from scratch with information about flooded nodes
        if lastFloodedLeave in floodedNodes:
            floodedNodes.remove(lastFloodedLeave)

        print(waterHeight)

        #equationSolver = linearEquationSolverForFlows(graphWithGeodesicHeightAfterAuffangbeckenBuilt, waterHeight, self.rain, self.timeSteps, self.gridSize)
        #waterHeight = equationSolver.solveLinearEquationSystem()

        new_water_height = {"waterHeight": waterHeight}

        return floodingTimes, waterAmounts, modGraph, modArea, new_water_height