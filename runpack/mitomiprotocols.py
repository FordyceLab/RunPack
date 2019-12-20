# title             : eMITOMIprotocols.py
# description       : HT-MEK specific protocols for experimental acquisition
# authors           : Daniel Mokhtari
# credits           : Craig Markin
# date              : 20180520
# version update    : 20191219
# version           : 0.1.1
# usage             : With permission from DM
# python_version    : 2.7


import time
from Queue import Queue

import numpy as np
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler

from runpack import valvecontrol as vc
from runpack import imagingcontrol as ic
from runpack.io import HardwareInterface as hi
from runpack.io import ExperimentalHarness as eh


################################################################################


def patternDevices(devices, inletNames = None, blocknames = None):
    """Performs device surface patterning

    Performs patterning on passed list of devices assuming standard input line 
    configuration (bBSA in 'bb', NeutrAvidin in 'NA', antibody in 'pHis', and 
    PBS in 'Hepes'). Be sure to attach a "waste tail" to the device, and open 
    all lines to pressure before executing.

    Custom inlet names should be of the form {'na': [na_renamed], 'ph': 
    [ph_renamed], 'bb': [bb_renamed], 'hep': [bb_renamed], 'w': [w_renamed]}
    
    Custom blocknames should be of the form ['bn1', 'bn2', 'bn3',..., 'bnn']
    Blocks opening/closing will occur with inlet opening/closing

    Args:
        devices (list): list of devices to be patterned, lowercase (e.g. 
            ['d1', 'd2', and 'd3'])
        inletNames (dict): remapped inlet names containing precisely {'w':[
            w_renamed], 'na': [na_renamed], 'ph': [ph_renamed], 
            'bb': [bb_renamed], 'hep': [bb_renamed]}. Should not contain trailing index.
        blocknames (list): block control valve names of the form ['c1', 'c2', ..., 'c3']. 
            Valvenames should not containing trailing device index.

    Returns:
        None
    """
    
    wasteValve = ['w']
    buttonValves = ['b1', 'b2']
    sandwichValves = ['s1', 's2']
    inletValve = ['in']
    outlet = ['out']
    wasteValve = ['w']
    naValve = ['na']
    antibodyValve = ['ph']
    bbsaValve = ['bb']
    bufferValve = ['hep']
    if inletNames:
        wasteValve = inletNames['w']
        naValve = inletNames['na']
        antibodyValve = inletNames['ph']
        bbsaValve = inletNames['bb']
        bufferValve = inletNames['hep']
    if blocknames:
        inletValve = inletValve + blocknames


    vc.returnToSafeState(devices) # Closing all valves

    eh.scriptlogger.info('>> 1/18. Starting Device Patterning for devices {}. \
        Starting with all valves closed. NOTE: flow of non-biotinylated BSA \
        should have already been done'.format(devices))
    eh.scriptlogger.info('2/18. Opening sandwiches, outlet, bBSA inlet, and waste. \
        Flushing bBSA through inlet tree to waste for 30s')
    vc.openValves(devices, sandwichValves + outlet + bbsaValve + wasteValve)
    time.sleep(30)

    eh.scriptlogger.info('3/18. Done Flushing bBSA to waste. Flushing bBSA through \
        devices with buttons closed for 5min')
    vc.closeValves(devices, wasteValve)
    vc.openValves(devices, inletValve)
    time.sleep(300)

    eh.scriptlogger.info('4/18. Opened buttons with bBSA flowing through devices to waste for 35min')
    vc.openValves(devices, buttonValves)
    time.sleep(2100)

    eh.scriptlogger.info('5/18. Done Flowing bBSA through devices and closed inlet. \
        Flushing PBS through inlet tree to waste for 30s')
    vc.closeValves(devices, bbsaValve + inletValve)
    vc.openValves(devices, bufferValve + wasteValve)
    time.sleep(30)

    eh.scriptlogger.info('6/18. Done flowing PBS to waste. Flushing PBS through device \
        with  buttons open for 10min')
    vc.closeValves(devices,  wasteValve)
    vc.openValves(devices, inletValve)
    time.sleep(600)

    eh.scriptlogger.info('7/18. Done flushing PBS through devices. \
        Flowing neutravidin through inlet tree to waste for 30s')
    vc.closeValves(devices, bufferValve + inletValve)
    vc.openValves(devices, naValve + wasteValve)
    time.sleep(30)

    eh.scriptlogger.info('8/18. Done flushing Neutravidin to waste. \
        Flowing Neutravidin through devices with buttons open for 30min')
    vc.closeValves(devices, wasteValve)
    vc.openValves(devices, inletValve)
    time.sleep(1800)

    eh.scriptlogger.info('9/18. Done flowing Neutravidin through devices. \
        Flowing PBS through devices with buttons open for 10min')
    vc.closeValves(devices, naValve)
    vc.openValves(devices, bufferValve)
    time.sleep(600)

    eh.scriptlogger.info('10/18. Done flowing PBS through devices and closed buttons. \
        Flowing bBSA through the device for another 35min (quench walls only)')
    vc.closeValves(devices, bufferValve + buttonValves)
    vc.openValves(devices, bbsaValve)   
    time.sleep(2100)

    eh.scriptlogger.info('11/18. Done flowing bBSA through devices. \
        Flowing PBS through the device for 10min. **NEXT STEP IS ANTIBODY FLOWING**')
    vc.closeValves(devices, bbsaValve)
    vc.openValves(devices, bufferValve)
    time.sleep(600)

    eh.scriptlogger.info('12/18. Done flowing PBS through devices and closed inlet. \
        Flowing Antibody through inlet tree to waste for 30s')
    vc.closeValves(devices, bufferValve + inletValve)
    vc.openValves(devices, antibodyValve + wasteValve)
    time.sleep(30)
            
    eh.scriptlogger.info('13/18. Done flowing Antibody through inlet tree. Flowing \
        Antibody through device for 2min')
    vc.closeValves(devices, wasteValve)
    vc.openValves(devices, inletValve)
    time.sleep(120)

    eh.scriptlogger.info('14/18. While flowing Antibody through devices, opened buttons. \
        Flowing for 13.3min')
    vc.openValves(devices, buttonValves)
    time.sleep(800)

    eh.scriptlogger.info('15/18. Closed buttons while flowing Antibody through device for 30s')
    vc.closeValves(devices, buttonValves)
    time.sleep(30)

    eh.scriptlogger.info('16/18. Done flowing Antibody through device. Flowing PBS through \
        inlet tree to waste for 30s')
    vc.closeValves(devices, antibodyValve + inletValve)
    vc.openValves(devices, bufferValve + wasteValve)
    time.sleep(30)      

    eh.scriptlogger.info('17/18. Done flowing PBS to waste. Flowing PBS through device for 10min')
    vc.closeValves(devices, wasteValve)
    vc.openValves(devices, inletValve)
    time.sleep(600)

    eh.scriptlogger.info('18/18. Closed the outlets')
    vc.closeValves(devices, outlet)
    
    eh.scriptlogger.info('>> Done with device patterning')


def performSDSWash(deviceNames, channelsExposures, sdsInputLines, bufferInputLines):
    """SDS pH 6.0 MES wash 

    Standard protocol of four 5-minute pulses with 10-min post-pulse recovery.
    Do not inlcude trailing device nuymber in input line names
    Protocol Time: ~1.0h, 
    Rev. 102817, DM
    
    
    Args:
        deviceNames (list): list of devices for which to perform SDS washes 
            (e.g., ['d1', 'd2', 'd3'])
        channelsExposures (dict): Dictionary of channels mapped to exposures 
            (e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
        sdsInputLines (list): names of SDS input ports (without trailing device number)
        bufferInputLines (list): names of buffer input ports (without trailing device number)

    Returns:
        None
    
    """

    deviceNumbers = [d[1:] for d in deviceNames]
    sdsInputs = ["{}{}".format(b, a) for a, b in zip(deviceNumbers, sdsInputLines)]
    mopsLines = ["{}{}".format(b, a) for a, b in zip(deviceNumbers, bufferInputLines)]
    
    startMessage = 'SDS Washes Started for Devices {}'.format(str(deviceNames))
    eh.scriptlogger.info(startMessage)
    
    try:
        vc.returnToSafeState(deviceNames) 
        for washNumber in range(1, 5):
            washStartMessage = 'SDS Wash Number {} Started for devices {}'.format(washNumber, str(deviceNames))
            eh.scriptlogger.info(washStartMessage)
            time.sleep(0.5)
           
            vc.openValves(deviceNames, ['s1', 's2'])            #Open sandwiches, bring to start state
            map(lambda v: vc.open('chip', v), sdsInputs)        #Open SDS Inputs
            vc.openValves(deviceNames, ['w'])                   #Open the Wastes
            time.sleep(10)

            vc.closeValves(deviceNames, ['w'])                  #Close the Wastes
            vc.openValves(deviceNames, ['in'])                  #Open Tree Inputs, Start SDS Flowing
            vc.openValves(deviceNames, ['out'])                 #Open Outlets, Start SDS Flowing
            time.sleep(300)

            vc.closeValves(deviceNames, ['in'])                 # Close inlet tree to stop flow
            map(lambda v: vc.close('chip', v), sdsInputs)       # Close the SDS input lines
            map(lambda v: vc.open('chip', v), mopsLines)        # Open Buffer Port
            vc.openValves(deviceNames, ['w'])                   # Open the waste to flush inlet tree
            time.sleep(10)

            vc.closeValves(deviceNames, ['w'])                  # Close the waste to stop inlet tree flush
            vc.openValves(deviceNames, ['in'])                  # Open the inlet tree to flush devices
            time.sleep(600) 
            
            vc.returnToSafeState(deviceNames)                   # Close everything in preparation for next cycle

            washEndMessage = 'SDS Wash Number {} Ended for devices {}'.format(washNumber, str(deviceNames))
            eh.scriptlogger.info(washEndMessage)
    
    except Exception:
        eh.scriptlogger.warning('The SDS Wash Failed with an Exception! Closing all valves')
        vc.returnToSafeState(deviceNames)
        
    endMessage = 'SDS Washes Ended for Devices {}'.format(str(deviceNames))
    eh.scriptlogger.info(startMessage)
    
    vc.returnToSafeState(deviceNames)


def flowSubstrateStartAssay(deviceName, substrateInput, KineticAcquisition, 
    equilibrationTime = 600, treeFlushTime = 20, postEquilibrationImaging = False, 
    performImaging = True, postEquilibImageChanExp = {'4egfp':[500]}, scanQueueFlag = False):
    """Performs a standard enzyme turnover assay. 

    Flows substrate, exposes buttons and closes sandwiches, 
    performs imaging at specified timesteps
    Rev. 102817, DM
    
    Args:
        substrateInput (str): valve name of input
        deviceName (str): name of device
        equilibrationTime (int): time to flush device before assay
        
    Returns:
        None
    """   

    sendToQueue = scanQueueFlag  
    inputValve =  substrateInput[:-1]

    eh.scriptlogger.info('>> Flowing substrate, starting assay for \
        device {} in lines {}'.format(deviceName, str(substrateInput)))
    deviceNumber = str(deviceName[-1])
    
    #Flush the inlet tree
    eh.scriptlogger.info('The inlet tree wash started for substrate in ' + str(substrateInput))
    vc.returnToSafeState([deviceName])
    vc.openValves([deviceName], [inputValve, 'w'])
    time.sleep(treeFlushTime)
    eh.scriptlogger.info('The inlet tree wash done for substrate in ' + str(substrateInput))
    
    #Expose chip to substrate, equilibrate for equilibrationTime
    eh.scriptlogger.info('Chip equilibration started for substrate in ' + str(substrateInput))
    if inputValve == 'w': #For the instance where the waste line is the input
        pass
    else:
        vc.closeValves([deviceName], ['w'])
    vc.openValves([deviceName], ['in', 'out', 's1', 's2'])
    time.sleep(equilibrationTime)
    eh.scriptlogger.info('Chip equilibration done for substrate in ' + str(substrateInput))


    if postEquilibrationImaging:
        if sendToQueue == True:
            args = [eh.rootPath, 
                    postEquilibImageChanExp, 
                    deviceName, 
                    KineticAcquisition.note.replace(" ", "_")+'_PreAssay_ButtonQuant', 
                    eh.posLists[deviceName]]
            kwargs = {wrappingFolder: True}
            ic.hardwareQueue.put((args, kwargs))
        else:
            ic.scan(eh.rootPath, 
                postEquilibImageChanExp, 
                deviceName, 
                KineticAcquisition.note.replace(" ", "_")+'_PreAssay_ButtonQuant', 
                eh.posLists[deviceName], 
                wrappingFolder = True)

    #Close things to prep for assay, and open buttons
    vc.closeValves([deviceName], [substrateInput[:-1], 'in', 'out', 's1', 's2'])
    time.sleep(0.5)
    vc.openValves([deviceName], ['b1', 'b2'])
  
    #Start the assay
    if performImaging: 
        KineticAcquisition.startAssay(eh.rootPath, 
                                        eh.posLists[deviceName], 
                                        scanQueueFlag = sendToQueue)


def measureStandardCurve(devices, devicesInputs, concentrations, channelsExposures, 
    standardType, treeFlushTime = 15, equilibrationTime = 480):
    """Sequentially flows fluorogenic product and images with "buttons up"

    Leaving group (product lines) lines pre-attached to devices
    
    Args:
        devices (list): devices to be imaged
        concentrations (list): concentrations (with units) to be flowed and 
            quantified (i.e., [c1(uM), c2(uM),..., cn(uM)])
        devicesInputs (dict): {d1: {concentration1: input1, concentration2: input2}, 
            d2: {concentration1: input1, concentration2: input2}}
        channelsExposures (dict): Dictionary of channels mapped to exposures 
            (e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
        standardType (str): keyword descriptor for standard (e.g., cMU, FL, or PBP)
        
    Returns: 
        None
    """

    eh.scriptlogger.info('Measuring Standard Curves for ' 
                            + str(devices) 
                            + 'with ' 
                            + str(channelsExposures))
    timeSpacings = []
    s = BackgroundScheduler()
    s.start()
    for concentration in concentrations:
        concentrationScans = []
        for device in devicesInputs.keys():
            inputLine = devicesInputs[device][concentration]
            description = '{}_{}_{}_{}'.format(str(device), 
                                                str(concentration), 
                                                str(standardType), 
                                                str(inputLine))
            k = ic.KineticAcquisition(device, channelsExposures, timeSpacings, description)
            concentrationScans.append(k)
            
            scanArgs = [device, inputLine, k]
            keywordArgs = {'treeFlushTime': treeFlushTime, 'equilibrationTime': equilibrationTime, 
                                'performImaging': False, 'postEquilibrationImaging': False}
            s.add_job(flowSubstrateStartAssay, args = scanArgs, kwargs = keywordArgs)
            time.sleep(0.3)

        time.sleep(treeFlushTime + equilibrationTime)
        map(lambda s: s.startAssay(eh.rootPath, eh.posLists[s.device]), concentrationScans)
    vc.returnToSafeState(devices)


def flowSubstratesStartConcurrentAssays(deviceNames, substrateInputs, KineticAcquisitions, data_dir, pos_lists, 
    equilibrationTime = 480, treeFlushTime = 20):
    """Concurrently executes two assays 

    Assays are riffled, but executed concurrently, and with the same timepoints.
    Best for use in control assays for multiple devices.
    Rev. 103017, DM
   
    Args:
        deviceNames (list): names of devices for which to run assays, in 
            numerical device order (e.g., ['d1', 'd2'])
        substrateInputs (list): names of input lines (NOT CONTAINING THE 
            TRAILING DEVICE NUMBER) containing substrates to assay, in 
            numerical device order (e.g., [prot, ext1])
        KineticAcquisitions (list): list of KineticAcquisition objects 
            containing acquisition parameters. Note that 'd1' KineticAcquisition 
            timings will be used to drive both devices
        data_dir (str): path of root data directory
        pos_lists (list): list of device-specific position lists, in 
            numerical device order (e.g., [posLists['d1'], posLists['d2']])
        equilibrationTime (int): time to flow substrate through device before 
            assay start (s)
        treeFlushTime (int): time to flow substrate through inlet tree before 
            device equilibration (s)

    Returns:
        None
    """

    eh.scriptlogger.info('**Flowing substrate, starting concurrent for devices \
        {} in lines {}'.format(str(deviceNames), str(substrateInputs)))

    # Flush the inlet trees
    eh.scriptlogger.info('The inlet tree wash started for substrates in ' + str(substrateInputs))
    
    # Close Everything
    vc.returnToSafeState(deviceNames)

    # vc.openValves(deviceNames, ['hep', 'b1', 'b2'])
    vc.open('chip', substrateInputs[0])
    vc.open('chip', substrateInputs[1])
    vc.openValves(deviceNames, ['w'])
    time.sleep(treeFlushTime)
    eh.scriptlogger.info('The inlet tree wash done for substrates in ' + str(substrateInputs))

    #Expose chips to substrate, equilibrate for equilibrationTime
    eh.scriptlogger.info('Chip equilibration started for substrates in ' + str(substrateInputs))
    
    vc.closeValves(deviceNames, ['w'])
    vc.openValves(deviceNames, ['in'])
    vc.openValves(deviceNames, ['out'])
    vc.openValves(deviceNames, ['s1, s2']) # Open both device sandwiches
    time.sleep(equilibrationTime)
    eh.scriptlogger.info('Chip equilibration done for substrates in ' + str(substrateInputs))

    #Close d1 input, inlet tree, outlet, and sandwiches (for d1 only1!!)
    
    vc.close('chip', substrateInputs[0])
    vc.closeValves([deviceNames[0]], ['in'])
    vc.closeValves([deviceNames[0]], ['out'])
    vc.closeValves([deviceNames[0]], ['s1', 's2'])

    # Name the kinetic acquisitions and directories
    d1Kinetics = KineticAcquisitions[0]
    d2Kinetics = KineticAcquisitions[1]
    d1KineticSubfolder = '{}_{}_{}'.format('d1', 
                                            time.strftime("%Y%m%d_%H%M%S", time.localtime()), 
                                            d1Kinetics.note.replace(" ", "_"))
    d2KineticSubfolder = '{}_{}_{}'.format('d2', 
                                            time.strftime("%Y%m%d_%H%M%S", time.localtime()), 
                                            d2Kinetics.note.replace(" ", "_"))
    d1kineticDirectory = os.path.join(data_dir, d1KineticSubfolder)
    d2kineticDirectory = os.path.join(data_dir, d2KineticSubfolder)
    os.makedirs(d1kineticDirectory)
    os.makedirs(d2kineticDirectory)

    eh.scriptlogger.info('Concurrent Kinetic Acquisitions Started: ' 
        + str(d1Kinetics.note.replace(" ", "_")) 
        + ' & ' 
        + str(d2Kinetics.note.replace(" ", "_")))

    #Open d1 buttons only
    vc.openValves([deviceNames[0]], ['b1', 'b2'])

    scanIndex = 0
    d1ScanQueue = Queue()
    d2ScanQueue = Queue()
    map(lambda k: d1ScanQueue.put(k), d1Kinetics.delayTimes)
    map(lambda k: d2ScanQueue.put(k), d2Kinetics.delayTimes)

    lastScanTime = time.time()
    while not d1ScanQueue.empty():
        nextScanDelay = d1ScanQueue.get() # Dequeue the next scan
        deltaTime = (nextScanDelay + lastScanTime) - time.time()
        # If too much elapsed time on previous scans, scan right away
        if deltaTime <= 0:
            # For the first scan, scan d1, then change d2 valve states to start the 
            # reaction on d2, then scan d2 immediately
            if scanIndex == 0:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                    d1Kinetics.channelsExposures, 
                    d1Kinetics.device, 
                    d1Kinetics.note.replace(" ", "_"), p
                    os_lists[0], 
                    wrappingFolder = True)
                
                vc.close('chip', substrateInputs[1])
                vc.closeValves([deviceNames[1]], ['in'])
                vc.closeValves([deviceNames[1]], ['out'])
                vc.closeValves([deviceNames[1]], ['s1', 's2'])
                vc.openValves([deviceNames[1]], ['b1', 'b2'])

                ic.scan(d2kineticDirectory, 
                    d2Kinetics.channelsExposures, 
                    d2Kinetics.device, 
                    d2Kinetics.note.replace(" ", "_"), 
                    pos_lists[1], 
                    wrappingFolder = True)
                    scanIndex+=1
            else:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                    d1Kinetics.channelsExposures, 
                    d1Kinetics.device, 
                    d1Kinetics.note.replace(" ", "_"), 
                    pos_lists[0], 
                    wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                    d2Kinetics.channelsExposures, 
                    d2Kinetics.device, 
                    d2Kinetics.note.replace(" ", "_"), 
                    pos_lists[1], 
                    wrappingFolder = True)
        # If you have time to spare, wait, then proceed
        else:
            time.sleep(deltaTime)
            if scanIndex == 0:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                
                vc.close('chip', substrateInputs[1])
                vc.closeValves([deviceNames[1]], ['in'])
                vc.closeValves([deviceNames[1]], ['out'])
                vc.closeValves([deviceNames[1]], ['s1', 's2'])
                vc.openValves([deviceNames[1]], ['b1', 'b2'])

                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
                scanIndex+=1
            else:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
    
    eh.scriptlogger.info('Concurrent Kinetic Read Complete')
    

def startConcurrentImaging(deviceNames, KineticAcquisitions, data_dir, pos_lists):
    """Concurrently executes imaging for two devices.
   
    Args:
        deviceNames (list): names of devices for which to run assays, in 
            numerical device order (e.g., ['d1', 'd2'])
        KineticAcquisitions (list): list of KineticAcquisition objects containing acquisition 
            parameters. Note that 'd1' KineticAcquisition timings will be 
            used to drive both devices
        data_dir (str): path of root data directory
        pos_lists (list): list of device-specific position lists, in numerical 
            device order (e.g., [posLists['d1'], posLists['d2']])

    Returns:
        None
    """

    # Name the kinetic acquisitions and directories
    d1Kinetics = KineticAcquisitions[0]
    d2Kinetics = KineticAcquisitions[1]
    d1KineticSubfolder = '{}_{}_{}'.format(deviceNames[0], 
                                            time.strftime("%Y%m%d_%H%M%S", time.localtime()), 
                                            d1Kinetics.note.replace(" ", "_"))
    d2KineticSubfolder = '{}_{}_{}'.format(deviceNames[1], 
                                            time.strftime("%Y%m%d_%H%M%S", time.localtime()), 
                                            d2Kinetics.note.replace(" ", "_"))
    d1kineticDirectory = os.path.join(data_dir, d1KineticSubfolder)
    d2kineticDirectory = os.path.join(data_dir, d2KineticSubfolder)
    os.makedirs(d1kineticDirectory)
    os.makedirs(d2kineticDirectory)

    eh.scriptlogger.info('Concurrent Imaging Started for \
        {}, {} & {}'.format(str(deviceNames), 
                            str(d1Kinetics.note.replace(" ", "_")), 
                            str(d2Kinetics.note.replace(" ", "_"))))
    scanIndex = 0
    d1ScanQueue = Queue()
    d2ScanQueue = Queue()
    map(lambda k: d1ScanQueue.put(k), [0] + d1Kinetics.delayTimes)
    map(lambda k: d2ScanQueue.put(k), [0] + d2Kinetics.delayTimes)

    lastScanTime = time.time()
    while not d1ScanQueue.empty():
        nextScanDelay = d1ScanQueue.get() # Dequeue the next scan
        deltaTime = (nextScanDelay + lastScanTime) - time.time()
        # If you've gobbled up too much time on previous scans, scan right away
        if deltaTime <= 0:
            # For the first scan, scan d1, then change d2 valve states to start the reaction on d2, 
            # then scan d2 immediately
            if scanIndex == 0:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
                scanIndex+=1
            else:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
        # If you have time to spare, wait, then proceed:
        else:
            time.sleep(deltaTime)
            if scanIndex == 0:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
                scanIndex+=1
            else:
                lastScanTime = time.time()
                ic.scan(d1kineticDirectory, 
                        d1Kinetics.channelsExposures, 
                        d1Kinetics.device, 
                        d1Kinetics.note.replace(" ", "_"), 
                        pos_lists[0], 
                        wrappingFolder = True)
                ic.scan(d2kineticDirectory, 
                        d2Kinetics.channelsExposures, 
                        d2Kinetics.device, 
                        d2Kinetics.note.replace(" ", "_"), 
                        pos_lists[1], 
                        wrappingFolder = True)
    eh.scriptlogger.info('Concurrent Imaging Complete for {}'.format(str(deviceNames)))



def makeAssayTimings(numLinearPoints = 5, totalPoints = 15, scanTime = 90, totalTime = 3600):
    """


    """
    logPoints = totalPoints - numLinearPoints
    baseTimes = []
    pointDensity = 1
    pointDenistyIncremener = 0.002

    while sum(baseTimes) < totalTime:
        pointDensity += pointDenistyIncremener
        baseTimes = [scanTime] * numLinearPoints
        logTimings = list(np.logspace(np.log10(scanTime), 
                                        np.log10(float(scanTime)**pointDensity), 
                                        num=logPoints, 
                                        dtype=int))
        baseTimes.extend(logTimings)
    
    baseTimes = [scanTime] * numLinearPoints
    logTimings = list(np.logspace(np.log10(scanTime), 
                                    np.log10(float(scanTime)**(pointDensity-pointDenistyIncremener)), 
                                    num=logPoints, 
                                    dtype=int))
    baseTimes.extend(logTimings)
    return baseTimes


def flushInletTree(deviceNames, inputInlet, vacantInlets, flushTime):
    """


    """
    
    # Close all the inlets AND the tree inlet (make no assumptions)
    allInputs = ['hep', 'prot', 'ext2', 'ext1', 'ph', 'na', 'bb', 'w']
    vc.closeValves(deviceNames, allInputs + ['in'])

    indexes = range(len(allInputs))
    indexesInputs = dict(zip(allInputs, indexes))

    inputIndex = indexesInputs[inputInlet]

    # Get the distance from the inputInlet to the vacantInlet mapped to the vacantInlet ID
    vacantInletsOrganized = {}
    for inlet in vacantInlets:
        vacantInletsOrganized[abs(indexesInputs[inlet] - inputIndex)] = [inlet] # distance->port

    vc.openValves(deviceNames, [inputInlet])
    # Now from close to far, open the valve and wash for the flushTime
    for inlet in sorted(vacantInletsOrganized.keys()):
        vc.openValves(deviceNames, vacantInletsOrganized[inlet])
        time.sleep(flushTime)
        vc.closeValves(deviceNames, vacantInletsOrganized[inlet])

    # Close all the inlets AND the tree inlet (again, make no assumptions)
    vc.closeValves(deviceNames, [inputInlet])



def performGFPTitration(expObject, deviceName, channelsExposures, channelsExposuresTimecourse, 
    eGFPInput, bufferInput, numPreEquilibriumSteps = 4, inletTreeFlushTime = 30, 
    preEquilibrationFlushTime = 600, stepUpEquilibrationTime = 360, eGFPTitrationBindingTimes = [], 
    scanTime = 90, numTitrationTimepoints = 10):
    """Performs a GFP titration experiment.
    Starting State: Chip Patterned, Buttons Down (protected)
    Reagent Lines: 1x MOPS reaction buffer (with Zn2+), 3nM or 5nM eGFP+2% BSA 
        in 1x reaction buffer (200uL is sufficient)

    Experimental Description________________________________________
    1. Close valving and single scan in GFP (pre-assay background)

    2. Pre-equilibrate the chamber walls (saturate with GFP)
        - Flow eGFP continuously
        - Close eGFP and flow buffer continously
        - Single scan in eGFP (post-equilibration, step no.)
        - Repeat Nx
    
    3. Control for eGFP Binding from the wall to button
        - Close all valves
        - Open buttons to allow eGFP binding
        - Image kinetically over time
        - Close buttons

    4. Single scan in GFP (pre-step-up button quant)

    5. Titration steps (with imaging time calculations)
        - Flow GFP, start imaging (flowSubstrateStartAssay)
            - Pre-assay imaging = true (adds about 2min flow time, 10min flow total)
            - Kinetic imaging, logarithmically, proportional to titration step number
        - Buttons down
        - Single scan

    6. Post-Titration Buffer Flush and Imaging
    _______________________________________________________________

    Args:
        expObject (eh.ExperimentalHarness): Experimental Harness Object
        deviceName (str): deviceName (i.e., 'd1', 'd2', 'd3')
        channelsExposures (dict): For final timepoints (endpoints). Dictionary 
            of channels mapped to exposures (e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
        channelsExposureTimecourse (dict): For all timecourses, typically with 
            reduced exposure times to limit time for assay. 
            Dictionary of channels mapped to exposures (e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
        eGFPInput (str): full name of 5nM eGFP input line (e.g., prot1, ext21, ...)
        bufferInput (str): full name of washing buffer input line (e.g., hep1, hep2, ...)
        numPreEquilibriumSteps (int): number of wall-binding pre-equilibration 
            steps to perform
        inletTreeFlushTime (int): time (seconds) to perform all inlet tree flushes
        preEquilibrationFlushTime (int): time (seconds) to flow eGFP, and then 
            Buffer, in wall-binding steps
        stepUpEquilibrationTime (int): time (seconds) to flow eGFP prior to each
            titration binding step
        eGFPTitrationBindingTimes (list): list of total times to bind, in temporal order
        scanTime (int): estimated length of a set of scans for channelsExposures
        numTitrationTimepoints (int): number of kinetic timepoints to obtain for
            each eGFP binding titration step, spanning time given in eGFPTitrationBindingTimes

    Returns:
        None
    """

    inputs = {'hep', 'prot', 'ext2', 'ext1', 'ph', 'na', 'bb', 'w'}

    if eGFPInput not in inputs or bufferInput not in inputs:
        raise ValueError('Port name(s) incorrectly specified. \
                            The eGFP and Buffer Input Ports must be specified without a \
                            trailing device number')

    eh.scriptlogger.critical('Starting eGFP Titration in 10s')
    time.sleep(10) # A safety in case you notice something wrong
   
    # 1. Close valving, scan GFP
    eh.scriptlogger.info('1/6. Started Assay. Preparing Valve States and Background Imaging')
    eh.scriptlogger.info(
        'GFP Input: {}, Buffer Input: {}, Channels & Exposures: {}, \
        Pre-Equilibration Steps: {}, Titration Steps: {}\
        '.format(
            eGFPInput, 
            bufferInput, 
            channelsExposures, 
            numPreEquilibriumSteps, 
            len(eGFPTitrationBindingTimes))
            )

    vc.returnToSafeState([deviceName])
    ic.scan(expObject.rootPath, 
            channelsExposures, 
            deviceName, 
            'PreAssay ButtonQuant', 
            eh.posLists[deviceName], 
            wrappingFolder = True)
    eh.scriptlogger.info('Completed Pre-Imaging')
   
    # 2. Pre-equilibration of chamber walls
    eh.scriptlogger.info('2/6. Started Wall Pre-Equilibration')
    vc.openValves([deviceName], ['s1', 's2', 'out'])
    for step in range(numPreEquilibriumSteps):
        eh.scriptlogger.warning('Started eGFP/Buffer Pre-Equilibration Cycle {} of {}, {}s \
            Cycle Time'.format(step+1, numPreEquilibriumSteps, preEquilibrationFlushTime*2))
        vc.openValves([deviceName], [eGFPInput, 'in'])
        time.sleep(preEquilibrationFlushTime)
        vc.closeValves([deviceName], [eGFPInput])
        vc.openValves([deviceName], [bufferInput])
        time.sleep(preEquilibrationFlushTime)
        ic.scan(expObject.rootPath, channelsExposures, deviceName, 'PostPreEquilibrationBinding \
            Step {}'.format(step+1), eh.posLists[deviceName], wrappingFolder = True)
        vc.closeValves([deviceName], [bufferInput])
        eh.scriptlogger.warning('Completed Pre-Equilibration Cycle {} of {}'.format(step+1, numPreEquilibriumSteps))
    eh.scriptlogger.info('Completed Wall Pre-Equilibration')

    # 3. eGFP from wall to button control (timecourse, ~20min)
    eh.scriptlogger.info('3/6. Started Wall to Button Control')
    vc.returnToSafeState([deviceName])
    wallToButtonTimings = {}
    wallToButtonTimings['fromWallsControl'] = makeAssayTimings(numLinearPoints = 5, 
                                                                totalPoints = 8, 
                                                                scanTime = scanTime, 
                                                                totalTime = 1200)
    expObject.addAssayTimings(wallToButtonTimings)
    fromButtonsToWalls = ic.KineticAcquisition(deviceName, 
                                                channelsExposuresTimecourse, 
                                                expObject.assayTimes['fromWallsControl'], 
                                                'Kinetics ButtonstoWallsControl ButtonsUp')
    vc.openValves([deviceName], ['b1', 'b2'])
    fromButtonsToWalls.startAssay(expObject.rootPath, eh.posLists[deviceName])
    vc.closeValves([deviceName], ['b1', 'b2'])
    eh.scriptlogger.info('Completed Wall to Button Control')

    # 4. Pre-Step-Up Imaging (Buttons Down)
    eh.scriptlogger.info('4/6. Started Pre-Step-Up Quantifications')
    ic.scan(expObject.rootPath, channelsExposures, deviceName, 'PreStepUp ButtonQuant ButtonsDown', 
            eh.posLists[deviceName], wrappingFolder = True)
    eh.scriptlogger.info('Completed Pre-Step-Up Quantifications')

    # 5. eGFP Titration Steps
    eGFPTitrationTimings = {}
    eGFPTitrationTimingsKeys = []
    for step, bindingTime in enumerate(eGFPTitrationBindingTimes):
        timingsName = 'eGFPBindingStep{}Times'.format(step)
        eGFPTitrationTimingsKeys.append(timingsName)
        eGFPTitrationTimings[timingsName] = makeAssayTimings(numLinearPoints = 0, 
                                                            totalPoints = numTitrationTimepoints, 
                                                            scanTime = scanTime, 
                                                            totalTime = bindingTime)
    expObject.addAssayTimings(eGFPTitrationTimings)

    eh.scriptlogger.info('5/6. Started eGFP Titration Step-Up')
    for step, stepTimingsName in enumerate(eGFPTitrationTimingsKeys):
        w = 'Started GFP Binding Step {} of {}'.format(step+1, len(eGFPTitrationTimingsKeys))
        i = 'Titration Step {}, Timings: {}'.format(stepTimingsName, expObject.assayTimes[stepTimingsName])
        eh.scriptlogger.warning(w)
        eh.scriptlogger.info(i)
        description = 'Kinetics eGFPTitrationBindingStep {}'.format(step+1)
        ka = ic.KineticAcquisition(deviceName, 
                                    channelsExposuresTimecourse, 
                                    expObject.assayTimes[stepTimingsName], 
                                    description)
        flowSubstrateStartAssay(deviceName,  
            eGFPInput+deviceName[-1], 
            ka, 
            equilibrationTime = stepUpEquilibrationTime, 
            treeFlushTime = 10, 
            postEquilibrationImaging = True, 
            performImaging = True, 
            postEquilibImageChanExp = channelsExposures)
        vc.closeValves([deviceName], ['b1', 'b2'])
        ic.scan(expObject.rootPath, 
            channelsExposures, 
            deviceName, 
            'PosteGFPTitrationBindingStep {} ButtonsDown'.format(step+1), 
            eh.posLists[deviceName], 
            wrappingFolder = True)
        eh.scriptlogger.warning('Completed GFP Binding Step \
            {} of {}'.format(step+1, len(eGFPTitrationTimingsKeys)))

    #6. Post-Titration Washout and Imaging. Leave Under Positive Pressure
    eh.scriptlogger.info('6/6. Started Buffer Flush and Final Imaging')
    vc.returnToSafeState([deviceName])
    vc.openValves([deviceName], [bufferInput, 'w'])
    time.sleep(inletTreeFlushTime)
    vc.closeValves([deviceName], ['w'])
    vc.openValves([deviceName], ['in', 's1', 's2', 'out'])
    time.sleep(stepUpEquilibrationTime)
    vc.returnToSafeState([deviceName])
    ic.scan(expObject.rootPath, 
        channelsExposures, 
        deviceName, 
        'PostTitration PostWash ButtonsDown', 
        eh.posLists[deviceName], 
        wrappingFolder = True)
    vc.openValves([deviceName], [bufferInput, 'in', 's1', 's2'])
    eh.scriptlogger.info('Completed eGFP Titration Experiment')