# title             : valvecontrol.py
# description       : eMITOMI-specific utilities for experimental acquisition notebook
# authors           : Daniel Mokhtari
# credits           : Scott Longwell
# date              : 20180520
# version update    : 20190326
# version           : 0.1.1
# usage             : With permission from DM
# python_version    : 2.7


import time

from acqpack import gui
from runpack.io import HardwareInterface as hi
from runpack.io import ExperimentalHarness as eh


referenceIndex = 'chip' #Column name in valvemap


def launchGui():
    """
    Wrapper for AcqPack manifold-controlling widget

    Arguments:
        None

    Returns:
        None
    """
    gui.manifold_control(hi.m, referenceIndex)


def open(reference, valveName, logging = True):
    """
    Opens a valve.

    Arguments:
        (str) reference:valvemap reference name
        (str) valveName: Valve name as per valvemap
        (bool) logging; flag to log valve state change
    
    Returns:
        None
        
    """
    hi.m.open(reference, valveName)
    if logging: 
        eh.valvelogger.info('Opened {}'.format(valveName))


def close(reference, valveName, logging = True):
    """
    Closes a valve.

    Arguments:
        (str) reference:valvemap reference name
        (str) valveName: Valve name as per valvemap
        (bool) logging; flag to log valve state change
    
    Returns:
        None
        
    """
    hi.m.close(reference, valveName)
    if logging: 
        eh.valvelogger.info('Closed {}'.format(valveName))


def openValves(devices, valves, reference = hi.valveReferenceIndex, logging = True):  
    """
    Opens specified valves of specified devices. If one valve is given, that valve is opened on all devices.

    Arguments:
        (list) devices: list of devices (e.g. ['d1', 'd2', and 'd3'])
        (list) valves: list of valves. (e.g. ['bb'] or ['bb, na, out'])

    Returns:
        None

    """
    dnums = [dname[-1] for dname in devices]
    for dnum in dnums:
        for valve in valves:
            time.sleep(0.005)
            open(reference, valve+str(dnum), logging = False)
    if logging:
        eh.valvelogger.info('Opened Valve(s) {} for Device(s) {}'.format(valves, devices))


def closeValves(devices, valves, reference= hi.valveReferenceIndex, logging = True):
    """
    Closes specified valves of specified devices. If one valve is given, that valve is closed on all devices.

    Arguments:
        (list) devices: list of devices (e.g. ['d1', 'd2', and 'd3'])
        (list) valves: list of valves. (e.g. ['bb'] or ['bb, na, out'])

    Returns:
        None

    """
    dnums = [dname[-1] for dname in devices]
    for dnum in dnums:
        for valve in valves:
            time.sleep(0.005)
            close(reference, valve+str(dnum), logging = False)
    if logging:
        eh.valvelogger.info('Closed Valve(s) {} for Device(s) {}'.format(valves, devices))


def returnToSafeState(devices, valves = 'all', reference = 'chip', logging = True):
    """
    Closes all valving (shuts all inlets/outlets, depresses buttons, sandwiches, and necks)
    
    Note: flowValves ['w','bb','na','ph','ext1','ext2','prot', 'hep','out','in']
          controlValves ['neck','b1','b2','s1','s2']

    Arguments:
        (list) devices: list of devices to return to safe state (name only, e.g. 'd1')
        (str) valves: which valving to shut ('all', 'flow', or 'control')

    Returns:
        None

    """

    if valves == 'all':
        for device in devices:
            closeValves(devices, hi.flowValves, logging = False)
            closeValves(devices, hi.controlValves, logging = False)
        if logging:
            eh.valvelogger.info('Closed all valves for devices {}'.format(devices))
    elif valves == 'flow':
        for device in devices:
            closeValves(devices, hi.flowValves, logging = False)
        if logging:
            eh.valvelogger.info('Closed flow valves for devices {}'.format(devices))
    elif valves == 'control':
        for device in devices:
            closeValves(devices, hi.controlValves, logging = False)
        if logging:
            eh.valvelogger.info('Closed control valves for devices {}'.format(devices))