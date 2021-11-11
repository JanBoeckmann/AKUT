from gekko import GEKKO
import networkx as nx
import gurobipy as gurobi

class linearEquationSolverForFlows:
    def __init__(self, graph, waterHeight, rain, timeSteps, gridSize):
        self.graphWithGeodesicHeight = graph
        self.waterHeight = waterHeight
        self.rain = rain
        self.timeSteps = timeSteps
        self.gridSize = gridSize
        self.geodesicHeight = self.getGeodesicHeight()
        self.ratios = self.getRatios()
        self.area = self.getArea()
        self.fullEdge = self.computeEdgeFull()

    def getGeodesicHeight(self):
        geodesicHeight = nx.get_node_attributes(self.graphWithGeodesicHeight, "geodesicHeight")
        return geodesicHeight

    def getRatios(self):
        ratios = nx.get_edge_attributes(self.graphWithGeodesicHeight, "edgeProportion")
        return ratios

    def getArea(self):
        area = nx.get_node_attributes(self.graphWithGeodesicHeight, "concatenatedNodes")
        area.update((x, y * pow(self.gridSize, 2)) for x, y in area.items())
        return area

    def computeEdgeFull(self):
        fullEdge = {}
        for e in self.graphWithGeodesicHeight.edges():
            if self.waterHeight[e[1]] + self.geodesicHeight[e[1]] >= self.geodesicHeight[e[0]]:
                fullEdge[e] = 1
            else:
                fullEdge[e] = 0
        return fullEdge

    def solveLinearEquationSystem(self):
        def declareVariables():
            #flows
            for e in self.graphWithGeodesicHeight.edges:
                if self.fullEdge[e] == 0:
                    flows[e] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="f_" + str(e[0]) + "_" + str(e[1]))
                else:
                    flows[e] = myModel.addVar(lb=-99999, vtype=gurobi.GRB.CONTINUOUS, name="f_" + str(e[0]) + "_" + str(e[1]))

            #excess
            for n in self.graphWithGeodesicHeight.nodes:
                excess[n] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="F_" + str(n))

            #waterHeight
            for n in self.graphWithGeodesicHeight.nodes:
                waterHeight[n] = myModel.addVar(lb=0.0, vtype=gurobi.GRB.CONTINUOUS, name="h_" + str(n))

        def addConstraints():
            #constraint for the excess
            for n in self.graphWithGeodesicHeight.nodes:
                myModel.addConstr(excess[n], gurobi.GRB.EQUAL, gurobi.quicksum(flows[e] for e in self.graphWithGeodesicHeight.in_edges(n)) - gurobi.quicksum(flows[e] for e in self.graphWithGeodesicHeight.out_edges(n)) + self.rain * self.timeSteps * self.area[n], name="excess_" + str(n))

            # constraint for water height
            for n in self.graphWithGeodesicHeight.nodes:
                myModel.addConstr(waterHeight[n], gurobi.GRB.EQUAL, excess[n] / self.area[n], name="ConnectWaterHeightToWaterAmount_" + str(n))

            # Ratios of Flows
            for n in self.graphWithGeodesicHeight.nodes:
                successors = []
                for s in self.graphWithGeodesicHeight.successors(n):
                    if self.fullEdge[(n, s)] == 0:
                        successors.append(s)
                if len(successors) >= 2:
                    for p1 in range(len(successors)):
                        for p2 in range(p1 + 1, len(successors)):
                            myModel.addConstr(flows[(n, successors[p1])] - (self.ratios[(n, successors[p1])] / self.ratios[(n, successors[p2])] * flows[(n, successors[p2])]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")
                            myModel.addConstr(flows[(n, successors[p2])] - (self.ratios[(n, successors[p2])] / self.ratios[(n, successors[p1])] * flows[(n, successors[p1])]), gurobi.GRB.LESS_EQUAL, 0, name="flowDistribution")

            #constraints for full arcs
            for e in self.graphWithGeodesicHeight.edges:
                if self.fullEdge[e] == 1:
                    myModel.addConstr(self.geodesicHeight[e[0]] + waterHeight[e[0]] - (self.geodesicHeight[e[1]] + waterHeight[e[1]]), gurobi.GRB.EQUAL, 0, name="effectsOnFullArcForFlows")

            for e in self.graphWithGeodesicHeight.edges:
                myModel.addConstr(self.geodesicHeight[e[0]] + waterHeight[e[0]] - (self.geodesicHeight[e[1]] + waterHeight[e[1]]), gurobi.GRB.GREATER_EQUAL, 0, name="effectsOnFullArcForFlows")

            #constraints for non-full arcs
            for e in self.graphWithGeodesicHeight.edges:
                if self.fullEdge[e] == 0:
                    myModel.addConstr(waterHeight[e[0]], gurobi.GRB.EQUAL, 0, name="noWaterStoredIfThereIsStillAnActiveOutArc")

        def putWaterHeightIntoDictionary():
            newDict = {}
            for n in self.graphWithGeodesicHeight.nodes:
                v = myModel.getVarByName("h_" + str(n))
                newDict[n] = v.x
            return newDict

        def putExcessIntoDictionary():
            newDict = {}
            for n in self.graphWithGeodesicHeight.nodes:
                v = myModel.getVarByName("F_" + str(n))
                newDict[n] = v.x
            return newDict

        def putFlowsIntoDictionary():
            newDict = {}
            for e in self.graphWithGeodesicHeight.edges:
                v = myModel.getVarByName("f_" + str(e[0]) + "_" + str(e[1]))
                flowValue = v.x
                if flowValue >= 0:
                    newDict[e] = v.x
                    newDict[(e[1], e[0])] = 0
                else:
                    newDict[e] = 0
                    newDict[(e[1], e[0])] = -v.x
            return newDict

        def putActiveArcIntoDictionary(flows):
            newDict = {}
            for e in flows:
                if flows[e] > 0:
                    newDict[e] = 1
                else:
                    newDict[e] = 0
            return newDict

        def computeReturnDict():
            solutionWaterHeight = putWaterHeightIntoDictionary()
            solutionExcess = putExcessIntoDictionary()
            solutionFlows = putFlowsIntoDictionary()
            solutionActiveAcrs = putActiveArcIntoDictionary(solutionFlows)
            newDict = {}
            newDict["waterHeight"] = solutionWaterHeight
            newDict["excess"] = solutionExcess
            newDict["flows"] = solutionFlows
            newDict["activeArcs"] = solutionActiveAcrs
            newDict["fullArc"] = self.fullEdge #careful: when direction of arc has reversed, will have to reverse this as well to hand it over to gurobi
            newDict["geodesicHeight"] = self.geodesicHeight
            return newDict

        def compute_return_dict_if_infeasible():
            newDict = {}
            newDict["waterHeight"] = self.waterHeight
            return newDict

        flows = {}
        excess = {}
        waterHeight = {}
        myModel = gurobi.Model("myModelForSolvingAnLGS")
        declareVariables()
        addConstraints()
        myModel.setParam("NumericFocus", 3)
        myModel.setParam("Presolve", 0)
        myModel.feasRelaxS(1, False, False, True)
        myModel.optimize()
        #myModel.computeIIS()
        #myModel.write(filename="myModelForSolvingAnLGS.ilp")

        print("GRB.OPTIMAL: ", gurobi.GRB.OPTIMAL)


        if gurobi.GRB.OPTIMAL == 3:
            initialSolution = compute_return_dict_if_infeasible()
        else:
            initialSolution = computeReturnDict()

        return initialSolution