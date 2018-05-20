# title             : imagingcontrol.py
# description       : Standard MITOMI Imaging Functions and Classes
# authors           : Daniel Mokhtari, Scott Longwell
# credits           : 
# date              : 20180520
# version update    : 20180520
# version           : 0.1.0
# usage             : With permission from DM
# python_version    : 2.7


import os
import copy
import time
import datetime
import pprint as pp
import pandas as pd
from PIL import Image
from Queue import Queue
import matplotlib.pyplot as pl

from acqpack import gui
from runpack.io import HardwareInterface as hi
from runpack.io import ExperimentalHarness as eh



hardwareQueue = Queue()
hardwareBlockingFlag = True
hardwareState = 0 #State: 0 = Resting, 1 = One Queue Complete, 2 = Both Complete

def snap(show = True, vmin = 0, vmax = 65535, figsize = (4, 4)):
    """
    Snaps an image and returns the resulting image array.

    Arguments:
        (bool) show: flag to show image
        (int) vmin: threshold minimum
        (int) vmax: threshold max
        (tuple) figsize: matplotlib image figure size

    Returns:
        None
    """

    hi.core.snapImage()
    imgArr = hi.core.getImage()
    if show:
        pl.figure(figsize = figsize)
        pl.imshow(imgArr, cmap='gray', vmin = vmin, vmax = vmax)
        pl.title('Snapped Imaged, {}'.format(time.strftime("%Y%m%d-%H%M%S", time.localtime())))
        pl.axis('off')
        pl.show()
    return imgArr


def live():
    """
    Wrapper for acqpack.gui.video() video acquisition function.
    # TODO: Enable live video saving to disk

    Arguments:
        None

    Returns:
        None
    """

    gui.video(hi.core, loop_pause=0.05)


def startHardwareQueue():
    """
    Start the hardware job queue

    Arguments:
        None

    Returns:
        None
    """

    eh.acquilogger.info('HardwareQueue Started')
    while hardwareState < 2:
        args, kwargs = hardwareQueue.get(block = hardwareBlockingFlag)
        scan(*args, **kwargs)


def scan(data_dir, channelsExposures, dname, note, position_list, wrappingFolder = False, writeRecord = False):
    """
    Raster image acquisition. Acquires images in a raster patern and saves the results.
    
    Arguements:
        (str) data_dir: root directory of image acquisitions
        (dict) channelsExposure: Dictionary of channels mapped to exposures (e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
        (str) dname: device name ('d1' | 'd2' |'d3')
        (str) note: Scan note
        (pandas.DataFrame) position_list: stage xy position list
        (bool) wrappingFolder: flag to wrap acquistions inside another directory of name notes
        (bool) writeRecord:
        
    Returns:
        None
    """

    def makeDir(path):
        if not os.isdir(outDir):
            os.makedirs(outDir)
    
    messageItems = str(dname), str(channelsExposures), str(note.replace(' ', '_'))
    startMessage = 'Started Scan of {}, channelsExposures = {}, note = {}'.format(8messageItems)
    eh.acquilogger.info(startMessage)
    
    if wrappingFolder:
        timeString = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        scanfolder = (os.path.join(data_dir, '{}-{}_{}'.format(timeString, dname, note.replace(' ', '_'))))
        data_dir = scanfolder
        makeDir(scanfolder)

    scanDirs = {}

    startTime = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    for channel in channelsExposures.keys():
        scan_dir = '{}_{}_{}'.format(startTime, note.replace(' ', '_'), channel)
        scanDirs[channel] = scan_dir
        outDir = os.path.join(data_dir, channel, scan_dir)
        makeDir(outDir)
    
    if hi.temp:
	   temp = hi.temp.getProbeTemp() # Get temperature for metadata
	   hum = hi.temp.getHumidity() # Get humidity for metadata
    
    scanRecord = {startTime: {}}
    for i in xrange(len(position_list)):
        si = str(i)
        x,y = position_list[['x','y']].iloc[i]
        hi.core.setXYPosition(x,y)
        hi.core.waitForDevice(hi.core.getXYStageDevice())
        for channel in channelsExposures.keys():
            hi.core.setConfig('Channel', channel)
            time.sleep(0.3)
            timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
            for exposure in channelsExposures[channel]:
                hi.core.setProperty(hi.core.getCameraDevice(), 'Exposure', exposure)
                hi.core.waitForDevice(hi.core.getCameraDevice())
                hi.core.snapImage()
                img = hi.core.getImage()
                image = Image.fromarray(img)
                timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                positionname = position_list['name'].iloc[i]
                
                outPath = os.path.join(data_dir, channel, scanDirs[channel])
                frameName = '{}/{}_{}.tif'.format(outPath, positionname, exposure)
                imagePath = os.path.join(outPath, frameName)

                summary = 'Device: {}, Note: {}'.format('Setup 3', note)
                frameInfo = '{{Channel: {}, Index:{}, Pos:({},{})}}'.format(channel, i, x, y)
                frameTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                recordLabels = ['RasterStartTime', 'ScanParams', 'Channel', 'Exposure', 'ImagePath', 'RasterIndex',
                                    'X', 'Y', 'dname', 'FrameTime', 'Temperature', 'Humidity', 'Note','Setup']
                recordFeatures = [startTime, channelsExposures, channel, exposure, imagePath,
                                    i, x, y, dname, frameTime, temp, hum, note, hi.setup]
                scanRecord[startTime][timestamp] = dict(zip(recordLabels, recordFeatures))
                
                exifIDs = [37888, 37889, 33434, 37510, 270, 306]
                exifValues = [temp, hum, exposure/1000.0, summary, frameInfo, frameTime]
                tags = dict(zip(exifIDs, exifValues))

                image.save(imagePath, tiffinfo = tags)

    messageItems = str(dname), str(channelsExposures), str(note.replace(" ", "_"))
    endMessage = 'Completed Scan of {}, channelsExposures = {}, note = {}'.format(*messageItems)
    eh.acquilogger.info(endMessage)
    bringHome(position_list)

    scanRecordDF = pd.from_dict(scanRecord, orient = 'index')
    return scanRecordDF


def bringHome(position_list):
    """
    Brings the stage to its origin, the "home" position

    Arguments:
        (pd.DataFrame) position_list: xy-stage position list

    Returns:
        None
    """

    x,y = position_list[['x','y']].iloc[0]
    hi.core.setXYPosition(x,y)
    hi.core.waitForDevice(hi.core.getXYStageDevice())


class KineticAcquisition():
    def __init__(self, deviceName, channelsExposures, delayTimes, description):
        self.device = deviceName #either d1, d2, or d1d2
        self.channelsExposures = channelsExposures # dict
        self.delayTimes = delayTimes #as a tuple
        self.absTimes = self.getTimeSpacings()
        self.note = description.replace(" ", "_")

    def getTimeSpacings(self):
        """
        Given a list of delay times (in seconds), calculates the summed time elapsed from a reference time.
        
        Arguments:
            None
            
        Returns:
            (list) List of summed delays from a common reference time (0)
        
        """
        referencedDelayTimes = [0]+self.delayTimes
        return np.cumsum(referencedDelayTimes).tolist()


    def toString(self):
        """
        Prints and returns a string representation of the kinetic acquisition parameters.
    
        Arguments:
            None

        Returns:
            (str) KineticAcquisition parameters 
        """
        
        paramVals = [self.device, self.channelsExposures, str(self.absTimes), str(self.delayTimes), self.note]
        params = 'Device Name: {}, Channels, Exposures: {}, \
                    Referenced Times (s): {}, Delay Times (s): {}, Note: {}'.format(*paramVals)
        return '>> Kinetic Acquisition Parameters: {}'.format(params)


    def startAssay(self, data_dir, pos_list, scanQueueFlag = False):
        """
        Brings the stage home, schedules the scans, then starts the image acquisitions
        # TODO: take returned scanrecord from scan function, generate pandas DF, 

        Arguments:
            (str) data_dir: directory to write image folder
            (pd.DataFrame) post_list: position list
            (bool) scanQueueFlag: flag to add scan to the common scan queue
        
        Returns:
            None
        """
        
        kineticSubfolder = '{}_{}'.format(time.strftime("%Y%m%d_%H%M%S", time.localtime()), self.note.replace(" ", "_"))
        kineticDirectory = os.path.join(data_dir, kineticSubfolder)
        os.makedirs(kineticDirectory)
            
        eh.acquilogger.info(self.toString())
        eh.acquilogger.info('Kinetic acquisition started: ' + str(self.note.replace(" ", "_")))
        
        delaysToQueue = [0] + self.delayTimes
        scanQueue = Queue()

        list(map(lambda k: scanQueue.put(k), delaysToQueue))
        
        lastScanTime = time.time()
        while not scanQueue.empty():
            nextScanDelay = scanQueue.get()
            deltaTime = (nextScanDelay + lastScanTime) - time.time()
            if deltaTime <= 0:
                lastScanTime = time.time()
                if scanQueueFlag == True:
                    args = [kineticDirectory, self.channelsExposures, self.device, self.note.replace(" ", "_"), pos_list]
                    kwargs = {}
                    hardwareQueue.put((args, kwargs))
                else:
                    scan(kineticDirectory, self.channelsExposures, self.device, self.note.replace(" ", "_"), pos_list)
            else:
                time.sleep(deltaTime)
                lastScanTime = time.time()
                if scanQueueFlag == True:
                    args = [kineticDirectory, self.channelsExposures, self.device, self.note.replace(" ", "_"), pos_list]
                    kwargs = {}
                    hardwareQueue.put((args, kwargs))
                else:
                    scan(kineticDirectory, self.channelsExposures, self.device, self.note.replace(" ", "_"), pos_list)
        eh.acquilogger.info('Kinetic Read Complete')
