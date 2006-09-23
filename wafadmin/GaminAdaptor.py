#! /usr/bin/env python
# encoding: utf-8
# Oscar Blumberg 2006 (nael)
# Matthias Jahn <jahn.matthias@freenet.de>

"""Depends on python gamin and on gamin demon"""

import os, sys, select, errno
import DirWatch
try:
	import gamin
	support = True
except:
	support = False

class WatchObjGamin(DirWatch.WatchObject):
	def watch(self, watcher, callBack=None):
		if self.__fr != None:
			self.unwatch()
		if self.__isDir:
			self.__watcher = watcher
			self.__fr = watcher.watch_directory(self.__name, callBack, self.__idxName)
		else:
			self.__fr = watcher.watch_file(self.__name, callBack, self.__idxName)
	def unwatch(self):
		if self.__watcher == None: raise "gamin not init"
		self.__watcher.stop_watch(self.__name)

class WatchMonitor:
	def __init__(self):
		if support == False:
			raise "gamin not supported"
		self.__gamin = None
		self.connect()
		self.__watcher = {}
		self.__loops = True

	def __del__ (self):
		self.disconnect()
		self.removeAllDirWatch()

	def __raise_disconnected(self):
		raise("Already disconnected")

	def connect(self):
		self.__gamin = gamin.WatchMonitor()

	def disconnect(self):
		if  self.__gamin != None:
			self.suspendAllDirWatch()
			self.__gamin.disconnect()
		self.__gamin = None;

	def addDirWatch(self, idxName, callBackThis, dirList, handleEvents=['changed', 'deleted', 'created']):
		self.removeDirWatch(idxName)
		self.__watcher[idxName] = []
		for directory in dirList:
			watchObject = WatchObjGamin(idxName, os.path.abspath(directory), 1, callBackThis, handleEvents)
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
		if  self.__gamin == None:
			self.connect()
		for watchObject in self.__watcher[idxName]:
			watchObject.watch(self.__gamin, self.__processDirEvents)

	def resumeAllDirWatch(self):
		""" resume all DirWatcher"""
		for idxName in self.__watcher.keys():
			self.resumeDirWatch(idxName)

	def __code2str(self, event):
		gaminCodes = {
			1: "changed",
			2: "deleted",
			3: "StartExecuting",
			4: "StopExecuting",
			5: "created",
			6: "moved",
			7: "acknowledge",
			8: "exists",
			9: "endExist"
		}
		try:
			return gaminCodes[event]
		except:
			return "unknown"

	def __processDirEvents(self, pathName, event, idxName):
		if self.__code2str(event) in self.__watcher[idxName][0].getHandleEvents():
			self.disconnect()
			__watcher = self.__watcher[idxName][0]
			__watcher.getCallBackThis()(idxName, __watcher.getFullPath(pathName), self.__code2str(event))
			self.connect()
			self.resumeDirWatch(idxName)

	def requestEndLoop(self):
		"""sets a flag that stops the loop. it do not stop the loop directly!"""
		self.__loops = False

	def loop(self):
		self.__loops = True
		while (self.__loops) and (self.__gamin != None) :
			try:
				ri, ro, re = select.select([self.__gamin.get_fd()], [], [])
			except select.error, er:
				errnumber, strerr = er
				if errnumber == errno.EINTR:
					continue
				else:
					raise strerr
					sys.exit(1)
			while self.__gamin.event_pending():
				self.__gamin.handle_events()
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
		self.fam_test.resumeAllDirWatch()

if __name__ == "__main__":
	Test()

