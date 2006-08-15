#! /usr/bin/env python
# encoding: utf-8
#Matthias Jahn <jahn.matthias@freenet.de> 2006
#Fam WatchMonitor depends on python-fam ... it works with fam or gamin demon
__revision__ = "0.1.0"
import os, sys, select, errno
try:
	import _fam
	support = True
except:
	support = False

class WatchMonitor:
	class WatchObject:
		def __init__(self, idxName, namePath, isDir, callBackThis, handleEvents):
			self.__fr = None
			self.__idxName = idxName
			self.__name = namePath
			self.__isDir = isDir
			self.__callBackThis = callBackThis
			self.__handleEvents = handleEvents
		
		def __del__(self):
			self.unwatch()
	
		def watch(self, watcher):
			if self.__fr != None:
				self.unwatch()
			if self.__isDir:
				self.__fr = watcher.monitorDirectory(self.__name, self.__idxName)
			else:
				self.__fr = watcher.monitorFile(self.__name, self.__idxName)
	
		def unwatch(self):
			if self.__fr == None:
				raise "fam not init"
			self.__fr.cancelMonitor()
		
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

	def __init__(self):
		self.__fam = None
		self.connect()
		self.__watcher = {}
		self.__loops = True
	
	def __del__ (self):
		self.disconnect()

	def __raise_disconnected(self):
		raise("Already disconnected")

	def connect(self):
		self.__fam = _fam.open()
	
	def disconnect(self):
		if  self.__fam != None:
			self.removeAllDirWatch()
			self.__fam.close()
		self.__fam = None;
	
	def addDirWatch(self, idxName, callBackThis, dirList, handleEvents = ['changed', 'deleted', 'created']):
		"""add dirList to watch.
		idxName: unique name for ref
		callBackThis: is called if something in dirs in dirlist has events (handleEvents)  
		callBackThis(idxName, changedFilePath)
		dirList: list of directories to watch
		handleEvents:  events to handle possible are 'changed', 'delete', 'create', 'exist'
			suspendDirWatch after a handled change
		"""
		self.removeDirWatch(idxName)
		self.__watcher[idxName] = []
		for directory in dirList:
			watchObject = self.WatchObject(idxName, os.path.abspath(directory), 1, callBackThis, handleEvents)
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
		if  self.__fam == None:
			self.connect()
		for watchObject in self.__watcher[idxName]:
			watchObject.watch(self.__fam)
	
	def resumeAllDirWatch(self):
		""" resume all DirWatcher"""
		for idxName in self.__watcher.keys():
			self.resumeAllDirWatch(idxName)

	def __processDirEvents(self, fe):
		if fe.code2str() in self.__watcher[fe.userData][0].getHandleEvents():
			self.suspendDirWatch(fe.userData)
			__watcher = self.__watcher[fe.userData][0]
			__watcher.getCallBackThis()(fe.userData, __watcher.getFullPath(fe.filename), fe.code2str())
			self.resumeDirWatch(fe.userData)
	
	def requestEndLoop(self):
		"""sets a flag that stops the loop. it do not stop the loop directly!"""
		self.__loops = False
		
	def loop(self):
		self.__loops = True
		while (self.__loops) and (self.__fam!= None) :
			try:
				ri, ro, re = select.select([self.__fam], [], [])
			except select.error, er:
				errnumber, strerr = er
				if errnumber == errno.EINTR:
					continue
				else:
					raise strerr
					sys.exit(1)
			while self.__fam.pending():
				fe = self.__fam.nextEvent()
				self.__processDirEvents(fe)
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
