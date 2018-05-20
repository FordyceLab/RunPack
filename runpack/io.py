# title             : io.py
# description       : Top-level classes for Jupyter-based experimental MicroManager imaging & WAGO valve control 
# authors           : Daniel Mokhtari
# credits           : 
# date              : 20180520
# version update    : 20180520
# version           : 0.1.0
# usage             : With permission from DM
# python_version    : 2.7


import os
import sys
import time
import json
import logging
import warnings
import pandas as pd

from acqpack import Manifold
from acqpack import utils as ut
from acqpack import gui

import visa



class ExperimentalHarness:
    posLists = {}
    valvelogger = None
    scriptlogger = None
    acquilogger = None
    userlogger = None
    rootPath = ''
    experimentalDescription = ''
    assayTimes = {}
    imagingRecord = pd.DataFrame()

    def __init__(self, root, description, loggername = 'experiment'):
        """
        Experimental Harness constructor
        TODO: refactor as parent class

        Arguments:
            (str) root: experimental root path. Location where images will be written.
            (str) description: brterse exeperimental description
            (str) loggername: custom name for the experimental logger. Will be propogated to the experimental log.

        Returns:
            None
        """

        ExperimentalHarness.rootPath = self.root = root
        ExperimentalHarness.experimentalDescription = self.description = description
        time.sleep(0.2)
        
        self.initializeLogger(loggername)


    def addPositionList(self, dname, path):
        """
        Adds a MicroManager position list to the experimental harness

        Arguments:
            (str) dname: device name ('d1' | 'd2' | 'd3')
            (str) path: path of the MicroManager position list (.pos file)

        Returns:
            None
        """

        posList = ut.load_mm_positionlist(path)
        ExperimentalHarness.posLists[dname] = posList
        logging.info('Added Posiiton List for Device {}'.format(dname))


    def removePositionList(self, dname):
        """
        Removes a MicroManager position list from the experimental harness

        Arguments:
            (str) dname: device name for harness to remove ('d1' | 'd2' | 'd3')

        Returns:
            None
        """

        ExperimentalHarness.posLists.pop(dname)
        logging.info('Remove Posiiton List for Device {}'.format(dname))


    def note(self, note, importance = 0):
        """
        Writes a custom note to the user logger of the given importance

        Arguments:
            (str) note: 
            (int) importance: logging level. 0 = 'info', 1 = 'warning', 2 = 'error', 3 = 'critical' (0 | 1 | 2 | 3)

        Returns:
            None
        """

        if importance == 1: 
            ExperimentalHarness.userlogger.warning(note)
        elif importance == 2:
            ExperimentalHarness.userlogger.error(note)
        elif importance == 3:
            ExperimentalHarness.userlogger.critical(note)
        else:
            ExperimentalHarness.userlogger.info(note)


    def initializeLogger(self, name):
        """
        Initializes the loggers, including a valve logger, script logger, acquisition logger, and user logger.

        Arguments:
            (str) name: log file name

        Return:
            None
        """

        logging.basicConfig(level=logging.INFO,
                    format = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                    datefmt = '%y-%m-%d %H:%M:%S',
                    filename = os.path.join(self.root, '{}.log'.format(name)),
                    filemode = 'a+')

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s', '%y-%m-%d %H:%M:%S')
        console.setFormatter(formatter)

        # add the handler to the root logger
        logging.getLogger('').addHandler(console)
        logging.captureWarnings(True)

        ExperimentalHarness.valvelogger = logging.getLogger('Valves')
        ExperimentalHarness.scriptlogger = logging.getLogger('Script')
        ExperimentalHarness.acquilogger = logging.getLogger('Acquisition')
        ExperimentalHarness.userlogger = logging.getLogger('User')


    def addAssayTimings(self, assayTimesDict):
        """
        Adds a dictionary of assay kinetic delay timings to the experimental harness.

        Arguments:
            (dict) assayTimesDict: dicitonary of assay timings of the form {'name': [dt0, dt1, ..., dtf], ...}

        Returns:
            None
        """

        for key in assayTimesDict.keys():
            if key in ExperimentalHarness.assayTimes.keys():
                logging.warning('Harness already contained the assay time key: {}'.format(key))
        ExperimentalHarness.assayTimes.update(assayTimesDict)
        logging.info('Updated harness with assay times: {}'.format(assayTimesDict))


    def removeAssayTimings(self, assayTimesKeys):
        """
        Removes a list of assay timings from the experimental harness

        Arguments:
            (list) assayTimesKeys: list of assay timings keys to remove from the experimetnal harness

        Returns:
            None
        """

        try:
            list(map(ExperimentalHarness.assayTimes.pop, assayTimesKeys))
            logging.info('Removed assay times from harness: {}'.format(assayTimesKeys))
        except KeyError as e:
            offendingKey = e.args[0]
            errornote = 'Time list not present: {}'.format(offendingKey)
            raise warnings.warn(note)


    def toString(self):
        """
        A string description of the ExperimentalHarness

        Arguments:
            None

        Returns:
            (str) Description of the experimental harness description
        """
        stringVals = {'rp': ExperimentalHarness.rootPath, 'ed': ExperimentalHarness.experimentalDescription, 
                        'pl': ExperimentalHarness.posLists.keys(), 'at': ExperimentalHarness.assayTimes}
        return 'Experimental Harness Current State: \n\
                Root Path: {rp}\n\
                Experimental Description: {ed}\n\
                Position Lists: {pl}\n\
                Assay Timings: {at}'.format(stringVals)
    

    def __del__(self):
        x = logging._handlers.copy()
        for i in x:
            logging.removeHandler(i)
            i.flush()
            i.close()



class HardwareInterface:

    config = None
    mmcfg = None
    mm_version = None
    valvemapPath = None
    manifoldAddress = None
    manifoldOffset = None
    channels = None
    filterBlockName = None
    valves = None
    coreTimeout = 10000 #ms
    core = None #MM core
    temp = None #temperature & humidity probe
    m = None #manifold
    flowValves = None
    controlValves = None
    valveReferenceIndex = 'chip'


    def __init__(self, loadAllHardware = True, configLoc = ''):
        """
        Hardware interface for control of camera/microscope, valving, and sensors
        TODO: refactor as parent class

        Arguments:
            (bool) loadAllHardware: flag to load all hardware available
            (str) configLog: path of JSON configuration file

        Returns:
            None
        """
        self.loadConfig(configLoc)
        if loadAllHardware:
            self.initializeHardware()
        else: logging.info('HardwareInterface Created. Add Hardware to Interface.')


    def initializeHardware(self, subset = 'all'):
        """
        Initializes control of the hardware by adding it to the hardware interface. 
        Possible subsets are 'all', 'manifold', 'microscope', and 'temperature'.

        Arguments:
            (str) subset: subset of hardware to initialize ('all' | 'manifold' | 'microscope' | 'temperature'.)

        Returns:
            None
        """

        if subset == 'all':
            self.intializeManifoldControl()
            self.initializeMicroManager()
            self.initializeTempProbe()
        elif subset == 'manifold':
            self.intializeManifoldControl()
        elif subset == 'microscope':
            self.initializeMicroManager()
        elif subset == 'temperature':
            self.initializeTempProbe()
        elif subset is None:
            warnings.warn('No hardware was selected to initialize')
        else:
            raise ValueError('The requested hardware initialization failed. Specify a valid subset.')


    def intializeManifoldControl(self):
        """
        Initialize connection to WAGO controller and manifold.

        Arguments:
            None

        Returns:
            None
        """
        hi = HardwareInterface
        HardwareInterface.m = Manifold(hi.manifoldAddress, str(hi.valvemapPath), hi.manifoldOffset)
        HardwareInterface.m.valvemap.fillna('', inplace=True)
        self.assignValvetypes()
        logging.info('Manifold Control Established')


    def assignValvetypes(self):
        """
        Assigns valves in the valvemap to type 'flow' or 'control' and adds to HardwareInterface.
        
        Arguments:
            None

        Returns:
            None
        """

        valves = HardwareInterface.m.valvemap.copy().dropna()
        device = valves['device'].drop_duplicates().tolist()[0]
        valves['chipshort'] = valves.chip.apply(lambda v: v[:-1]) # Shorthand valve notation
        HardwareInterface.flowValves = valves.loc[valves.layer == 'flow'].chipshort.drop_duplicates().tolist()
        HardwareInterface.controlValves = valves.loc[valves.layer == 'control'].chipshort.drop_duplicates().tolist()


    def initializeMicroManager(self):
        """
        Instantiates a MMCore instance, loads the default hardware configuration, and sets the default timeout.

        Arguments:
            None

        Returns:
            None
        """

        logging.info('Trying to Establish Microscope Control...')
        sys.path.insert(0, HardwareInterface.mm_version) # make it so python can find MMCorePy
        import MMCorePy
        HardwareInterface.core = MMCorePy.CMMCore()
        HardwareInterface.core.loadSystemConfiguration(str(HardwareInterface.mmcfg))
        HardwareInterface.core.setTimeoutMs(HardwareInterface.coreTimeout)
        logging.info('Microscope Control Established')

        defaults = self.config['mm']['defaults']
        self.setScopeConfig(exposure = defaults['exposure'], binning = defaults['binning'])
    

    def initializeTempProbe(self):
        """
        Initializes connection to the temperature probe

        Arguments:
            None

        Returns:
            None
        """

        th = HardwareInterface.config['temp_hum']
        HardwareInterface.temp = TemperatureProbe(th['vid'], th['pid'])
        HardwareInterface.temp.load()
        logging.info('Temperature and Humidity Probe Connected')
    

    def setScopeConfig(self, exposure = None, binning = None, channel = None):
        """
        Sets the camera configuration to the specified exposure, binning, and channel

        Arguments:
            (int) exposure: camera exposure time (ms)
            (str) binning: camera binning ('1x1' | '2x2' | '3x3' | '4x4 | '6x6')
            (str) channel: camera channel, as per Channel preset group (eMITOMI defaults: 1pbp, 2bf, 3dapi, 4egfp, 5cy5)

        Returns:
            None
        """

        if exposure:
            HardwareInterface.core.setProperty(HardwareInterface.core.getCameraDevice(), "Exposure", exposure)
            logging.info('Camera Exposure Set: {}ms'.format(exposure))
        if binning:
            HardwareInterface.core.setProperty(HardwareInterface.core.getCameraDevice(), "Binning", str(binning))
            logging.info('Camera Binning Set: {}'.format(binning))
        if channel:
            HardwareInterface.core.setConfig('Channel', str(channel))
            logging.info('Camera Channel Set: {}'.format(channel))
        HardwareInterface.core.waitForDevice(HardwareInterface.filterBlockName)


    def unloadHardware(self):
        """
        Unloads all hardware from the HardwareInterface

        Arguments:
            None

        Returns:
            None
        """

        try:
            HardwareInterface.m.exit()
            logging.info('Manifold Control Unloaded')
        except Exception:
            warnings.warn('Could Not Unload Manifold')
            pass
        try:
            HardwareInterface.core.unloadAllDevices()
            logging.info('MicroManager Core Unloaded')
            HardwareInterface.core.reset()
            logging.info('MicroManager Core Reset')
        except Exception:
            warnings.warn('Could Not Unload Micromanager')
            pass
        try:
            del(HardwareInterface.temp)
            logging.info('Temperature Probe Disconnected')
        except Exception:
            warnings.warn('Could Not Disconnect Temp/Hum Probe')
            pass

    
    def loadConfig(self, c):
        """
        Loads a JSON experimental configuration. Experimental configuration specifies hardware details
        and ExperimentalHarness initial values.

        Arguments:
            (str) c: config path
        
        Returns:
            None
        """

        with open(c) as config_source:
            HardwareInterface.config = json.load(config_source)['Hardware']
        hc = HardwareInterface.config
        mm = hc['mm']
        wago = hc['wago']
        th = hc['temp_hum']
        HardwareInterface.mm_version = mm['version']
        HardwareInterface.mmcfg = mm['config_loc']
        HardwareInterface.coreTimeout
        HardwareInterface.valvemapPath = str(wago['valvemap_path'])
        HardwareInterface.manifoldAddress = wago['address']
        HardwareInterface.manifoldOffset = wago['offset']
        HardwareInterface.filterBlockName = mm['filterblock_name']
        HardwareInterface.channels = mm['channels']


    def toString(self):
        """
        A string description of the HardwareInterface

        Arguments:
            None

        Returns:
            (str) Description of the experimental harness description
        """

        stringVals = {'vm', HardwareInterface.valvemapPath, 'ma': HardwareInterface.manifoldAddress, 
                        'mmv': HardwareInterface.mm_version, 'mmc': HardwareInterface.mmcfg, 
                            'f': HardwareInterface.channels}
        return 'Hardware Interface Current State: \n\
                Valvemap Path: {vm}\n\
                Manifold Address Path: {ma}\n\
                MicroManager Version: {mmv}\n\
                MicroManager Config: {mmc}\n\
                Filters: {f}\n'.format(**stringVals)

    def __del__(self):
        self.unloadHardware()



class TemperatureProbe:
    def __init__(self, vid = '0x1313', pid = '0x80F8'):
        """
        Temperature Probe object for connection and query of Thorlabs TSP01 temperature/humidity probe

        Arguments:
            (str) vid: Vendor ID (hex)
            (str) pid: Product ID (hex)

        Returns:
            None
        """
        self.vid = vid
        self.pid = pid
        self.rm = visa.ResourceManager() #pyvisa


    def load(self):
        """
        Opens Thorlabs TSP01 temperature/humidity probe as pyvisa resource

        Arguments:
            None

        Returns:
            None
        """
        for device in self.listVISAResources():
            if self.vid in device and self.pid in device:
                try:
                    self.inst = self.rm.open_resource(str(device))
                except:
                    raise IOError('Connection to probe could not be established')


    def getDeviceInfo(self):
        """
        Queries probe IDN

        Arguemnts:
            None

        Returns:
            (dict) A dictionary of device ID fields to values 
        """
        fields = ['Model', 'SerialNo', 'FirmwareRev']
        return dict(zip(fields, self.inst.query('*IDN?').split(',')))


    def listVISAResources(self):
        """
        Lists available VISA resources

        Arguments:
            None

        Returns:
            (list) Connected VISA resources
        """
        return self.rm.list_resources()


    def getOnboardTemp(self):
        """
        Query onboard temperature (celcius)

        Arguments:
            None
        Return:
            (float) Onboard temperature (celcius)
        """

        try:
            temp = float(self.inst.query('SENS1:TEMP:DATA?'))
        except:
            warnings.warn('Could not read onboard probe temperature')
            temp = 999.9

    def getProbeTemp(self):
        """
        Query outboard temperature (celcius)

        Arguments:
            None
        Return:
            (float) Outboard temperature (celcius)
        """

        try:
            temp = float(self.inst.query('SENS3:TEMP:DATA?'))
        except:
            warnings.warn('Could not read outboard probe temperature')
            temp = 999.9
        return temp


    def getHumidity(self):
        """
        Query onboard humidity (realtive %)

        Arguments:
            None
        Return:
            (float) Onboard humidity (%)
        """
        try:
            temp = float(self.inst.query('SENS2:HUM:DATA?'))
        except:
            warnings.warn('Could not read probe humidity')
            hum = 999.9
        return hum


    def launchGUI(self, static_window = None):
        """
        TODO: Implement Jupyter widget for real-time temperature/humidity tracking
        """
        return


    def __del__(self):
        self.inst.close()
        self.rm.close()