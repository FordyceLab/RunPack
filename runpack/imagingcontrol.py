# title             : imagingcontrol.py
# description       : Imaging and stage control for RunPack experiments
# authors           : Daniel Mokhtari, Scott Longwell
# credits           : 
# date              : 20180520
# version update    : 20191219
# version           : 0.1.1
# usage             : With permission from DM
# python_version    : 2.7


import os
import time
import datetime
import numpy as np
import pandas as pd
from PIL import Image
from Queue import Queue
import matplotlib.pyplot as pl

from acqpack import gui
from runpack.io import HardwareInterface as hi
from runpack.io import ExperimentalHarness as eh


################################################################################


hardwareQueue = Queue()
hardwareBlockingFlag = True
hardwareState = 0 #State: 0 = Resting, 1 = One Queue Complete, 2 = Both Complete

def snap(show = True, vmin = 0, vmax = 65535, figsize = (4, 4)):
	"""Snaps an image and returns the resulting image array.

	Args:
		show (bool): flag to show image
		vmin (int): threshold minimum
		vmax (int): threshold max
		figsize (tuple): matplotlib image figure size

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
	"""Wrapper for acqpack.gui.video() video acquisition function.
	
	TODO: Enable live video saving to disk

	Args:
		None

	Returns:
		None
	"""

	gui.video(hi.core, loop_pause=0.05)


def startHardwareQueue():
	"""Start the hardware job queue

	Args:
		None

	Returns:
		None
	"""

	eh.acquilogger.info('HardwareQueue Started')
	while hardwareState < 2:
		args, kwargs = hardwareQueue.get(block = hardwareBlockingFlag)
		scan(*args, **kwargs)


def get_stage_position():
	"""
	TODO: Implement getting current stage position
	"""
	raise NotImplementedError('Fetching stage position not yet implemented.')


def move_stage_custom(x, y, z):
	"""Immediately move the stage to a custom (x, y, z) position

	Args:
		(float) x: target stage x coordinate
		(float) y: target stage y coordinate
		(float) z: target stage z coordinate

	Returns:
		None
	"""

	hi.core.setXYPosition(x,y)
	hi.core.waitForDevice(hi.core.getXYStageDevice())
	
	hi.core.setPosition(hi.core.getFocusDevice(), z)
	hi.core.waitForDevice(hi.core.getFocusDevice())


def move_stage_poslist(position_list, poslistIndex, zControl = True):
	"""Move the xy(z) stage to cooredinates specified by the ith
	entry in the position list. It is likely that you want to position list
	in sorted order. 
	
	Args:
		position_list (pd.DataFrame): stage xy(z) position list. z position 
			is not required. The default behavior is to move to z if present 
		poslistIndex (int): row index of position list to move to
		zControl (bool): flag to move to home z position or retain current z

	Returns:
		None
	"""

	x,y = position_list[['x','y']].iloc[i]
	hi.core.setXYPosition(x,y)
	hi.core.waitForDevice(hi.core.getXYStageDevice())
	
	if ('z' in position_list.columns) and zControl:
		z = position_list[['z']].iloc[i]
		hi.core.setPosition(hi.core.getFocusDevice(), z)
		hi.core.waitForDevice(hi.core.getFocusDevice())


def home_stage(position_list, zControl = True):
	"""Brings the stage to its initial pinlist position

	Args:
		position_list (pd.DataFrame): xy-stage or xyz-stage position list
		zControl (bool): flag to move to home z position or retain current z

	Returns:
		None
	"""

	move_stage_poslist(position_list, 0, zControl = zControl)


def scan(data_dir, channelsExposures, dname, note, position_list, 
			wrappingFolder = False, write_imaging_record = True, 
			return_imaging_record = False, zControl = True):
	"""Rastered image acquisition. 
	
	Acquires images in a raster patern and saves the results.
	Writes metadata to the acquired images.
	
	Args:
		data_dir (str): root directory of image acquisitions
		channelsExposure (dict): Dictionary of channels mapped to exposures 
			(e.g., {'2bf':[50, 500], '1pbp':[100, 200]})
		dname (str): device name ('d1' | 'd2' |'d3')
		note (str): Scan note, to be used in the image filename
		position_list (pd.DataFrame): stage xy(z) position list
		wrappingFolder (bool): flag to wrap acquistions inside another 
			directory of name notes
		zControl (bool): flag to move to home z position or retain current z
		
	Returns:
		(pd.DataFrame | None): Pandas dataframe with a summary of the image raster
	"""

	def makeDir(path):
		if not os.path.isdir(path):
			os.makedirs(path)
	
	messageItems = [str(dname), str(channelsExposures), str(note.replace(' ', '_'))]
	startMessage = 'Started Scan of {}, channelsExposures = {}, note = {}'.format(*messageItems)
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
	else:
		temp = 999.9
		hum = 999.9

	scanRecord = []
	for i in xrange(len(position_list)):
		move_stage_poslist(position_list, i, zControl)
		
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

				summary = 'Device: {}, Note: {}, ExpDescription: {}'.format('Setup 3', note, eh.experimentalDescription)
				frameInfo = '{{Channel: {}, Index:{}, Pos:({},{})}}'.format(channel, i, x, y)
				frameTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

				recordLabels = ['raster_start_time', 'scan_params', 'channel', 
								'exposure_ms', 'image_path', 'raster_index',
								'x', 'y', 'dname', 'frame_time', 'temperature', 
								'humidity', 'note','setup', 'experimental_desc']
				recordFeatures = [startTime, channelsExposures, channel, exposure, 
									imagePath, i, x, y, dname, frameTime, temp, 
									hum, note, hi.setup, 
									eh.experimentalDescription]
				scanRecord.append(dict(zip(recordLabels, recordFeatures)))
				
				exifIDs = [37888, 37889, 33434, 37510, 270, 306]
				exifValues = [temp, hum, exposure/1000.0, summary, frameInfo, frameTime]
				tags = dict(zip(exifIDs, exifValues))

				image.save(imagePath, tiffinfo = tags)

	messageItems = str(dname), str(channelsExposures), str(note.replace(" ", "_"))
	endMessage = 'Completed Scan of {}, channelsExposures = {}, note = {}'.format(*messageItems)
	eh.acquilogger.info(endMessage)
	home_stage(position_list, zControl = zControl)
	
	
	scanRecordDF = pd.DataFrame(scanRecord)
	if write_imaging_record:
		imageRecordsPath = os.path.join(eh.rootPath, 'imaging.csv')
		imageRecordExists = os.path.isfile(imageRecordsPath)
		with open(imageRecordsPath, 'a+') as ir:
			if imageRecordExists:
				scanRecordDF.to_csv(ir, header=False)
			else:
				scanRecordDF.to_csv(ir, header=True)

	if return_imaging_record:
		return scanRecordDF


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
		
		Args:
			None
			
		Returns:
			list: List of summed delays from a common reference time (0)
		
		"""
		referencedDelayTimes = [0]+self.delayTimes
		return np.cumsum(referencedDelayTimes).tolist()


	def __str__(self):
		"""Prints and returns a string representation of the kinetic acquisition parameters.
	
		Args:
			None

		Returns:
			str: KineticAcquisition parameters 
		"""
		
		paramVals = [self.device, 
					self.channelsExposures, 
					str(self.absTimes), 
					str(self.delayTimes), 
					self.note]
		params = 'Device Name: {}, Channels, Exposures: {}, \
					Referenced Times (s): {}, Delay Times (s): {}, Note: {}'.format(*paramVals)
		return '>> Kinetic Acquisition Parameters: {}'.format(params)


	def startAssay(self, data_dir, position_list, scanQueueFlag = False):
		"""Brings the stage home, schedules the scans, then starts the image acquisitions

		Args:
			data_dir (str): directory to write image folder
			post_list (pd.DataFrame): position list
			scanQueueFlag (bool): flag to add scan to the common scan queue
		
		Returns:
			None
		"""
		
		kineticSubfolder = '{}_{}'.format(time.strftime("%Y%m%d_%H%M%S", 
														time.localtime()), 
											self.note.replace(" ", "_")
											)
		kineticDirectory = os.path.join(data_dir, kineticSubfolder)
		os.makedirs(kineticDirectory)
			
		eh.acquilogger.info(self.__str__())
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
					args = [kineticDirectory, 
							self.channelsExposures, 
							self.device, 
							self.note.replace(" ", "_"), 
							position_list]
					kwargs = {}
					hardwareQueue.put((args, kwargs))
				else:
					scan(kineticDirectory, 
						self.channelsExposures, 
						self.device, 
						self.note.replace(" ", "_"), 
						position_list)
			else:
				time.sleep(deltaTime)
				lastScanTime = time.time()
				if scanQueueFlag == True:
					args = [kineticDirectory, 
							self.channelsExposures, 
							self.device, 
							self.note.replace(" ", "_"), 
							position_list]
					kwargs = {}
					hardwareQueue.put((args, kwargs))
				else:
					scan(kineticDirectory, 
						self.channelsExposures, 
						self.device, 
						self.note.replace(" ", "_"), 
						position_list)
		eh.acquilogger.info('Kinetic Read Complete')
