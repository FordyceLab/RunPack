# title             : assays.py
# description       : Standard MITOMI Concurrent Imaging
# authors           : Daniel Mokhtari
# credits           : Scott Longwell
# date              : 20180520
# version update    : 20190326
# version           : 0.1.1
# usage             : With permission from DM
# python_version    : 2.7


import time
from Queue import Queue

from runpack.io import HardwareInterface
from runpack.io import ExperimentalHarness as eh
from runpack import imagingcontrol as imaging
from runpack import mitomiprotocols as protocols



class Assay:
	def __init__(self, dname, experimentalObject, inletPort, channelsExposures, assayTimesName, description, 
		equilibrationTime = 480, treeFlushTime = 15, postEquilibrationImaging = True, forConcurrency = False):
		"""
		Traditional eMITOMI kinetic enzyme turnover assay
		# TODO: Write as parent class for eMITOMI, tfMITOMI, stabilityMITOMI subclasses

		Arguments:
			(str) dname: device name ('d1' | 'd2' |'d3')
			(ExperimentalHarness) experimentalObject:
			(str) inletPort: name of port bearing substrate/reagent
			(dict) channelsExposures: Dictionary of channels mapped to exposures 
				(e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
			(str) assayTimesName: Name of assay timing delay times in ExperimentalHarness
			(str) description: Assay description
			(int) equilibrationTime: Time (s) to equilibrate reaction chambers with substrate/reagent
			(int) treeFlushTime: Time (s) to pre-flush the inlet tree with substrate/reagent
			(bool) postEquilibrationImaging: flag to acquire chip image following equilibration
			(bool) forConcurrency: flag to execute assay as part of concurrent imaging
		
		Returns:
			None
		"""


		self.dname = dname
		self.description = description
		self.inletPort = inletPort
		self.experimentalObject = experimentalObject
		self.assayTimesName = assayTimesName
		self.forConcurrency = forConcurrency
		self.channelsExposures = channelsExposures
		self.assayParams = {'equilibrationTime': equilibrationTime, 'treeFlushTime': treeFlushTime, 
								'postEquilibrationImaging': postEquilibrationImaging}
		self.acquisitionObject = imaging.KineticAcquisition(dname, channelsExposures, 
									experimentalObject.assayTimes[assayTimesName], description)
		self.testParams()

	def startAssay(self):
		"""
		Start eMITOMI kinetic assay

		Arguments:
			None

		Returns:
			None
		"""

		protocols.flowSubstrateStartAssay(self.dname, self.inletPort, self.acquisitionObject, 
			equilibrationTime = self.assayParams['equilibrationTime'], treeFlushTime = self.assayParams['treeFlushTime'], 
			postEquilibrationImaging = self.assayParams['postEquilibrationImaging'], scanQueueFlag = self.forConcurrency)

	def testParams(self):
		"""
		Assay parameter error checking

		Arguments:
			None

		Returns:
			None
		"""

		if not self.dname in self.experimentalObject.posLists.keys():
			raise ValueError('Device name incorrect or not added to experimental object')
		
		if not self.inletPort[-1] == self.dname[-1]:
			raise ValueError('Your inlet port either lacks a trailing digit or is for another device')
		
		for channel in self.channelsExposures.keys():
			if not channel in HardwareInterface.channels:
				raise ValueError('Channel {} does not exist for hardware'.format(channel))
		
		if not self.assayTimesName in self.experimentalObject.assayTimes:
			raise ValueError('The AssayTimes name specified does not exist in experimental object. Check your spelling.')


class AssaySeries:
	def __init__(self, assayList, offsets = None):
		"""
		General-purpose assay series.

		Arguments:
			(list) assayList: list of assays objects to start, in order
			(list) offsets: list of assay start delay offsets (int)
		
		Returns:
			None
		"""

		self.dname = assayList[0].dname
		self.assayList = assayList
		self.assayQueue = self.scheduleAssays()
		self.assayParams = self.assayList[0].assayParams
		self.offsets = offsets

	def scheduleAssays(self):
		"""
		Queue up assays for execution.

		Arguments:
			None

		Returns:
			(Queue) Queue of assays to perform

		"""
		assayQueue = Queue()
		list(map(lambda k: assayQueue.put(k), self.assayList))
		return assayQueue

	def startAssays(self, scanQueueFlag = False):
		"""
		Start execution of the assay series

		Arguments:
			(bool) scanQueueFlag: flag to dequeue assays to the common scanqueue

		Returns:
			None
		"""

		if not self.offsets:
			while not self.assayQueue.empty():
				nextAssay = self.assayQueue.get()
				nextAssay.startAssay()
		else:
			while not self.assayQueue.empty():
				for offset in self.offsets:
					time.sleep(offset)
					nextAssay = self.assayQueue.get()
					nextAssay.startAssay() #Except the backgrounded version
		imaging.hardwareState += 1


class RiffledAssaySeries:

	def __init__(self, assaySeriesDict):
		"""
		A Riffled (scheduled) Assay Series Class
		Not yet implemented
		"""

		self.assaySeriesDict = assaySeriesDict
		# self.initialOffset = self.calculateInitialOffset()
		# self.otherOffsets = self.calculateOtherOffsets()
		self.assaySchedules = self.scheduleRiffle()

	def calculateInitialOffset(self):
		"""
		To be implemented
		"""
		return

	def calculateOtherOffsets(self):
		"""
		To be implemented
		"""
		return

	def startAssays(self):
		"""
		To be implemented
		"""

		imaging.hardwareBlockingFlag = True
		imaging.hardwareState = 0
		self.assaySchedules.resume()
		time.sleep(0.2)
		self.assaySchedules.resume_job('d1')
		print('d1 jobs resumed')
		time.sleep(0.2)
		self.assaySchedules.resume_job('d2')
		print('d2 jobs resumed')
		imaging.startHardwareQueue()
		self.assaySchedules.shutdow()
		return
	

	def scheduleRiffle(self):
		"""
		To be implemented
		"""
		startAssaySeries = lambda series: series.startAssays()

		backgroundConfig = {'logger': eh.scriptlogger}
		s = BackgroundScheduler(gconfig=backgroundConfig)
		s.start()
		s.pause()
		for dname, assaySeries in self.assaySeriesDict.items():
			assayArgs = [assaySeries]
			s.add_job(startAssaySeries, id = dname, misfire_grace_time = 100, args = assayArgs, next_run_time = None)
		return s
