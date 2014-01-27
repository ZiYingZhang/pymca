#/*##########################################################################
# Copyright (C) 2004-2014 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# This file is free software; you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2 of the License, or (at your option)
# any later version.
#
# This file is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
#############################################################################*/
__author__ = "V.A. Sole - ESRF Data Analysis"
__license__ = "LGPL"
__doc__ = """
Matplotlib Plot backend.
"""
import numpy
from numpy import vstack as numpyvstack
import sys
from .. import PlotBackend
from matplotlib import cm
from matplotlib.font_manager import FontProperties
# This should be independent of Qt
if "tk" in sys.argv:
    if sys.version < '3.0':
        import Tkinter as Tk
    else:
        import tkinter as Tk
else:
    from PyQt4 import QtCore, QtGui
if ("PyQt4" in sys.modules) or ("PySide" in sys.modules): 
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
    TK = False
    QT = True
elif ("Tkinter" in sys.modules) or ("tkinter") in sys.modules:
    TK = True
    QT = False
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches
Rectangle = patches.Rectangle
Polygon = patches.Polygon
from matplotlib.lines import Line2D
from matplotlib.text import Text
from matplotlib.image import AxesImage, NonUniformImage
import time

DEBUG = 0

class MatplotlibGraph(FigureCanvas):
    def __init__(self, parent=None, **kw):
        #self.figure = Figure(figsize=size, dpi=dpi) #in inches
        self.fig = Figure()
        if TK:
            self._canvas = FigureCanvas.__init__(self, self.fig, master=parent)
        else:
            self._canvas = FigureCanvas.__init__(self, self.fig)
            # get the default widget color
            color = self.palette().color(self.backgroundRole())
            color = "#%x" % color.rgb()
            if len(color) == 9:
                color = "#" + color[3:]
            self.fig.set_facecolor(color)
            # that's it
        self.ax = self.fig.add_axes([.15, .15, .75, .75])
        # this respects aspect size
        # self.ax = self.fig.add_subplot(111, aspect='equal')
        # This should be independent of Qt
        if "PyQt4" in sys.modules or "PySide" in sys.modules:
            FigureCanvas.setSizePolicy(self,
                                   QtGui.QSizePolicy.Expanding,
                                   QtGui.QSizePolicy.Expanding)

        self.__lastMouseClick = ["middle", time.time()]
        self.__zooming = False
        self.__picking = False
        self._zoomStack = []
        self.xAutoScale = True
        self.yAutoScale = True

        #info text
        self._infoText = None

        #drawingmode handling
        self.setDrawModeEnabled(False)
        self.__drawModeList = ['line', 'polygon']
        self.__drawing = False
        self._drawingPatch = None
        self._drawModePatch = 'line'

        #event handling
        self._callback = self._dummyCallback
        self._x0 = None
        self._y0 = None
        self._zoomRectangle = None
        self.fig.canvas.mpl_connect('button_press_event',
                                    self.onMousePressed)
        self.fig.canvas.mpl_connect('button_release_event',
                                    self.onMouseReleased)
        self.fig.canvas.mpl_connect('motion_notify_event',
                                    self.onMouseMoved)
        self.fig.canvas.mpl_connect('pick_event',
                                    self.onPick)

    def _dummyCallback(self, ddict):
        if DEBUG:
            print(ddict)

    def setCallback(self, callbackFuntion):
        self._callback = callbackFuntion

    def onPick(self, event):
        middleButton = 2
        rightButton = 3
        button = event.mouseevent.button 
        if button == middleButton:
            # do nothing with the midle button
            return
        elif button == rightButton:
            button = "right"
        else:
            button = "left"
        if self._drawModeEnabled:
            # forget about picking or zooming
            # should one disconnect when setting the mode?
            return
        self.__picking = False
        self._pickingInfo = {}
        if isinstance(event.artist, Line2D):
            # we only handle curves and markers for the time being
            self.__picking = True
            artist = event.artist
            label = artist.get_label()
            ind = event.ind
            #xdata = thisline.get_xdata()
            #ydata = thisline.get_ydata()
            #print('onPick line:', zip(numpy.take(xdata, ind),
            #                           numpy.take(ydata, ind)))
            self._pickingInfo['artist'] = artist
            self._pickingInfo['event_ind'] = ind
            if label.startswith("__MARKER__"):
                label = label[10:]
                self._pickingInfo['type'] = 'marker' 
                self._pickingInfo['label'] = label
                if 'draggable' in artist._plot_options:
                    self._pickingInfo['draggable'] = True
                else:
                    self._pickingInfo['draggable'] = False
                if 'selectable' in artist._plot_options:
                    self._pickingInfo['selectable'] = True
                else:
                    self._pickingInfo['selectable'] = False
                self._pickingInfo['infoText'] = artist._infoText
            else:
                self._pickingInfo['type'] = 'curve' 
                self._pickingInfo['label'] = label
                self._pickingInfo['artist'] = artist
                xdata = artist.get_xdata()
                ydata = artist.get_ydata()
                self._pickingInfo['xdata'] = xdata[ind]
                self._pickingInfo['ydata'] = ydata[ind]
                self._pickingInfo['infoText'] = None
            if self._pickingInfo['infoText'] is None:
                if self._infoText is None:
                    self._infoText = self.ax.text(event.mouseevent.xdata,
                                                  event.mouseevent.ydata,
                                                  label)
                else:
                    self._infoText.set_position((event.mouseevent.xdata,
                                                event.mouseevent.ydata))
                    self._infoText.set_text(label)
                self._pickingInfo['infoText'] = self._infoText
            self._pickingInfo['infoText'].set_visible(True)
            if DEBUG:
                print("%s %s selected" % (self._pickingInfo['type'].upper(),
                                          self._pickingInfo['label']))
        elif isinstance(event.artist, Rectangle):
            patch = event.artist
            print('onPick patch:', patch.get_path())
        elif isinstance(event.artist, Text):
            text = event.artist
            print('onPick text:', text.get_text())
        elif isinstance(event.artist, AxesImage):
            self.__picking = True
            artist = event.artist
            #print dir(artist)
            self._pickingInfo['artist'] = artist
            #self._pickingInfo['event_ind'] = ind
            label = artist.get_label()
            self._pickingInfo['type'] = 'image' 
            self._pickingInfo['label'] = label
            self._pickingInfo['draggable'] = False
            self._pickingInfo['selectable'] = False
            if hasattr(artist, "_plot_options"):
                if 'draggable' in artist._plot_options:
                    self._pickingInfo['draggable'] = True
                else:
                    self._pickingInfo['draggable'] = False
                if 'selectable' in artist._plot_options:
                    self._pickingInfo['selectable'] = True
                else:
                    self._pickingInfo['selectable'] = False
        else:
            print("unhandled", event.artist)

    def setDrawModeEnabled(self, flag=True):
        self._drawModeEnabled = flag
        if flag:
            #cannot draw and zoom simultaneously
            self.setZoomModeEnabled(False)

    def setZoomModeEnabled(self, flag=True):
        if flag:
            self._zoomEnabled = True
            self.setDrawModeEnabled(False)
        else:
            self._zoomEnabled = True

    def setDrawModePatch(self, mode=None):
        if mode is None:
            mode = self.__drawModeList[0]

        mode = mode.lower()
        #raise an error in case of an invalid mode
        modeIndex = self.__drawModeList.index(mode)

        self._drawModePatch = mode


    def onMousePressed(self, event):
        if DEBUG:
            print("onMousePressed, event = ",event.xdata, event.ydata)
            print("Mouse button = ", event.button)
        if event.inaxes != self.ax:
            if DEBUG:
                print("RETURNING")
            return        
        button = event.button
        leftButton = 1
        middleButton = 2
        rightButton = 3
        if button == middleButton:
            # do nothing with the middle button
            return

        self._x0 = event.xdata
        self._y0 = event.ydata
        self._x0Pixel = event.x
        self._y0Pixel = event.y
        self._x1 = event.xdata
        self._y1 = event.ydata
        self._x1Pixel = event.x
        self._y1Pixel = event.y
        
        self.__movingMarker = 0
        # picking handling
        if self.__picking:
            if DEBUG:
                print("PICKING, Ignoring zoom")
            self.__zooming = False
            self.__drawing = False
            self.__markerMoving = False
            if self._pickingInfo['type'] == "marker":
                if button == rightButton:
                    # only selection or movement
                    self._pickingInfo = {}
                    return
                artist = self._pickingInfo['artist']
                if button == leftButton:
                    if self._pickingInfo['draggable']:
                        self.__markerMoving = True
                    if 'xmarker' in artist._plot_options:
                        artist.set_xdata(event.xdata)
                    elif 'ymarker' in artist._plot_options:
                        artist.set_ydata(event.ydata)
                    else:
                        artist.set_xdata(event.xdata)
                        artist.set_ydata(event.ydata)
                    self.fig.canvas.draw()
                    ddict = {}
                    if self.__markerMoving:
                        ddict['event'] = "markerMoving"
                    else:
                        ddict['event'] = "markerClicked"
                    ddict['label'] = self._pickingInfo['label']
                    ddict['type'] = self._pickingInfo['type']
                    ddict['draggable'] = self._pickingInfo['draggable']
                    ddict['selectable'] = self._pickingInfo['selectable']
                    ddict['x'] = self._x0
                    ddict['y'] = self._y0
                    ddict['xpixel'] = self._x0Pixel
                    ddict['ypixel'] = self._y0Pixel
                    ddict['xdata'] = artist.get_xdata()
                    ddict['ydata'] = artist.get_ydata()
                    if button == leftButton:
                        ddict['button'] = "left"
                    else:
                        ddict['button'] = "right"
                    self._callback(ddict)
                return
            elif self._pickingInfo['type'] == "curve":
                ddict = {}
                ddict['event'] = "curveClicked"
                #ddict['event'] = "legendClicked"
                ddict['label'] = self._pickingInfo['label']
                ddict['type'] = self._pickingInfo['type']
                ddict['x'] = self._x0
                ddict['y'] = self._y0
                ddict['xpixel'] = self._x0Pixel
                ddict['ypixel'] = self._y0Pixel
                ddict['xdata'] = self._pickingInfo['xdata']
                ddict['ydata'] = self._pickingInfo['ydata']
                if button == leftButton:
                    ddict['button'] = "left"
                else:
                    ddict['button'] = "right"
                self._callback(ddict)
                return
            elif self._pickingInfo['type'] == "image":
                artist = self._pickingInfo['artist']
                ddict = {}
                ddict['event'] = "imageClicked"
                #ddict['event'] = "legendClicked"
                ddict['label'] = self._pickingInfo['label']
                ddict['type'] = self._pickingInfo['type']
                ddict['x'] = self._x0
                ddict['y'] = self._y0
                ddict['xpixel'] = self._x0Pixel
                ddict['ypixel'] = self._y0Pixel
                xScale = artist._plot_info['xScale']
                yScale = artist._plot_info['yScale']
                col = (ddict['x'] - xScale[0])/float(xScale[1])
                row = (ddict['y'] - yScale[0])/float(yScale[1])
                ddict['row'] = int(row)
                ddict['col'] = int(col)
                if button == leftButton:
                    ddict['button'] = "left"
                else:
                    ddict['button'] = "right"
                self.__picking = False
                self._callback(ddict)

        self.__time0 = -1.0
        if event.button == rightButton:
            #right click
            self.__zooming = False
            if self._drawingPatch is not None:
                self._drawingPatch.remove()
                self.draw()
                self._drawingPatch = None
            return

        self.__time0 = time.time()
        self.__zooming = self._zoomEnabled
        self._zoomRect = None
        self._xmin, self._xmax  = self.ax.get_xlim()
        self._ymin, self._ymax  = self.ax.get_ylim()

        self.__drawing = self._drawModeEnabled
            
    def onMouseMoved(self, event):
        if DEBUG:
            print("onMouseMoved, event = ",event.xdata, event.ydata)
        if event.inaxes != self.ax:
            if DEBUG:
                print("RETURNING")
            return

        #as default, export the mouse in graph coordenates
        self._x1 = event.xdata
        self._y1 = event.ydata
        self._x1Pixel = event.x
        self._y1Pixel = event.y
        ddict= {'event':'mouseMoved',
              'x':self._x1,
              'y':self._y1,
              'xpixel':self._x1Pixel,
              'ypixel':self._y1Pixel}
        self._callback(ddict)
        # should this be made by Plot1D with the previous call???
        # The problem is Plot1D does not know if one is zooming or drawing
        if not (self.__zooming or self.__drawing or self.__picking):
            # this corresponds to moving without click
            marker = None
            for artist in self.ax.lines:
                if marker is not None:
                    break
                label = artist.get_label()
                if label.startswith("__MARKER__"):
                    #data = artist.get_xydata()[0:1]
                    x, y = artist.get_xydata()[-1]
                    pixels = self.ax.transData.transform(numpyvstack([x,y]).T)
                    xPixel, yPixels = pixels.T
                    if 'xmarker' in artist._plot_options:
                        if abs(xPixel-event.x) < 5:
                            marker = artist
                    elif 'ymarker' in artist._plot_options:
                        if abs(yPixel-event.y) < 5:
                            marker = artist
                    elif (abs(xPixel-event.x) < 5) and \
                         (abs(yPixel-event.y) < 5):
                            marker = artist
            if QT:
                oldShape = self.cursor().shape()
                if oldShape not in [QtCore.Qt.SizeHorCursor,
                                QtCore.Qt.SizeVerCursor,
                                QtCore.Qt.PointingHandCursor,
                                QtCore.Qt.OpenHandCursor,
                                QtCore.Qt.SizeAllCursor]:
                    self._originalCursorShape = oldShape
            if marker is not None:
                ddict = {}
                ddict['event'] = 'hover'
                ddict['type'] = 'marker' 
                ddict['label'] = marker.get_label()[10:]
                if 'draggable' in marker._plot_options:
                    ddict['draggable'] = True
                    if QT:
                        self.setCursor(QtGui.QCursor(QtCore.Qt.SizeHorCursor))
                else:
                    ddict['draggable'] = False
                if 'selectable' in marker._plot_options:
                    ddict['selectable'] = True
                    if QT:
                        self.setCursor(QtGui.QCursor(QtCore.Qt.PointingHandCursor))
                else:
                    ddict['selectable'] = False
                ddict['x'] = self._x1
                ddict['y'] = self._y1
                ddict['xpixel'] = self._x1Pixel,
                ddict['ypixel'] = self._y1Pixel
                self._callback(ddict)
            elif QT:
                if self._originalCursorShape in [QtCore.Qt.SizeHorCursor,
                                QtCore.Qt.SizeVerCursor,
                                QtCore.Qt.PointingHandCursor,
                                QtCore.Qt.OpenHandCursor,
                                QtCore.Qt.SizeAllCursor]:
                    self.setCursor(QtGui.QCursor(QtCore.Qt.ArrowCursor))
                else:
                    self.setCursor(QtGui.QCursor(self._originalCursorShape))
            return
        if self.__picking:
            if self.__markerMoving:
                artist = self._pickingInfo['artist']
                infoText = self._pickingInfo['infoText']
                if 'xmarker' in artist._plot_options:
                    artist.set_xdata(event.xdata)
                    ymin, ymax = self.ax.get_ylim()
                    delta = abs(ymax - ymin)
                    ymax = max(ymax, ymin) - 0.005 * delta
                    infoText.set_position((event.xdata, ymax))
                elif 'ymarker' in artist._plot_options:
                    artist.set_ydata(event.ydata)
                    infoText.set_position((event.xdata, event.ydata))
                else:
                    artist.set_xdata(event.xdata)
                    artist.set_ydata(event.ydata)
                self.fig.canvas.draw()
                ddict = {}
                ddict['event'] = "markerMoving"
                ddict['button'] = "left"
                ddict['label'] = self._pickingInfo['label']
                ddict['type'] = self._pickingInfo['type']
                ddict['draggable'] = self._pickingInfo['draggable']
                ddict['selectable'] = self._pickingInfo['selectable']
                ddict['x'] = self._x1
                ddict['y'] = self._y1
                ddict['xpixel'] = self._x1Pixel,
                ddict['ypixel'] = self._y1Pixel
                self._callback(ddict)
            return
        if (not self.__zooming) and (not self.__drawing):
            return

        if self._x0 is None:
            return
        
        if self.__zooming:
            if self._x1 < self._xmin:
                self._x1 = self._xmin
            elif self._x1 > self._xmax:
                self._x1 = self._xmax
     
            if self._y1 < self._ymin:
                self._y1 = self._ymin
            elif self._y1 > self._ymax:
                self._y1 = self._ymax
     
            if self._x1 < self._x0:
                x = self._x1
                w = self._x0 - self._x1
            else:
                x = self._x0
                w = self._x1 - self._x0
            if self._y1 < self._y0:
                y = self._y1
                h = self._y0 - self._y1
            else:
                y = self._y0
                h = self._y1 - self._y0

            if self._zoomRectangle is None:
                self._zoomRectangle = Rectangle(xy=(x,y),
                                               width=w,
                                               height=h,
                                               fill=False)
                self.ax.add_patch(self._zoomRectangle)
            else:
                self._zoomRectangle.set_bounds(x, y, w, h)
                #self._zoomRectangle._update_patch_transform()
            self.fig.canvas.draw()
            return
        
        if self.__drawing:
            if self._drawingPatch is None:
                self._mouseData = numpy.zeros((2,2), numpy.float32)
                self._mouseData[0,0] = self._x0
                self._mouseData[0,1] = self._y0
                self._mouseData[1,0] = self._x1
                self._mouseData[1,1] = self._y1
                self._drawingPatch = Polygon(self._mouseData,
                                             closed=True,
                                             fill=False)
                self.ax.add_patch(self._drawingPatch)
            elif self._drawModePatch == 'line':
                self._mouseData[1,0] = self._x1
                self._mouseData[1,1] = self._y1
                self._drawingPatch.set_xy(self._mouseData)
            elif self._drawModePatch == 'polygon':
                self._mouseData[-1,0] = self._x1
                self._mouseData[-1,1] = self._y1
                self._drawingPatch.set_xy(self._mouseData)
                self._drawingPatch.set_hatch('/')
                self._drawingPatch.set_closed(True)
            self.fig.canvas.draw()
        
    def onMouseReleased(self, event):
        if DEBUG:
            print("onMouseReleased, event = ",event.xdata, event.ydata)
        if self._infoText in self.ax.texts:
            self._infoText.set_visible(False)
        if self.__picking:
            self.__picking = False
            if self.__markerMoving:
                self.__markerMoving = False
                artist = self._pickingInfo['artist']
                ddict = {}
                ddict['event'] = "markerMoved"
                ddict['label'] = self._pickingInfo['label']
                ddict['type'] = self._pickingInfo['type']
                ddict['draggable'] = self._pickingInfo['draggable']
                ddict['selectable'] = self._pickingInfo['selectable']
                # use this and not the current mouse position because
                # it has to agree with the marker position
                ddict['x'] = artist.get_xdata()
                ddict['y'] = artist.get_ydata()
                ddict['xdata'] = artist.get_xdata()
                ddict['ydata'] = artist.get_ydata()
                self._callback(ddict)
            return

        if not hasattr(self, "__zoomstack"):
            self.__zoomstack = []

        if event.button == 3:
            #right click
            if self.__drawing:
                self.__drawing = False
                self._drawingPatch = None
                ddict = {}
                ddict['event'] = 'drawingFinished'
                ddict['type']  = '%s' % self._drawModePatch
                ddict['data']  = self._mouseData * 1
                self.mySignal(ddict)
                return

            self.__zooming = False
            if len(self._zoomStack):
                xmin, xmax, ymin, ymax = self._zoomStack.pop()
                self.setLimits(xmin, xmax, ymin, ymax)
                self.draw()

        if self.__drawing and (self._drawingPatch is not None):
            nrows, ncols = self._mouseData.shape                
            self._mouseData = numpy.resize(self._mouseData, (nrows+1,2))
            self._mouseData[-1,0] = self._x1
            self._mouseData[-1,1] = self._y1
            self._drawingPatch.set_xy(self._mouseData)

        if self._x0 is None:
            print("How can it be here???")
            return

        if self._zoomRectangle is None:
            currentTime = time.time() 
            deltaT =  currentTime - self.__time0
            if (deltaT < 0.1) or (self.__time0 < 0):
                # single or double click, no zooming
                self.__zooming = False
                ddict = {'x':event.xdata,
                         'y':event.ydata,
                         'xpixel':event.x,
                         'ypixel':event.y}
                leftButton = 1
                middleButton = 2
                rightButton = 3
                button = event.button
                if button == rightButton:
                    ddict['button'] = "right"
                else:
                    ddict['button'] = "left"
                if (button == self.__lastMouseClick[0]) and\
                   ((currentTime - self.__lastMouseClick[1]) < 0.6):
                    ddict['event'] = "mouseDoubleCliked"
                else:
                    ddict['event'] = "mouseClicked"
                self.__lastMouseClick = [button, time.time()]
                self._callback(ddict)
                return

        if self._zoomRectangle is not None:
            x, y = self._zoomRectangle.get_xy()
            w = self._zoomRectangle.get_width()
            h = self._zoomRectangle.get_height()
            self._zoomRectangle.remove()
            self._x0 = None
            self._y0 = None
            self._zoomRectangle = None
            xmin, xmax = self.ax.get_xlim()
            ymin, ymax = self.ax.get_ylim()
            self._zoomStack.append((xmin, xmax, ymin, ymax))
            self.setLimits(x, x+w, y, y+h)
            self.draw()

    def setLimits(self, xmin, xmax, ymin, ymax):
        self.ax.set_xlim(xmin, xmax)
        self.ax.set_ylim(ymin, ymax)
        # Next line forces a square display region
        #self.ax.set_aspect((xmax-xmin)/float(ymax-ymin))
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.limitsSet = True

    def resetZoom(self):
        xmin = None
        for line2d in self.ax.lines:
            label = line2d.get_label()
            if label.startswith("__MARKER__"):
                #it is a marker
                continue
            x = line2d.get_xdata()
            y = line2d.get_ydata()
            if not len(x) or not len(y):
                continue
            if xmin is None:
                xmin = x.min()
                xmax = x.max()
                ymin = y.min()
                ymax = y.max()
                continue
            xmin = min(xmin, x.min())
            xmax = max(xmax, x.max())
            ymin = min(ymin, y.min())
            ymax = max(ymax, y.max())
        if xmin is None:
            xmin = 0
            xmax = 1
            ymin = 0
            ymax = 1
        self.setLimits(xmin, xmax, ymin, ymax)
        self._zoomStack = []

class MatplotlibBackend(PlotBackend.PlotBackend):
    def __init__(self, parent=None, **kw):
       	#self.figure = Figure(figsize=size, dpi=dpi) #in inches
        self.graph = MatplotlibGraph(parent, **kw)
        self.ax = self.graph.ax
        PlotBackend.PlotBackend.__init__(self, parent)
        self._parent = parent
        self._logX = False
        self._logY = False
        self.setZoomModeEnabled = self.graph.setZoomModeEnabled
        self.setDrawModeEnabled = self.graph.setDrawModeEnabled
        self._oldActiveCurve = None
        self._oldActiveCurveLegend = None
        self._imageItem = None
        if self._imageItem is not None:
            # Temperature as defined in spslut
            from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
            cdict = {'red': ((0.0, 0.0, 0.0),
                             (0.5, 0.0, 0.0),
                             (0.75, 1.0, 1.0),
                             (1.0, 1.0, 1.0)),
                     'green': ((0.0, 0.0, 0.0),
                               (0.25, 1.0, 1.0),
                               (0.75, 1.0, 1.0),
                               (1.0, 0.0, 0.0)),
                     'blue': ((0.0, 1.0, 1.0),
                              (0.25, 1.0, 1.0),
                              (0.5, 0.0, 0.0),
                              (1.0, 0.0, 0.0))}
            #but limited to 256 colors for a faster display (of the colorbar)
            self.__temperatureCmap = LinearSegmentedColormap('temperature',
                                                             cdict, 256)
            cmap = self.__temperatureCmap
            x = numpy.arange(1000*1000.)
            x.shape = 1000, 1000
            self.ax.imshow(x,
                           interpolation='nearest',
                           origin='upper',
                           cmap=cmap,
                           norm=Normalize(0, 1000*1000.))

    def addCurve(self, x, y, legend, info=None, replace=False, replot=True, **kw):
        """
        Add the 1D curve given by x an y to the graph.
        :param x: The data corresponding to the x axis
        :type x: list or numpy.ndarray
        :param y: The data corresponding to the y axis
        :type y: list or numpy.ndarray
        :param legend: The legend to be associated to the curve
        :type legend: string or None
        :param info: Dictionary of information associated to the curve
        :type info: dict or None
        :param replace: Flag to indicate if already existing curves are to be deleted
        :type replace: boolean default False
        :param replot: Flag to indicate plot is to be immediately updated
        :type replot: boolean default True
        :returns: The legend/handle used by the backend to univocally access it.
        """
        if replace:
            self.clearCurves()
        else:
            self.removeCurve(legend, replot=False)
        if info is None:
            info = {}
        color = info.get('plot_color', 'k')
        symbol = info.get('plot_symbol', None)
        brush = color
        style = info.get('plot_line_style', '-')
        linewidth = 1
        """
        return self.plot(x, y, title=legend,
                         pen=color,
                         symbol=symbol,
                         symbolPen=color,
                         symbolBrush=color)

        line2D.set_marker(symbol)
        line2D.set_data(x, y)
        """
        if self._logY:
            curveList = self.ax.semilogy( x, y, label=legend,
                                          linestyle=style,
                                          color=color,
                                          linewidth=linewidth,
                                          picker=3,
                                          **kw)
        else:
            curveList = self.ax.plot( x, y, label=legend,
                                      linestyle=style,
                                      color=color,
                                      linewidth=linewidth,
                                      picker=3,
                                      **kw)
        curveList[-1].set_marker(symbol)
        curveList[-1]._plot_info = {'color':color,
                                      'linewidth':linewidth,
                                      'brush':brush,
                                      'style':style,
                                      'symbol':symbol,
                                      'label':legend}
        if self._oldActiveCurve in self.ax.lines:
            if self._oldActiveCurve.get_label() == legend:
                curveList[-1].set_color('k')
        elif self._oldActiveCurveLegend == legend:
            curveList[-1].set_color('k')
        return curveList[-1]

    def clear(self):
        """
        Clear all curvers and other items from the plot
        """
        n = list(range(len(self.ax.lines)))
        n.reverse()
        for i in n:
            line2d = self.ax.lines[i]
            line2d.remove()
            del line2d
        self.ax.clear()

    def clearImages(self):
        n = list(range(len(self.ax.images)))
        n.reverse()
        for i in n:
            image = self.ax.images[i]
            image.remove()
            del image
            del self.ax.images[i]

        n = list(range(len(self.ax.artists)))
        n.reverse()
        for i in n:
            artist = self.ax.artists[i]
            label = artist.get_label()
            if label.startswith("__IMAGE__"):
                artist.remove()
                del artist

    def clearCurves(self):
        """
        Clear all curves from the plot. Not the markers!!
        """
        n = list(range(len(self.ax.lines)))
        n.reverse()
        for i in n:
            line2d = self.ax.lines[i]
            label = line2d.get_label()
            if label.startswith("__MARKER__"):
                #it is a marker
                continue
            line2d.remove()
            del line2d

    def clearMarkers(self):
        """
        Clear all markers from the plot. Not the curves!!
        """
        n = list(range(len(self.ax.lines)))
        n.reverse()
        for i in n:
            line2d = self.ax.lines[i]
            label = line2d.get_label()
            if label.startswith("__MARKER__"):
                #it is a marker
                line2d.remove()
                del line2d

    def getGraphXLimits(self):
        """
        Get the graph X (bottom) limits.
        :return:  Minimum and maximum values of the X axis
        """
        return self.ax.get_xlim()

    def getGraphYLimits(self):
        """
        Get the graph Y (left) limits.
        :return:  Minimum and maximum values of the Y axis
        """
        return self.ax.get_ylim()

    def getWidgetHandle(self):
        """
        :return: Backend widget.
        """
        if hasattr(self.graph, "get_tk_widget"):
            return self.graph.get_tk_widget()
        else:
            return self.graph

    def insertMarker(self, x, y, label, color='k',
                      selectable=False, draggable=False,
                      **kw):
        """
        :param x: Horizontal position of the marker in graph coordenates
        :type x: float
        :param y: Vertical position of the marker in graph coordenates
        :type y: float
        :param label: Legend associated to the marker
        :type label: string
        :param color: Color to be used for instance 'blue', 'b', '#FF0000'
        :type color: string, default 'k' (black)
        :param selectable: Flag to indicate if the marker can be selected
        :type selectable: boolean, default False
        :param draggable: Flag to indicate if the marker can be moved
        :type draggable: boolean, default False
        :return: Handle used by the backend to univocally access the marker
        """
        print("MatplotlibBackend insertMarker not implemented")
        return label

    def insertXMarker(self, x, label,
                      color='k', selectable=False, draggable=False,
                      **kw):
        """
        :param x: Horizontal position of the marker in graph coordenates
        :type x: float
        :param label: Legend associated to the marker
        :type label: string
        :param color: Color to be used for instance 'blue', 'b', '#FF0000'
        :type color: string, default 'k' (black)
        :param selectable: Flag to indicate if the marker can be selected
        :type selectable: boolean, default False
        :param draggable: Flag to indicate if the marker can be moved
        :type draggable: boolean, default False
        :return: Handle used by the backend to univocally access the marker
        """
        #line = self.ax.axvline(x, picker=True)
        text = " " + label
        label = "__MARKER__" + label
        self.removeMarker(label, replot=False)
        if selectable or draggable:
            line = self.ax.axvline(x, label=label, color=color, picker=5)
        else:
            line = self.ax.axvline(x, label=label, color=color)
        if label is not None:
            ymin, ymax = self.getGraphYLimits()
            delta = abs(ymax - ymin)
            if ymin > ymax:
                ymax = ymin
            ymax -= 0.005 * delta
            line._infoText = self.ax.text(x, ymax, text,
                                          color=color,
                                          horizontalalignment='left',
                                          verticalalignment='top')
        #line.set_ydata(numpy.array([1.0, 10.], dtype=numpy.float32))
        line._plot_options = ["xmarker"]
        if selectable:
            line._plot_options.append('selectable')
        if draggable:
            line._plot_options.append('draggable')
        self.replot()
        return line
        
    def insertYMarker(self, y, label,
                      color='k', selectable=False, draggable=False,
                      **kw):
        """
        :param y: Vertical position of the marker in graph coordenates
        :type y: float
        :param label: Legend associated to the marker
        :type label: string
        :param color: Color to be used for instance 'blue', 'b', '#FF0000'
        :type color: string, default 'k' (black)
        :param selectable: Flag to indicate if the marker can be selected
        :type selectable: boolean, default False
        :param draggable: Flag to indicate if the marker can be moved
        :type draggable: boolean, default False
        :return: Handle used by the backend to univocally access the marker
        """
        label = "__MARKER__" + label 
        if selectable or draggable:
            line = self.ax.axhline(y, label=label, color=color, picker=5)
        else:
            line = self.ax.axhline(y, label=label, color=color)
        line._plot_options = ["ymarker"]
        if selectable:
            line._plot_options.append('selectable')
        if draggable:
            line._plot_options.append('draggable')
        return line

    def isXAxisAutoScale(self):
        if self._xAutoScale:
            return True
        else:
            return False

    def isYAxisAutoScale(self):
        if self._yAutoScale:
            return True
        else:
            return False

    def removeCurve(self, handle, replot=True):
        if hasattr(handle, "remove"):
            if handle in self.ax.lines:
                handle.remove()
        else:
            # we have received a legend!
            legend = handle
            handle = None
            for line2d in self.ax.lines:
                label = line2d.get_label()
                if label == legend:
                    handle = line2d
            if handle is not None:
                handle.remove()
                del handle
        if replot:
            self.replot()

    def removeImage(self, handle, replot=True):
        if hasattr(handle, "remove"):
            if (handle in self.ax.images) or (handle in self.ax.artists):
                handle.remove()
        else:
            # we have received a legend!
            legend = handle
            handle = None
            for item in self.ax.artists:
                label = item.get_label()
                if label == ("__IMAGE__" + legend):
                    handle = item
            if handle is None:
                for item in self.ax.images:
                    label = item.get_label()
                    if label == legend:
                        handle = item                
            if handle is not None:
                handle.remove()
                del handle
        if replot:
            self.replot()

    def removeMarker(self, handle, replot=True):
        if hasattr(handle, "remove"):
            self._removeInfoText(handle)
            handle.remove()
            del handle
        else:
            # we have received a legend!
            legend = handle
            handle = None
            for line2d in self.ax.lines:
                label = line2d.get_label()
                if label == ("__MARKER__"+legend):
                    handle = line2d
            if handle is not None:
                self._removeInfoText(handle)
                handle.remove()
                del handle
        if replot:
            self.replot()

    def _removeInfoText(self, handle):
        if hasattr(handle, "_infoText"):
            t = handle._infoText
            handle._infoText = None
            t.remove()
            del t

    def resetZoom(self):
        """
        It should autoscale any axis that is in autoscale mode
        """
        xmin, xmax = self.getGraphXLimits()
        ymin, ymax = self.getGraphYLimits()
        xAuto = self.isXAxisAutoScale() 
        yAuto = self.isYAxisAutoScale()
        if xAuto and yAuto:
            self.graph.resetZoom()
        elif yAuto:
            self.graph.resetZoom()
            self.setGraphXLimits(xmin, xmax)
        elif xAuto:
            self.graph.resetZoom()
            self.setGraphYLimits(ymin, ymax)
        else:
            if DEBUG:
                print("Nothing to autoscale")
        self.replot()
        return

    def replot(self):
        """
        Update plot
        """
        self.graph.draw()
        return

    def setActiveCurve(self, legend, replot=True):
        if hasattr(legend, "_plot_info"):
            # we have received an actual item
            handle = legend
        else:
            # we have received a legend
            handle = None
            for line2d in self.ax.lines:
                label = line2d.get_label()
                if label.startswith("__MARKER__"):
                    continue
                if label == legend:
                    handle = line2d
        if handle is not None:
            handle.set_color('k')
        else:
            raise KeyError("Curve %s not found" % legend)
        if self._oldActiveCurve in self.ax.lines:
            if self._oldActiveCurve._plot_info['label'] != legend:
                color = self._oldActiveCurve._plot_info['color']
                self._oldActiveCurve.set_color(color)
        elif self._oldActiveCurveLegend is not None:
            if self._oldActiveCurveLegend != handle._plot_info['label']:
                for line2d in self.ax.lines:
                    label = line2d.get_label()
                    if label == self._oldActiveCurveLegend:
                        color = line2d._plot_info['color']
                        line2d.set_color(color)
                        break
        self._oldActiveCurve = handle
        self._oldActiveCurveLegend = handle.get_label()
        if replot:
            self.replot()

    def setCallback(self, callbackFunction):
        self.graph.setCallback(callbackFunction)
        # Should I call the base to keep a copy?
        # It does not seem necessary since the graph will do it.

    def getGraphTitle(self):
        return self.ax.get_title()

    def getGraphXLabel(self):
        return self.ax.get_xlabel()

    def getGraphYLabel(self):
        return self.ax.get_ylabel()

    def setGraphTitle(self, title=""):
        self.ax.set_title(title)

    def setGraphXLabel(self, label="X"):
        self.ax.set_xlabel(label)
    
    def setGraphXLimits(self, xmin, xmax):
        self.ax.set_xlim(xmin, xmax)

    def setGraphYLabel(self, label="Y"):
        self.ax.set_ylabel(label)

    def setGraphYLimits(self, ymin, ymax):
        self.ax.set_ylim(ymin, ymax)

    def setXAxisAutoScale(self, flag=True):
        if flag:
            self._xAutoScale = True
        else:
            self._xAutoScale = False

    def setXAxisLogarithmic(self, flag):
        if flag:
            self._logX = True
            self.ax.set_xscale('log')
        else:
            self._logX = False
            self.ax.set_xscale('linear')

    def setYAxisAutoScale(self, flag=True):
        if flag:
            self._yAutoScale = True
        else:
            self._yAutoScale = False

    def setYAxisLogarithmic(self, flag):
        """
        :param flag: If True, the left axis will use a log scale
        :type flag: boolean
        """
        if flag:
            self._logY = True
            self.ax.set_yscale('log')
        else:
            self._logY = False
            self.ax.set_yscale('linear')

    def setZoomModeEnabled(self, flag=True):
        """
        Zoom and drawing are not compatible
        :param flag: If True, the user can zoom. 
        :type flag: boolean, default True
        """
        self._zoomEnabled = flag
        if flag:
            #cannot draw and zoom simultaneously
            self.setDrawModeEnabled(False)
            self._selecting = False

    def addImage(self, data, legend=None, info=None,
                    replace=True, replot=True,
                    xScale=None, yScale=None, z=0,
                    selectable=False, draggable=False, **kw):
        """
        :param data: (nrows, ncolumns) data or (nrows, ncolumns, RGBA) ubyte array 
        :type data: numpy.ndarray
        :param legend: The legend to be associated to the curve
        :type legend: string or None
        :param info: Dictionary of information associated to the image
        :type info: dict or None
        :param replace: Flag to indicate if already existing images are to be deleted
        :type replace: boolean default True
        :param replot: Flag to indicate plot is to be immediately updated
        :type replot: boolean default True
        :param xScale: Two floats defining the x scale
        :type xScale: list or numpy.ndarray
        :param yScale: Two floats defining the y scale
        :type yScale: list or numpy.ndarray
        :param z: level at which the image is to be located (to allow overlays).
        :type z: A number bigger than or equal to zero (default)  
        :param selectable: Flag to indicate if the image can be selected
        :type selectable: boolean, default False
        :param draggable: Flag to indicate if the image can be moved
        :type draggable: boolean, default False
        :returns: The legend/handle used by the backend to univocally access it.
        """
        if not hasattr(self, "__temperatureCmap"):
            # Temperature as defined in spslut
            from matplotlib.colors import LinearSegmentedColormap, LogNorm, Normalize
            cdict = {'red': ((0.0, 0.0, 0.0),
                             (0.5, 0.0, 0.0),
                             (0.75, 1.0, 1.0),
                             (1.0, 1.0, 1.0)),
                     'green': ((0.0, 0.0, 0.0),
                               (0.25, 1.0, 1.0),
                               (0.75, 1.0, 1.0),
                               (1.0, 0.0, 0.0)),
                     'blue': ((0.0, 1.0, 1.0),
                              (0.25, 1.0, 1.0),
                              (0.5, 0.0, 0.0),
                              (1.0, 0.0, 0.0))}
            #but limited to 256 colors for a faster display (of the colorbar)
            self.__temperatureCmap = LinearSegmentedColormap('temperature',
                                                             cdict, 256)

        # Non-uniform image
        #http://wiki.scipy.org/Cookbook/Histograms
        # Non-linear axes
        #http://stackoverflow.com/questions/11488800/non-linear-axes-for-imshow-in-matplotlib
        if replace:
            self.clearImages()
        else:
            # make sure we do not cummulate images with same name
            self.removeImage(legend, replot=False)

        cmap = self.__temperatureCmap
        if xScale is None:
            xScale = [0.0, 1.0]
        if yScale is None:
            yScale = [0.0, 1.0]
        h, w = data.shape[0:2]
        xmin = xScale[0]
        xmax = xmin + xScale[1] * w
        ymin = yScale[0]
        ymax = ymin + yScale[1] * h
        extent = (xmin, xmax, ymax, ymin)
        
        if selectable or draggable:
            picker = True
        else:
            picker = None
            
        if 0:
            # this supports non regularly spaced coordenates!!!!
            x = xmin + numpy.arange(w) * xScale[1] 
            y = ymin + numpy.arange(h) * yScale[1] 
            image = NonUniformImage(self.ax,
                                    interpolation='nearest',
                                    #aspect='auto',
                                    extent=extent,
                                    picker=picker,
                                    cmap=cmap)
                                                     
                                               

            image.set_data(x, y, data)
            xmin, xmax = self.getGraphXLimits()
            ymin, ymax = self.getGraphYLimits()
            self.ax.images.append(image)
            self.ax.set_xlim(xmin, xmax)
            self.ax.set_ylim(ymin, ymax)
        elif 1:
            #the normalization can be a source of time waste
            image = AxesImage(self.ax,
                              label="__IMAGE__"+legend,
                              interpolation='nearest',
                              #origin=
                              cmap=cmap,
                              extent=extent,
                              picker=picker,
                              zorder=z,
                              norm=Normalize(data.min(), data.max()))
            image.set_data(data)
            self.ax.add_artist(image)
            #self.ax.draw_artist(image)
        image._plot_info = {'label':legend,
                            'type':'image',
                            'xScale':xScale,
                            'yScale':yScale,
                            'z':z}
        image._plot_options = []
        if draggable:
            image._plot_options.append('draggable')
        if selectable:
            image._plot_options.append('selectable')
        return image

    def invertYAxis(self, flag=True):
        if flag:
            if not self.ax.yaxis_inverted():
                self.ax.invert_yaxis()
        else:
            if self.ax.yaxis_inverted():
                self.ax.invert_yaxis()

    def isYAxisInverted(self):
        return self.ax.yaxis_inverted()

    def showGrid(self, flag=True):
        if flag == 1:
            self.ax.xaxis.set_tick_params(which='major')
            self.ax.yaxis.set_tick_params(which='major')
            self.ax.grid(which='major')
        elif flag == 2:
            self.ax.xaxis.set_tick_params(which='both')
            self.ax.yaxis.set_tick_params(which='both')
            self.ax.grid(which='both')
        elif flag:
            self.ax.xaxis.set_tick_params(which='major')
            self.ax.yaxis.set_tick_params(which='major')
            self.ax.grid(True)
        else:
            self.ax.grid(False)
        self.replot()

def main(parent=None):
    from .. import Plot
    x = numpy.arange(100.)
    y = x * x
    plot = Plot.Plot(parent, backend=MatplotlibBackend)
    plot.addCurve(x, y, "dummy")
    plot.addCurve(x + 100, -x * x, "To set Active")
    print("Active curve = ", plot.getActiveCurve())
    print("X Limits) = ", plot.getGraphXLimits())
    print("Y Limits = ", plot.getGraphYLimits())
    print("All curves = ", plot.getAllCurves())
    #plot.removeCurve("dummy")
    plot.setActiveCurve("To set Active")
    print("All curves = ", plot.getAllCurves())
    #plot.resetZoom()
    return plot

if __name__ == "__main__":
    if "tkinter" in sys.modules or "Tkinter" in sys.modules:
        root = Tk.Tk()
        parent=root
        #w = MatplotlibGraph(root)
        #Tk.mainloop()
        #sys.exit(0)
        w = main(parent)
        widget = w._plot.graph
    else:        
        app = QtGui.QApplication([])
        parent=None
        w = main(parent)
        widget = w.getWidgetHandle()
    #w.invertYAxis(True)
    w.replot()
    #w.invertYAxis(True)
    data = numpy.arange(1000.*1000)
    data.shape = 10000,100
    #plot.replot()
    #w.invertYAxis(True)
    #w.replot()
    #w.widget.show()
    w.addImage(data, legend="image 0", xScale=(25, 1.0) , yScale=(-1000, 1.0),
                  selectable=True)
    w.removeImage("image 0")
    #w.invertYAxis(True)
    #w.replot()
    w.addImage(data, legend="image 1", xScale=(25, 1.0) , yScale=(-1000, 1.0),
                  replot=False, selectable=True)
    #w.invertYAxis(True)
    widget.ax.axis('auto') # appropriate for curves, no aspect ratio
    #w.widget.ax.axis('equal') # candidate for keepting aspect ratio
    #w.widget.ax.axis('scaled') # candidate for keepting aspect ratio
    print("aspect = %s" % widget.ax.get_aspect())
    w.insertXMarker(50., label="Label", color='pink', draggable=True)
    #print(w.widget.ax.get_images())
    #print(w.widget.ax.get_lines())
    if "tkinter" in sys.modules or "Tkinter" in sys.modules:
        tkWidget = w.getWidgetHandle()
        tkWidget.pack(side=Tk.TOP, fill=Tk.BOTH, expand=1)
        Tk.mainloop()
    else:        
        widget.show()
        app.exec_()