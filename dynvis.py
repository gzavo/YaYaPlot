# -*- coding: utf-8 -*-
"""
Dynamic Visualizer

@author: Gabor Zavodszky
@license: GPLv3
@version: 0.1
"""

import os
import sys
from pyqtgraph.Qt import QtCore, QtGui
import pyqtgraph as pg
import pyqtgraph.opengl as gl
import numpy as np


## Class to watch file content changes
class FileWatcher:
    def __init__(self, fileName = None):
        self.fileName = ''
        self.fileHandle = -1
        self.fileOSNO = -1
        
        if fileName is not None:
            self.open(fileName)
        
    def open(self, fileName):
        self.fileName = fileName
        self.fileHandle = open(fileName, "r")
        self.fileOSNO = os.fstat(self.fileHandle.fileno()).st_ino
    
    def readData(self):
        while True:
            line = self.fileHandle.readline()
            if not line:
                break
            yield line

        try:
            if os.stat(self.fileName).st_ino != self.fileOSNO:
                newFileHandle = open(self.fileName, "r")
                self.fileHandle.close()
                self.fileHandle = newFileHandle
                self.fileOSNO = os.fstat(self.fileHandle.fileno()).st_ino
        except IOError:
            pass
       

class ItemHandler:
    def __init__(self, glWidget):
        self.ItemList = []
        self.DataFrames = []
        self.w = glWidget
        
        self.cColor = (1,0,0,1) # RGBA
        
    def addDataFrame(self, stringStream):                
        self.DataFrames.append(stringStream)

    def buildLastScene(self):
        nr = len(self.DataFrames) - 1
        self.buildScene(nr)
    
    def buildScene(self, nrDataFrame):
        global C
        for l in self.DataFrames[nrDataFrame]:
            c = l.split()
             
            if c[0] is 'c':   # Change colour
                arg = [float(i) for i in c[1:]]
                self.cColor = (arg[0], arg[1], arg[2], arg[3])
                
            elif c[0] is 's':     #Add a sphere
                arg = [float(i) for i in c[1:]]
                md = gl.MeshData.sphere(rows=10, cols=20, radius=arg[3])
                m = gl.GLMeshItem(meshdata=md, color = self.cColor, smooth=False, shader='shaded')#, shader='balloon')
                m.translate(arg[0], arg[1], arg[2])
                m.translate(-C[0], -C[1], -C[2])
                self.ItemList.append(m)
                self.w.addItem(m)

            elif c[0] is 't':   # Add tube
                arg = [float(i) for i in c[1:]]
                md = gl.MeshData.cylinder(rows=10, cols=20, radius=(arg[3], arg[4]))
                m = gl.GLMeshItem(meshdata=md, color = self.cColor, smooth=False)#, shader='balloon')
                m.translate(arg[0], arg[1], arg[2])
                m.translate(-C[0], -C[1], -C[2])
                self.ItemList.append(m)
                self.w.addItem(m)
            
            elif c[0] is 'l':   # Add a line
                arg = [float(i) for i in c[1:]]
                pos = [ [arg[0], arg[1], arg[2]], [arg[3], arg[4], arg[5]] ]
                line = gl.GLLinePlotItem(pos=np.array(pos), width=arg[6], antialias=True)
                line.translate(-C[0], -C[1], -C[2])
                self.ItemList.append(line)
                self.w.addItem(line)
            
            else:               # Unhandled directive
                print("Unknown command line: " + l )
    
    def updateScene(self, nrDataFrame):
        pass    # TODO: implement it when needed
    
    def clearScene(self):
        for i in self.ItemList:
            self.w.removeItem(i)
        self.ItemList = []


def playScenes():
    global index, ih
    index += 1
    if index >= len(ih.DataFrames):
        pass
    else:
        ih.buildScene(index)


def parseFile():
    global isRealTimeView
    
    tmpRealtimeView = isRealTimeView
    isRealTimeView = False
    updateFile()
    isRealTimeView = tmpRealtimeView
    
    if len(ih.DataFrames) > 0:
        if isRealTimeView:
            ih.buildLastScene()
        else:
            ih.buildScene(0)


def updateViewCoordSystem():
    global widg, DOMAIN, C, boxDomain

    widg.setCameraPosition(distance=DOMAIN[1]*2.0)

    if boxDomain is not None:
        widg.removeItem(boxDomain)

    boxDomain = gl.GLBoxItem()
    boxDomain.setSize(DOMAIN[0],DOMAIN[1],DOMAIN[2])
    boxDomain.translate(-C[0], -C[1], -C[2])
    widg.addItem(boxDomain)
    #TODO: at some point allow to reset the camera handling as well
    
def updateFile():
    global fw, frame, ih, isRealTimeView, C, DOMAIN
    lines = fw.readData()
    for l in lines:
        if l[0:3] == "END":
            # The lines until now since the last "NEW" make up a scene
            ih.addDataFrame(frame)
            if isRealTimeView:
                ih.buildLastScene()
            frame=[]  
        
        elif l[0:3] == "NEW":
            # Clear the currently displayed scene
            ih.clearScene()
        
        elif l[0:4] == "GRID":
            #TODO: Allow rotation for the grid
            global widg
            ## Add a grid to the view
            g = gl.GLGridItem()
            g.scale(DOMAIN[3]/10.0, DOMAIN[4]/10.0, 1) #TODO:scale this using domain size
            g.setDepthValue(10)  # draw grid after surfaces since they may be translucent
            #g.translate(C[0], C[1], C[2])
            widg.addItem(g)
                    
        elif l[0:6] == "DOMAIN":
            # Handle domain settings
            c = l.split()
            arg = [float(i) for i in c[1:]]
            
            C = (arg[0], arg[1], arg[2])
            DOMAIN = (arg[3], arg[4], arg[5])
            updateViewCoordSystem()
        
        else:
            frame.append(l)  

        
if __name__ == '__main__':
    ## Create a GL View widget to display data
    app = QtGui.QApplication([])
    widg = gl.GLViewWidget()
    widg.show()
    widg.setWindowTitle('Uniform Dynamic Visualisation')
    
    boxDomain = None
    DOMAIN = (5.0, 5.0, 5.0)  
    C = (0,0,0)
    updateViewCoordSystem()
        
    index = 0
    isRealTimeView = True

    ## Timer to play the scenes TODO: Implement the rest of this functionality
    timer = QtCore.QTimer()
    timer.timeout.connect(playScenes)
#    timer.start(100)
    
    ## Create the file watcher class
    if len(sys.argv) > 1:
        fname = sys.argv[1]
    else:
        fname = "data.out"
    
    frame = []
    fw = FileWatcher(fname)
    
    ## Create item handler
    ih = ItemHandler(widg)

    ## See if the file already contains frames
    parseFile()
    
    ## Timer to keep reding the input file
    timer2 = QtCore.QTimer()
    timer2.timeout.connect(updateFile)
    timer2.start(200)  # Trigger it every 0.2 second


    ## Start Qt event loop unless running in interactive mode.
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()