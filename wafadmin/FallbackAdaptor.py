#! /usr/bin/env python
# encoding: utf-8
#Matthias Jahn <jahn.matthias@freenet.de> 2006
"""
Fallback WatchMonitor should work anywhere ..;-)
this do not depends on gamin or fam instead it polls for changes
it works at least under linux ... windows or other  *nix are untested
"""

import os, time
support = True

class Fallback:
	class Helper:
		def __init__(self, callBack, userdata):
			self.currentFiles = {}
			self.oldFiles = {}
			self.__firstRun = True
			self.callBack = callBack
			self.userdata = userdata

		def isFirstRun(self):
			if self.__firstRun:
				self.__firstRun = False
				return True
			else:
				return False

	def __init__(self):
		self.__dirs = {}
		#event lists for changed and deleted
		self.__changeLog = {}

	def __traversal(self, dirName):
		"""Traversal function for directories
Basic principle: all_files is a dictionary mapping paths to
modification times.  We repeatedly crawl through the directory
tree rooted at 'path', doing a stat() on each file and comparing
the modification time.
"""
		files = os.listdir(dirName)
		firstRun = self.__dirs[dirName].isFirstRun()

		for filename in files:
			path = os.path.join(dirName, filename)
			try:
				fileStat = os.stat(path)
			except os.error:
				# If a file has been deleted since the lsdir
				# scanning the directory and now, we'll get an
				# os.error here.  Just ignore it -- we'll report
				# the deletion on the next pass through the main loop.
				continue
			modifyTime = self.__dirs[dirName].oldFiles.get(path)
			if modifyTime is not None:
				# Record this file as having been seen
				del self.__dirs[dirName].oldFiles[path]
				# File's mtime has been changed since we last looked at it.
				if fileStat.st_mtime > modifyTime:
					self.__changeLog[path] = 'changed'
			else:
				if firstRun:
					self.__changeLog[path] = 'exists'
				else:
					# No recorded modification time, so it must be
					# a brand new file
					self.__changeLog[path] = 'created'
			# Record current mtime of file.
			self.__dirs[dirName].currentFiles[path] = fileStat.st_mtime

	def watch_directory(self, namePath, callBack, idxName):
		self.__dirs[namePath] = self.Helper(callBack, idxName)
		return self

	def unwatch_directory(self, namePath):
		if self.__dirs.get(namePath):
			del self.__dirs[namePath]

	def event_pending(self):
		for dirName in self.__dirs.keys():
			self.__dirs[dirName].oldFiles = self.__dirs[dirName].currentFiles.copy()
			self.__dirs[dirName].currentFiles = {}
			self.__traversal(dirName)
			for deletedFile in self.__dirs[dirName].oldFiles.keys():
				self.__changeLog[deletedFile] = 'deleted'
				del self.__dirs[dirName].oldFiles[deletedFile]
		return len(self.__changeLog)

	def handle_events(self):
		pathName = self.__changeLog.keys()[0]
		event = self.__changeLog[pathName]
		dirName = os.path.dirname(pathName)
		self.__dirs[dirName].callBack(pathName, event, self.__dirs[dirName].userdata)
		del self.__changeLog[pathName]

class WatchMonitor:
	class WatchObject:
		def __init__(self, idxName, name, isDir, callBackThis, handleEvents):
			self.__fr = None
			self.__idxName = idxName
			self.__name = name
			self.__isDir = isDir
			self.__callBackThis = callBackThis
			self.__handleEvents = handleEvents

		def __del__(self):
			self.unwatch()

		def watch(self, watcher, callBack):
			if self.__fr != None:
				self.unwatch()
			if self.__isDir:
				self.__fr = watcher.watch_directory(self.__name, callBack, self.__idxName)
			else:
				self.__fr = watcher.watch_file(self.__name, callBack, self.__idxName)

		def unwatch(self):
			if self.__fr == None:
				raise "fam not init"
			self.__fr.unwatch_directory(self.__name)

		def getHandleEvents(self):
			return self.__handleEvents

		def getCallBackThis(self):
			return self.__callBackThis

		def getIdxName(self):
			return self.__idxName

		def __str__(self):
			if self.__isDir:
				return 'DIR %s: ' % self.__name
			else:
				return 'FILE %s: ' % self.__name

	def __init__(self):
		self.__fallback = None
		self.connect()
		self.__watcher = {}
		self.__loops = True

	def __del__ (self):
		self.disconnect()

	def __raise_disconnected(self):
		raise("Already disconnected")

	def connect(self):
		self.__fallback = Fallback()

	def disconnect(self):
		if  self.__fallback != None:
			self.removeAllDirWatch()
		self.__fallback = None;

	def addDirWatch(self, idxName, callBack, dirList, handleEvents=['changed', 'deleted', 'created']):
		"""add dirList to watch.
		idxName: unique name for ref
		callBack: is called if something in dirs in dirlist has events (handleEvents)  
		callBack(idxName, changedFilePath)
		dirList: list of dirs to watch
		handleEvents:  events to handle possible are 'changed', 'delete', 'create', 'exist'
			suspendDirWatch after a handled change
		"""
		self.removeDirWatch(idxName)
		self.__watcher[idxName] = []
		for directory in dirList:
			watchObject = self.WatchObject(idxName, os.path.abspath(directory), 1, callBack, handleEvents)
			self.__watcher[idxName].append(watchObject)
		self.resumeDirWatch(idxName)

	def removeDirWatch(self, idxName):
		"""remove DirWatch with name idxName"""
		if self.__watcher.has_key(idxName):
			self.suspendDirWatch(idxName)
			del self.__watcher[idxName]

	def removeAllDirWatch(self):
		"""remove all DirWatcher"""
		self.__watcher = {}

	def suspendDirWatch(self, idxName):
		"""suspend DirWatch with name idxName. No dir/filechanges will be reacted until resume"""
		if self.__watcher.has_key(idxName):
			for watchObject in self.__watcher[idxName]:
				watchObject.unwatch()

	def suspendAllDirWatch(self):
		"""suspend all DirWatcher ... they could be resumed with resumeAllDirWatch"""
		for idxName in self.__watcher.keys():
			self.suspendDirWatch(idxName)

	def resumeDirWatch(self, idxName):
		"""resume a DirWatch that was supended with suspendDirWatch or suspendAllDirWatch"""
		if  self.__fallback == None:
			self.connect()
		for watchObject in self.__watcher[idxName]:
			watchObject.watch(self.__fallback, self.__processDirEvents)

	def resumeAllDirWatch(self):
		""" resume all DirWatcher"""
		for idxName in self.__watcher.keys():
			self.resumeDirWatch(idxName)

	def __processDirEvents(self, pathName, event, idxName):
		if event in self.__watcher[idxName][0].getHandleEvents():
			self.suspendDirWatch(idxName)
			#self.__loops=False
			#print "name \"%s\", file: %s, event: %s"%(idxName, pathName, event)
			self.__watcher[idxName][0].getCallBackThis()(idxName, pathName, event)
			self.resumeDirWatch(idxName)

	def requestEndLoop(self):
		"""sets a flag that stops the loop. it do not stop the loop directly!"""
		self.__loops = False

	def loop(self):
		self.__loops = True
		while (self.__loops) and (self.__fallback != None) :
			time.sleep(1)
			while self.__fallback.event_pending():
				self.__fallback.handle_events()
				if not self.__loops:
					break

class Test:
	def __init__(self):
		self.fam_test = WatchMonitor()
		self.fam_test.addDirWatch("tmp Test", self.thisIsCalledBack, ["/tmp"])
		self.fam_test.loop()
		self.fam_test.loop()

	def thisIsCalledBack(self, idxName, pathName, event):
		print "idxName=%s, Path=%s, Event=%s " % (idxName, pathName, event)
		self.fam_test.resumeDirWatch(idxName)

if __name__ == "__main__":
	Test()

