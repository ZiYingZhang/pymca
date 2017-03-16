#/*##########################################################################
#
# The PyMca X-Ray Fluorescence Toolkit
#
# Copyright (c) 2004-2017 European Synchrotron Radiation Facility
#
# This file is part of the PyMca X-ray Fluorescence Toolkit developed at
# the ESRF by the Software group.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
#############################################################################*/
__author__ = "V.A. Sole - ESRF Data Analysis"
__contact__ = "sole@esrf.fr"
__license__ = "MIT"
__copyright__ = "European Synchrotron Radiation Facility, Grenoble, France"
import os
import sys
import numpy
from PyMca5.PyMcaIO import JcampReader
from PyMca5.PyMcaIO import SpecFileAbstractClass
if sys.version < "3":
    import StringIO.StringIO as StringIO
else:
    from io import StringIO

class JcampFileParser(SpecFileAbstractClass.SpecFileAbstractClass):
    def __init__(self, filename, single=False):
        # get the number of entries in the file
        self.__lastEntryData = -1
        self._scanLimits = []
        f = open(filename, "r")
        entryStarted = False
        current = f.tell()
        line = f.readline()
        nLines = 0
        while len(line):
            if entryStarted:
                if line.startswith("##END="):
                    lineEnd = nLines
                    self._scanLimits.append((start, current, lineStart, lineEnd))
                    entryStarted = False
                    if single:
                        break
            elif line.startswith("##TITLE"):
                start = current
                lineStart = nLines
                entryStarted = True
            nLines += 1
            current = f.tell()
            line = f.readline()
        f.close()
        self._filename = os.path.abspath(filename)
        self._parseEntryData(0)

    def _parseEntryData(self, idx):
        if idx == self.__lastEntryData:
            # nothing to be done
            return
        if (idx < 0) or (idx >= len(self._scanLimits)):
            raise IndexError("Only %d entries in file. Requested %d" % (len(self._scanLimits), idx))
        #get the relevant file section
        f = open(self._filename, "r")
        start, end = self._scanLimits[idx][0:2]
        f.seek(start)
        scanBuffer = StringIO(f.read(1 + end - start))
        f.close()
        instance = JcampReader.JcampReader(scanBuffer)
        info = instance.info
        jcampDict = info
        x, y = instance.data
        title = jcampDict.get('TITLE', "Unknown scan")
        xLabel = jcampDict.get('XUNITS', 'channel')
        yLabel = jcampDict.get('YUNITS', 'counts')
        try:
            fileheader = instance._header
        except:
            print("JCampFileParser cannot access '_header' attribute")
            fileheader=None
        data = numpy.zeros((x.size, 2), numpy.float32)
        data[:, 0] = x
        data[:, 1] = y
        self.scandata = []
        scanheader = ["#S %d %s" % (2*idx + 1, title)]
        scanheader.append("#N 2")
        scanheader.append("#L %s  %s" % (xLabel, yLabel))
        scanData = JCAMPFileScan(data,
                                 scantype="SCAN",
                                 scanheader=scanheader,
                                 labels=[xLabel, yLabel],
                                 fileheader=fileheader)
        self.scandata.append(scanData)
        scanheader = ["#S %d %s" % (2*idx + 2, title)]
        if jcampDict['XYDATA'].upper() ==  '(X++(Y..Y))':
            # we can deal with the X axis via its calibration
            scanheader.append("#@CHANN %d  %d  %d  1" % (len(x), 0, len(x) - 1))
            scanheader.append("#@CALIB %f %f 0" % (x[0], x[1] - x[0]))
            scantype = "MCA"
        scanData = JCAMPFileScan(data, scantype="MCA",
                                                      scanheader=scanheader,
                                                      #labels=[xLabel, yLabel],
                                                      fileheader=fileheader)
        self.scandata.append(scanData)
        self.__lastEntryData = idx

    def __getitem__(self, item):
        if item < 0:
            item = self.scanno() - item
        idx = item // 2
        self._parseEntryData(idx)
        return self.scandata[item % 2]

    def list(self):
        return '1:%d' % self.scanno()

    def scanno(self):
        return len(self.scandata) * len(self._scanLimits)

class JCAMPFileScan(SpecFileAbstractClass.SpecFileAbstractScan):
    def __init__(self, data, scantype="SCAN",
                 scanheader=None, labels=None, fileheader=None):
        SpecFileAbstractClass.SpecFileAbstractScan.__init__(self, data,
                            scantype=scantype, scanheader=scanheader,
                            labels=labels)
        self._data = data
        self._fileHeader = fileheader

    def fileheader(self, key=''):
        return self._fileHeader

    def nbmca(self):
        if self.scantype == 'SCAN':
            return 0
        else:
            return 1

    def mca(self, number):
        if number not in [1]:
            raise ValueError("Specfile mca numberig starts at 1")
        return self._data[:, number]

def isJcampFile(filename):
    return JcampReader.isJcampFile(filename)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python JCAMPFileParser.py filename")
        sys.exit(0)
    print(" isJCAMPFile = ", isJcampFile(sys.argv[1]))
    sf = JcampFileParser(sys.argv[1])
    print("nscans = ", sf.scanno())
    print("list = ", sf.list())
    print("select = ", sf.select(sf.list()[0]))
