#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn <jahn.matthias@freenet.de> 2006

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
			self._firstRun = True
			self.callBack = callBack
			self.userdata = userdata

		def isFirstRun(self):
			if self._firstRun:
				self._firstRun = False
				return True
			else:
				return False

	def __init__(self):
		self._dirs = {}
		#event lists for changed and deleted
		self._changeLog = {}

	def _traversal(self, dirName):
		"""Traversal function for directories
Basic principle: all_files is a dictionary mapping paths to
modification times.  We repeatedly crawl through the directory
tree rooted at 'path', doing a stat() on each file and comparing
the modification time.
"""
		files = os.listdir(dirName)
		firstRun = self._dirs[dirName].isFirstRun()

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
			modifyTime = self._dirs[dirName].oldFiles.get(path)
			if modifyTime is not None:
				# Record this file as having been seen
				del self._dirs[dirName].oldFiles[path]
				# File's mtime has been changed since we last looked at it.
				if fileStat.st_mtime > modifyTime:
					self._changeLog[path] = 'changed'
			else:
				if firstRun:
					self._changeLog[path] = 'exists'
				else:
					# No recorded modification time, so it must be
					# a brand new file
					self._changeLog[path] = 'created'
			# Record current mtime of file.
			self._dirs[dirName].currentFiles[path] = fileStat.st_mtime

	def watch_directory(self, namePath, callBack, idxName):
		self._dirs[namePath] = self.Helper(callBack, idxName)
		return self

	def unwatch_directory(self, namePath):
		if self._dirs.get(namePath):
			del self._dirs[namePath]

	def event_pending(self):
		for dirName in self._dirs.keys():
			self._dirs[dirName].oldFiles = self._dirs[dirName].currentFiles.copy()
			self._dirs[dirName].currentFiles = {}
			self._traversal(dirName)
			for deletedFile in self._dirs[dirName].oldFiles.keys():
				self._changeLog[deletedFile] = 'deleted'
				del self._dirs[dirName].oldFiles[deletedFile]
		return len(self._changeLog)

	def handle_events(self):
		pathName = self._changeLog.keys()[0]
		event = self._changeLog[pathName]
		dirName = os.path.dirname(pathName)
		self._dirs[dirName].callBack(pathName, event, self._dirs[dirName].userdata)
		del self._changeLog[pathName]

class FallbackAdaptor:
	def __init__(self, eventHandler):
		self._fallback = Fallback()
		self._eventHandler = eventHandler # callBack function
		self._watchHandler = {} # {name : famId}

	def __del__(self):
		if self._fallback:
			for handle in self._watchHandler.keys():
				self.stop_watch(handle)
			self._fallback = None

	def _check_fallback(self):
		if self._fallback == None:
			raise "fallback not init"

	def watch_directory(self, name, idxName):
		self._check_fallback()
		if self._watchHandler.has_key(name):
			raise "dir already watched"
		# set famId
		self._watchHandler[name] = self._fallback.watch_directory(name, self._eventHandler, idxName)
		return self._watchHandler[name]

	def watch_file(self, name, idxName):
		self._check_fallback()
		if self._watchHandler.has_key(name):
			raise "file already watched"
		# set famId
		self._watchHandler[name] = self._fallback.watch_directory(name, self._eventHandler, idxName)
		return self._watchHandler[name]

	def stop_watch(self, name):
		self._check_fallback()
		if self._watchHandler.has_key(name):
			self._fallback.unwatch_directory(name)
			del self._watchHandler[name]
		return None

	def wait_for_event(self):
		self._check_fallback()
		time.sleep(1)

	def event_pending(self):
		self._check_fallback()
		return self._fallback.event_pending()

	def handle_events(self):
		self._check_fallback()
		self._fallback.handle_events()

