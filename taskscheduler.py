# title             : taskscheduler.py
# description       : eMITOMI-specific utilities for experimental acquisition notebook
# authors           : Daniel Mokhtari
# credits           : -
# date              : 20180520
# version update    : 20180520
# version           : 0.1.0
# usage             : With permission from DM
# python_version    : 2.7


import copy
import numpy as np
import matplotlib.pyplot as plt



def busyPeriods(delayTimes, scanTime, device):
    """
    Given a series of delay times between assays, determines a series of duty cycle 
    start/stop times for the camera/scope. The first delay represents a T0 assay and a T1 assay (2 assays)
    
    Arguments:

        (list) delayTimes: time delays between chip imagings
        (int) scanTime: estimated length of scope/stage duty cycle for assay
        (str) device: name of device (e.g., 'd1')

    Returns:
        (list) busyTimes: duty cycle start/stop times for the camera/scope as [(start1, 
        stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
    
    """
    
    busyTimes = []
    startTime = 0
    for delay in delayTimes:
        busyTimes.append((startTime, startTime+scanTime, device))
        startTime += delay
    busyTimes.append((startTime, startTime+scanTime, device))
    return busyTimes


def indolentPeriods(busyTimes, maxTime = 6000):
    """
    Given a list of busy periods (duty cycle start/stop times), determines the time 
    periods for which there is no duty cycle scheduled (indolent periods)
    
    Arguments:
        (list) busyTimes: duty cycle start/stop times for the camera/scope as 
        [(start1, stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
        (int) maxTimes: total amount of time out beyond the stop time of the 
        last duty cycle to go to identify a final indolent period.
    
    Returns:
        (list) emptySpaces: start/stop times for indolent periods of scope/stage 
            as [(startIndolent1, stopIndolent1), (startIndolent2, stopIndolent2),...,(startIndolentn, stopIndolentn)]
    
    """
    
    emptySpaces = []
    index = 0
    if len(busyTimes) % 2 == 0:
        while index < len(busyTimes)-1:
            emptySpaces.append((busyTimes[index][1], busyTimes[index+1][0]))
            index += 1
        emptySpaces.append((busyTimes[index][1], busyTimes[index][1]+maxTime))
    else: 
        while index < len(busyTimes)-1:
            emptySpaces.append((busyTimes[index][1], busyTimes[index+1][0]))
            index += 1
        emptySpaces.append((busyTimes[index][1], busyTimes[index][1]+maxTime))
    return emptySpaces


def shiftScheduleOffset(schedule, offset):
    """
    For a schedule of busy periods (duty cycles) and a start time offset, shifts the schedule start to the offset time.
    
    Arguments:
        (list) schedule:
        (int) offset:
    
    Returns:
        (list) offsetSchedule: 
    
    """
    
    offsetSchedule = []
    for busyTime in schedule:
        offsetSchedule.append(tuple(map(lambda t: int(t)+offset, busyTime[0:2])))
    return offsetSchedule


def schedulingCollisionsFlag(schedule1BusyTimes, schedule2BusyTimes, overlapBuffer = 60):
    """
    Takes two schedules of busy periods (for d1 and d2) and determines if there will 
    be a collision (if a duty cycle for either overlaps within a buffer)
    
    Arguments:
        (list) schedule1BusyTimes: Device 1 duty cycle start/stop times for the camera/scope as 
            [(start1, stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
        (list) schedule2BusyTimes: Device 2 duty cycle start/stop times for the camera/scope as 
            [(start1, stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
        (int) overlapBuffer: time buffer before/after a duty cycle for which any 
            overlap would be considered a collision
    
    Returns:
        (bool) Flag true if there is a collision, otherwise false
        
    """
    
    for d2DutyCycle in schedule2BusyTimes:
        for d1DutyCycle in schedule1BusyTimes:
            d1Range = set(range(d1DutyCycle[0]-overlapBuffer, d1DutyCycle[1]+overlapBuffer))
            d2Range = set(range(d2DutyCycle[0]-overlapBuffer, d2DutyCycle[1]+overlapBuffer))
            if len(d1Range.intersection(d2Range)) != 0: 
                return True
    return False


def findRiffledSchedule(schedule1, schedule2):
    """
    Given two schedules of busy periods, examines each potential offset time from short to 
    long and attemps a riffle. If a riffle solution is found, the updated riffled assay times are returned.
    
    Arguments:
        (list) schedule1: Device 1 duty cycle start/stop times for the camera/scope as 
            [(start1, stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
        (list) schedule2: Device 2 duty cycle start/stop times for the camera/scope as 
            [(start1, stop1, deviceName), (start2, stop2, deviceName), ... (startn, stopn, deviceName)]
    
    Returns:
        (dict) Riffled schedules for d1 and d2. If an optimal riffle was not found, 
            the original schedules will be returned (no riffle)
    
    """
    
    for possibleOffsetLists in map(lambda p: range(p[0], p[1]), indolentPeriods(schedule2, 500)):
        for possibleOffset in possibleOffsetLists:
            updatedSchedule2 = shiftScheduleOffset(schedule2, possibleOffset)
            if not schedulingCollisionsFlag(schedule1, updatedSchedule2):
                return {'d1': schedule1, 'd2': updatedSchedule2}
    return {'d1': schedule1, 'd2': schedule2}


def calculateRiffleOffset(assayParamsD1, assayParamsD2, flowDelay = 625):
    """
    Given two linear series of assays for d1 and d2, riffles them by examining 
    potential sliding start times and testing for collisions.

    Arguments:
        (dict) assayParamsD1: indexed assays to perform in linear succession in 
        the form {index: ('substrateInputLine', kineticAcquisition(*initialParams))}
        (dict) assayParamsD2:
        (int) flowDelay: time to flush inlet tree and equilibrate device to be used by actual assay
    
    Returns:
        (int) offset to start imaging device 2 after start
    
    """
    
    d1Assays = copy.deepcopy(assayParamsD1[1][1].delayTimes)
    for keyIndex in sorted(copy.deepcopy(assayParamsD1).keys())[1:]:
        d1Assays.extend([flowDelay])
        d1Assays.extend(assayParamsD1[keyIndex][1].delayTimes)
    
    d2Assays = copy.deepcopy(assayParamsD2[1][1].delayTimes)
    for keyIndex in sorted(copy.deepcopy(assayParamsD2).keys())[1:]:
        d2Assays.extend([flowDelay])
        d2Assays.extend(assayParamsD2[keyIndex][1].delayTimes)

    busyTimes1 = busyPeriods(d1Assays, 70, 'd1')
    busyTimes2 = busyPeriods(d2Assays, 70, 'd2')      
    riffledSchedule = findRiffledSchedule(busyTimes1, busyTimes2)
    d1Times = np.zeros(max(riffledSchedule['d1'][-1][1]+72, riffledSchedule['d2'][-1][1]+72), dtype=int)
    d2Times = copy.deepcopy(d1Times)

    for busyPeriod in riffledSchedule['d1']:
        for index in range(busyPeriod[0], busyPeriod[1]):
            d1Times[index] = 1

    for busyPeriod in riffledSchedule['d2']:
        for index in range(busyPeriod[0], busyPeriod[1]):
            d2Times[index] = 1
        
    times = range(max(len(d1Times), len(d2Times)))
    
    #Plot the riffled schedules. Plot colors: Device1 = blue, Device2 = red, and Device1+Device2 = dashed black
    f, ax = plt.subplots(figsize = (18, 6))
    ax.plot(times, d2Times, 'r', times, d1Times, 'b', times, np.sum([d1Times, d2Times], axis=0), 'k:')
    ax.set_title('Scope/Stage Duty Cycles For Riffled D1 and D2 Schedules', fontsize = 20)
    ax.set_xlabel('Times (s)', fontsize=16)
    ax.set_ylabel('Scheduled', fontsize=16)
    ax.tick_params(axis='both', which='major', labelsize=16)
    plt.show()

    return riffledSchedule['d2'][0][0]