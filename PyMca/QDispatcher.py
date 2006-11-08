from QSourceSelector import qt
QTVERSION = qt.qVersion()
import QSourceSelector
import QDataSource
import os
#import weakref

DEBUG = 0

class QDispatcher(qt.QWidget):
    def __init__(self, parent=None):
        qt.QWidget.__init__(self, parent)
        self.mainLayout = qt.QVBoxLayout(self)
        self.mainLayout.setMargin(0)
        self.mainLayout.setSpacing(0)
        self.sourceList = []
        self.sourceSelector = QSourceSelector.QSourceSelector(self)
        self.selectorWidget = {}
        self.tabWidget = qt.QTabWidget(self)
        
        #for the time being just files
        for src_widget in QDataSource.source_widgets.keys():
            self.selectorWidget[src_widget] = QDataSource.source_widgets[src_widget]()
            self.tabWidget.addTab(self.selectorWidget[src_widget], src_widget)
            
            if QTVERSION < '4.0.0':
                self.connect(self.selectorWidget[src_widget],
                             qt.PYSIGNAL("addSelection"),
                             self._addSelectionSlot)
                self.connect(self.selectorWidget[src_widget],
                             qt.PYSIGNAL("removeSelection"),
                             self._removeSelectionSlot)
                self.connect(self.selectorWidget[src_widget],
                             qt.PYSIGNAL("replaceSelection"),
                             self._replaceSelectionSlot)             
            else:
                self.connect(self.selectorWidget[src_widget],
                             qt.SIGNAL("addSelection"),
                             self._addSelectionSlot)                                                 
                self.connect(self.selectorWidget[src_widget],
                             qt.SIGNAL("removeSelection"),
                             self._removeSelectionSlot)                                                 
                self.connect(self.selectorWidget[src_widget],
                             qt.SIGNAL("replaceSelection"),
                             self._replaceSelectionSlot)                                                 
        
        self.mainLayout.addWidget(self.sourceSelector)
        self.mainLayout.addWidget(self.tabWidget)
        if QTVERSION < '4.0.0':
            self.connect(self.sourceSelector, 
                    qt.PYSIGNAL("SourceSelectorSignal"), 
                    self._sourceSelectorSlot)
        else:
            self.connect(self.sourceSelector, 
                    qt.SIGNAL("SourceSelectorSignal"), 
                    self._sourceSelectorSlot)

    def _addSelectionSlot(self, sel_list, event=None):
        if DEBUG:
            print "_addSelectionSlot"
            print "sel_list = ",sel_list

        if event is None:event = "addSelection"
        for sel in sel_list:
            #find the source
            sourcelist = sel['SourceName']
            for source in self.sourceList:
                if source.sourceName == sourcelist:
                    ddict = {}
                    ddict.update(sel)
                    ddict["event"]  = event
                    #we have found the source  
                    #this recovers the data and the info
                    if True:
                        #this creates a data object that is passed to everybody so
                        #there is only one read out.
                        #I should create a weakref to it in order to be informed
                        #about its deletion.
                        dataObject = source.getDataObject(sel['Key'],
                                                      selection=sel['selection'])
                        ddict['dataobject'] = dataObject
                        if QTVERSION < '4.0.0':
                            self.emit(qt.PYSIGNAL(event), (ddict,))
                        else:
                            self.emit(qt.SIGNAL(event), ddict)
                    else:
                        #this creates a weak reference to the source object
                        #the clients will be able to retrieve the data
                        #the problem is that 10 clients will requiere
                        #10 read outs
                        ddict["sourcereference"] = weakref.ref(source)
                        if QTVERSION < '4.0.0':
                            self.emit(qt.PYSIGNAL(event), (ddict,))
                        else:
                            self.emit(qt.SIGNAL(event), ddict)

    def _removeSelectionSlot(self, sel_list):
        if DEBUG:
            print "_removeSelectionSlot"
            print "sel_list = ",sel_list
        for sel in sel_list:
            ddict = {}
            ddict.update(sel)
            ddict["event"] = "removeSelection"
            if QTVERSION < '4.0.0':
                self.emit(qt.PYSIGNAL("removeSelection"), (ddict,))
            else:
                self.emit(qt.SIGNAL("removeSelection"), ddict)

    def _replaceSelectionSlot(self, sel_list):
        if DEBUG:
            print "_replaceSelectionSlot"
            print "sel_list = ",sel_list

        if len(sel_list) == 1:
            self._addSelectionSlot([sel_list[0]], event = "replaceSelection")
        elif len(sel_list) > 1:
            self._addSelectionSlot([sel_list[0]], event = "replaceSelection")
            self._addSelectionSlot(sel_list[1:], event = "addSelection")
            

    def _sourceSelectorSlot(self, ddict):
        if DEBUG:
            print "_sourceSelectorSlot(self, ddict)"
            print "ddict = ",ddict
        if ddict["event"] == "NewSourceSelected":
            source = QDataSource.QDataSource(ddict["sourcelist"])
            self.sourceList.append(source)
            sourceType = source.sourceType
            self.selectorWidget[sourceType].setDataSource(source)
            if QTVERSION < '4.0.0':
                index = self.tabWidget.indexOf(self.selectorWidget[sourceType])
                self.tabWidget.setCurrentPage(index)  
            else:
                self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
        elif ddict["event"] == "SourceSelected":
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                if DEBUG:
                    print "WARNING: source not found"
                return
            sourceType = source.sourceType
            self.selectorWidget[sourceType].setDataSource(source)
            if QTVERSION < '4.0.0':
                index = self.tabWidget.indexOf(self.selectorWidget[sourceType])
                self.tabWidget.setCurrentPage(index)  
            else:
                self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
        elif ddict["event"] == "SourceClosed":
            found = 0
            for source in self.sourceList:
                if source.sourceName == ddict["sourcelist"]:
                    found = 1
                    break
            if not found:
                if DEBUG:
                    print "WARNING: source not found"
                return
            sourceType = source.sourceType
            del self.sourceList[self.sourceList.index(source)]
            for source in self.sourceList:
                if sourceType == source.sourceType:
                    self.selectorWidget[sourceType].setDataSource(source)
                    if QTVERSION < '4.0.0':
                        index = self.tabWidget.indexOf(self.selectorWidget[sourceType])
                        self.tabWidget.setCurrentPage(index)  
                    else:
                        self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])
                    return
            #there is no other selection of that type
            if len(self.sourceList):
                source = self.sourceList[0]
                sourceType = source.sourceType
                self.selectorWidget[sourceType].setDataSource(source)
            else:
                self.selectorWidget[sourceType].setDataSource(None)
            if QTVERSION < '4.0.0':
                index = self.tabWidget.indexOf(self.selectorWidget[sourceType])
                self.tabWidget.setCurrentPage(index)  
            else:
                self.tabWidget.setCurrentWidget(self.selectorWidget[sourceType])


def test():
    app = qt.QApplication([])
    w = QDispatcher()
    w.show()
    qt.QObject.connect(app,qt.SIGNAL("lastWindowClosed()"),
                       app, qt.SLOT("quit()"))
    if QTVERSION < '4.0.0':
        app.exec_loop()
    else:
        app.exec_()
        
if __name__ == "__main__":
    test()
