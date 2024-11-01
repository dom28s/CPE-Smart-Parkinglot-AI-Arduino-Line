from ultralytics import YOLO
from shapely.geometry import Polygon
import cv2 as cv
import numpy as np
from scipy.spatial import distance as dist
from collections import OrderedDict
import json
import os


class CentroidTracker:
    def __init__(self, maxDisappeared=50):
        # Store the maximum number of consecutive frames an object is allowed to be "disappeared"
        self.maxDisappeared = maxDisappeared

        # Initialize the next unique object ID along with two ordered dictionaries to keep track of mapping a given object ID to its centroid and number of consecutive frames it has been marked as "disappeared", respectively
        self.nextObjectID = 0
        self.objects = OrderedDict()
        self.disappeared = OrderedDict()

    def register(self, centroid):
        # Register a new object by assigning the next available object ID and storing the centroid
        self.objects[self.nextObjectID] = centroid
        self.disappeared[self.nextObjectID] = 0
        self.nextObjectID += 1

    def deregister(self, objectID):
        # Remove the object ID from both object and disappeared dictionaries
        del self.objects[objectID]
        del self.disappeared[objectID]

    def update(self, rects):
        # If no bounding boxes were provided, mark existing objects as "disappeared"
        if len(rects) == 0:
            for objectID in list(self.disappeared.keys()):
                self.disappeared[objectID] += 1
                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)
            return self.objects

        # Initialize an array of input centroids for the current frame
        inputCentroids = np.zeros((len(rects), 2), dtype="int")

        # Loop over the bounding boxes and compute the centroid
        for (i, (startX, startY, endX, endY)) in enumerate(rects):
            cX = int((startX + endX) / 2.0)
            cY = int((startY + endY) / 2.0)
            inputCentroids[i] = (cX, cY)

        # If there are no objects being tracked, register each input centroid as a new object
        if len(self.objects) == 0:
            for i in range(0, len(inputCentroids)):
                self.register(inputCentroids[i])
        else:
            # Grab the set of object IDs and corresponding centroids
            objectIDs = list(self.objects.keys())
            objectCentroids = list(self.objects.values())

            # Compute the distance between each pair of object centroids and input centroids, then find the smallest distances between them
            D = dist.cdist(np.array(objectCentroids), inputCentroids)
            rows = D.min(axis=1).argsort()
            cols = D.argmin(axis=1)[rows]

            # Keep track of which rows and columns have already been examined
            usedRows = set()
            usedCols = set()

            for (row, col) in zip(rows, cols):
                # If either the row or column has been examined before, ignore it
                if row in usedRows or col in usedCols:
                    continue

                # Otherwise, grab the object ID, update its centroid, and reset the disappeared counter
                objectID = objectIDs[row]
                self.objects[objectID] = inputCentroids[col]
                self.disappeared[objectID] = 0

                # Mark the row and column as used
                usedRows.add(row)
                usedCols.add(col)

            # Compute the set of unused rows and columns
            unusedRows = set(range(0, D.shape[0])).difference(usedRows)
            unusedCols = set(range(0, D.shape[1])).difference(usedCols)

            # Handle disappeared objects
            for row in unusedRows:
                objectID = objectIDs[row]
                self.disappeared[objectID] += 1

                if self.disappeared[objectID] > self.maxDisappeared:
                    self.deregister(objectID)

            # Handle new object registrations
            for col in unusedCols:
                self.register(inputCentroids[col])

        return self.objects

