import csv
import os
import numpy as np
import networkx as nx
import matplotlib as plt
import math

class gisDataToInstance:
    def __init__(self, geosteps, gisData):
        self.geosteps = geosteps
        self.gisData = gisData
        self.columnwiseMaximum, self.columnwiseMinimum = self.getMaximumAndMinimumXAndYCoordinates()
        self.positionAndGeodesicHeight = self.createPositionAndGeodesicHeight()
        self.originalGraph = self.createGraph()
        self.ratios = self.createPositionAndRatio()
        self.areas = self.createAreas()

    def getMaximumAndMinimumXAndYCoordinates(self):
        myNumpyMatrix = np.array(self.gisData)
        columnwiseMaximum = np.max(myNumpyMatrix, axis=0)
        columnwiseMinimum = np.min(myNumpyMatrix, axis=0)
        return columnwiseMaximum, columnwiseMinimum

    def createPositionAndGeodesicHeight(self):
        positionAndGeodesicHeight = dict()
        for row in self.gisData:
            xpos = (row[0] - self.columnwiseMinimum[0]) / self.geosteps + 1
            ypos = (row[1] - self.columnwiseMinimum[1]) / self.geosteps + 1
            positionAndGeodesicHeight[(int(xpos), int(ypos))] = row[2] / 1000
        return positionAndGeodesicHeight

    def createGraph(self):
        def addEdge(source, sink):
            if sink in self.positionAndGeodesicHeight.keys():
                if self.positionAndGeodesicHeight[source] > self.positionAndGeodesicHeight[sink]:
                    myGraph.add_edge(source, sink)

        myGraph = nx.DiGraph()

        #adding the nodes
        for n in self.positionAndGeodesicHeight.keys():
            myGraph.add_node(n)

        #adding the edges
        for n in self.positionAndGeodesicHeight.keys():
            addEdge(n, (n[0] - 1, n[1]))
            addEdge(n, (n[0] + 1, n[1]))
            addEdge(n, (n[0], n[1] - 1))
            addEdge(n, (n[0], n[1] + 1))

        return myGraph

    def createPositionAndRatio(self):
        ratios = dict()
        for n in self.originalGraph.nodes:
            sumOfDifferencesInGeodesicHeightsOverOutgoingArcs = 0
            for v in self.originalGraph.successors(n):
                sumOfDifferencesInGeodesicHeightsOverOutgoingArcs = sumOfDifferencesInGeodesicHeightsOverOutgoingArcs + (self.positionAndGeodesicHeight[n] - self.positionAndGeodesicHeight[v])
            if sumOfDifferencesInGeodesicHeightsOverOutgoingArcs > 0:
                for v in self.originalGraph.successors(n):
                    ratios[(n, v)] = (self.positionAndGeodesicHeight[n] - self.positionAndGeodesicHeight[v]) / sumOfDifferencesInGeodesicHeightsOverOutgoingArcs
            else:
                for v in self.originalGraph.successors(n):
                    ratios[(n, v)] = 1/len(self.originalGraph.successors(n))
        return ratios

    def createAreas(self):
        areas = dict()
        for n in self.originalGraph.nodes:
            #normed to 25 x 25 grid
            areas[n] = math.pow(self.geosteps, 2) / 625
        return areas



    def drawGraph(self):
        pos = dict()
        for n in self.originalGraph.nodes:
            pos[n] = n
        nx.draw_networkx_nodes(self.originalGraph, pos)
        nx.draw_networkx_edges(self.originalGraph, pos)
        plt.pyplot.show()