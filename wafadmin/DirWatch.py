#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn <jahn.matthias@freenet.de>, 2006

"DirWatch chooses a supported backend (fam, gamin or fallback) it is mainly a wrapper script without own methods beside this"

from Params import debug
import GaminAdaptor, FamAdaptor, FallbackAdaptor
import os

class WatchObject:
	def __init__(self, idxName, namePath, isDir, callBackThis, handleEvents):
		"""watch object to handle a watch
		@param idxName: unique name for ref
		@param dirList: path to watch
		@param isDir: directory True or False
		@param callBackThis: is called if something in dirs in dirlist has events (handleEvents) callBackThis(idxName, changedFilePath)
		@param handleEvents: events to handle possible are 'changed', 'deleted', 'created', 'exist' suspendDirWatch after a handled change
		"""
		self._adaptor = None
		self._fr = None
		self._idxName = idxName
		self._name = namePath
		self._isDir = isDir
		self._callBackThis = callBackThis
		self._handleEvents = handleEvents

	def __del__(self):
		self.unwatch()

	def watch(self, adaptor):
		"""start watching
		@param adaptor: dirwatch adaptor for backend
		"""
		self._adaptor = adaptor
		if self._fr != None:
			self.unwatch()
		if self._isDir:
			self._fr = self._adaptor.watch_directory(self._name, self._idxName)
		else:
			self._fr = self._adaptor.watch_file(self._name, self._idxName)

	def unwatch(self):
		"""stop watching"""
		if self._fr:
			self._fr = self._adaptor.stop_watch(self._name)

	def get_events(self):
		"""returns all events to care"""
		return self._handleEvents

	def get_callback(self):
		"""returns the callback methode"""
		return self._callBackThis

	def get_fullpath(self, fileName):
		"""returns the full path dir + filename"""
		return os.path.join(self._name, fileName)

	def __str__(self):
		if self._isDir:
			return 'DIR %s: ' % self._name
		else:
			return 'FILE %s: ' % self._name

class DirectoryWatcher:
	"""DirWatch chooses a supported backend (fam, gamin or fallback)
	it is mainly a wrapper script without own methods beside this
	"""
	def __init__(self):
		self._adaptor = None
		self._watcher = {}
		self._loops = True
		self.connect()

	def __del__ (self):
		self.disconnect()

	def _raise_disconnected(self):
		raise "Already disconnected"

	def disconnect(self):
		if self._adaptor:
			self.suspend_all_watch()
		self._adaptor = None

	def connect(self):
		if self._adaptor:
			self.disconnect()
		if FamAdaptor.support:
			debug("using FamAdaptor")
			self._adaptor = FamAdaptor.FamAdaptor(self._processDirEvents)
			if self._adaptor == None:
				raise "something is strange"
		elif GaminAdaptor.support:
			debug("using GaminAdaptor")
			self._adaptor = GaminAdaptor.GaminAdaptor(self._processDirEvents)
		else:
			debug("using FallbackAdaptor")
			self._adaptor = FallbackAdaptor.FallbackAdaptor(self._processDirEvents)

	def add_watch(self, idxName, callBackThis, dirList, handleEvents = ['changed', 'deleted', 'created']):
		"""add dirList to watch.
		@param idxName: unique name for ref
		@param callBackThis: is called if something in dirs in dirlist has events (handleEvents) callBackThis(idxName, changedFilePath)
		@param dirList: list of dirs to watch
		@param handleEvents: events to handle possible are 'changed', 'deleted', 'created', 'exist' suspendDirWatch after a handled change
		"""
		self.remove_watch(idxName)
		self._watcher[idxName] = []
		for directory in dirList:
			watchObject = WatchObject(idxName, os.path.abspath(directory), 1, callBackThis, handleEvents)
			self._watcher[idxName].append(watchObject)
		self.resume_watch(idxName)

	def remove_watch(self, idxName):
		"""remove DirWatch with name idxName"""
		if self._watcher.has_key(idxName):
			self.suspend_watch(idxName)
			del self._watcher[idxName]

	def remove_all_watch(self):
		"""remove all DirWatcher"""
		self._watcher = {}

	def suspend_watch(self, idxName):
		"""suspend DirWatch with name idxName. No dir/filechanges will be reacted until resume"""
		if self._watcher.has_key(idxName):
			for watchObject in self._watcher[idxName]:
				watchObject.unwatch()

	def suspend_all_watch(self):
		"""suspend all DirWatcher ... they could be resumed with resume_all_watch"""
		for idxName in self._watcher.keys():
			self.suspend_watch(idxName)

	def resume_watch(self, idxName):
		"""resume a DirWatch that was supended with suspendDirWatch or suspendAllDirWatch"""
		for watchObject in self._watcher[idxName]:
			watchObject.watch(self._adaptor)

	def resume_all_watch(self):
		""" resume all DirWatcher"""
		for idxName in self._watcher.keys():
			self.resume_watch(idxName)

	def _processDirEvents(self, pathName, event, idxName):
		if event in self._watcher[idxName][0].get_events():
			#self.disconnect()
			self.suspend_watch(idxName)
			_watcher = self._watcher[idxName][0]
			_watcher.get_callback()(idxName, _watcher.get_fullpath(pathName), event)
			#self.connect()
			self.resume_watch(idxName)

	def request_end_loop(self):
		"""sets a flag that stops the loop. it do not stop the loop directly!"""
		self._loops = False

	def loop(self):
		"""wait for dir events and start handling of them"""
		try:
			self._loops = True
			while self._loops and self._adaptor != None:
				self._adaptor.wait_for_event()
				while self._adaptor.event_pending():
					self._adaptor.handle_events()
					if not self._loops:
						break
		except KeyboardInterrupt:
			self.request_end_loop()

if __name__ == "__main__":
	class Test:
		def __init__(self):
			self.fam_test = DirectoryWatcher()
			self.fam_test.add_watch("tmp Test", self.thisIsCalledBack, ["/tmp"])
			self.fam_test.loop()
#			self.fam_test.loop()

		def thisIsCalledBack(self, idxName, pathName, event):
			print "idxName=%s, Path=%s, Event=%s " % (idxName, pathName, event)
			self.fam_test.resume_watch(idxName)

	Test()

