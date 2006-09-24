#! /usr/bin/env python
# encoding: utf-8
# Matthias Jahn <jahn.matthias@freenet.de>, 2006

"DirWatch chooses a supported backend (fam, gamin or fallback) it is mainly a wrapper script without own methods beside this"

from Params import debug

class WatchObject:
	def __init__(self, idxName, name, isDir, callBackThis, handleEvents):
		self.__fr = None
		self.__idxName = idxName
		self.__name = name
		self.__isDir = isDir
		self.__callBackThis = callBackThis
		self.__handleEvents = handleEvents
		self.__watcher = None

	def __del__(self):
		self.unwatch()

	def getHandleEvents(self):
		return self.__handleEvents

	def getCallBackThis(self):
		return self.__callBackThis

	def getFullPath(self, fileName):
		return os.path.join(self.__name, fileName)

	def getIdxName(self):
		return self.__idxName

	def __str__(self):
		if self.__isDir:
			return 'DIR %s: ' %  self.__name
		else:
			return 'FILE %s: ' % self.__name

import GaminAdaptor, FamAdaptor, FallbackAdaptor

class DirectoryWatcher:
	"""DirWatch chooses a supported backend (fam, gamin or fallback)
	it is mainly a wrapper script without own methods beside this
	"""
	def __init__(self):
		if FamAdaptor.support:
			debug("using FamAdaptor")
			self.__adapter = FamAdaptor.WatchMonitor()
		elif GaminAdaptor.support:
			debug("using GaminAdaptor")
			self.__adapter = GaminAdaptor.WatchMonitor()
		else:
			debug("using FallbackAdaptor")
			self.__adapter = FallbackAdaptor.WatchMonitor()

	def addDirWatch(self, idxName, callBackThis, dirList, handleEvents=['changed', 'deleted', 'created']):
		"""add dirList to watch.
		@param idxName: unique name for ref
		@param callBackThis: is called if something in dirs in dirlist has events (handleEvents) callBackThis(idxName, changedFilePath)
		@param dirList: list of dirs to watch
		@param handleEvents: events to handle possible are 'changed', 'deleted', 'created', 'exist' suspendDirWatch after a handled change
		"""
		self.__adapter.addDirWatch(idxName, callBackThis, dirList, handleEvents)

	def removeDirWatch(self, idxName):
		"""remove DirWatch with name idxName"""
		self.__adapter.removeDirWatch(idxName)

	def removeAllDirWatch(self):
		"""remove all DirWatcher"""
		self.__adapter.removeAllDirWatch()

	def suspendDirWatch(self, idxName):
		"""suspend DirWatch with name idxName. No dir/filechanges will be reacted until resume"""
		self.__adapter.suspendDirWatch(idxName)

	def suspendAllDirWatch(self):
		"""suspend all DirWatcher ... they could be resumed with resumeAllDirWatch"""
		self.__adapter.suspendAllDirWatch()

	def resumeDirWatch(self, idxName):
		"""resume a DirWatch that was supended with suspendDirWatch or suspendAllDirWatch"""
		self.__adapter.resumeDirWatch(idxName)

	def resumeAllDirWatch(self):
		""" resume all DirWatcher"""
		self.__adapter.resumeAllDirWatch()

	def loop(self):
		"""wait for dir events and start handling of them"""
		try:
			self.__adapter.loop()
		except KeyboardInterrupt:
			self.requestEndLoop()

	def requestEndLoop(self):
		"""sets a flag that stops the loop. it do not stop the loop directly!"""
		self.__adapter.requestEndLoop()

class Test:
	def __init__(self):
		self.fam_test = DirectoryWatcher()
		self.fam_test.addDirWatch("tmp Test", self.thisIsCalledBack, ["/tmp"])
		self.fam_test.loop()
		self.fam_test.loop()

	def thisIsCalledBack(self, idxName, pathName, event):
		print "idxName=%s, Path=%s, Event=%s " % (idxName, pathName, event)
		self.fam_test.resumeDirWatch(idxName)

if __name__ == "__main__":
	Test()

