#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn <jahn.matthias@freenet.de> 2006

"""Fam WatchMonitor depends on python-fam ... it works with fam or gamin demon"""


import select, errno
try:
	import _fam
except ImportError:
	support = False
else:
	# check if fam runs and accepts connections
	test = _fam.open()
	test.close()
	test = None
	support = True

import DirWatch

class FamAdaptor(DirWatch.adaptor):
	def __init__(self, event_handler):
		DirWatch.adaptor.__init__(self, event_handler)

		self._fam = _fam.open()
		self._watchHandler = {} # {name : famId}

	def __del__(self):
		if self._fam:
			for handle in self._watchHandler.keys():
				self.stop_watch(handle)
			self._fam.close()

	def check_init(self):
		if self._fam == None:
			raise "fam not init"

	def watch_directory(self, name, idxName):
		self.check_init()
		if self._watchHandler.has_key(name):
			raise "dir already watched"
		# set famId
		self._watchHandler[name] = self._fam.monitorDirectory(name, idxName)
		return self._watchHandler[name]

	def watch_file(self, name, idxName):
		self.check_init()
		if self._watchHandler.has_key(name):
			raise "file already watched"
		# set famId
		self._watchHandler[name] = self._fam.monitorFile(name, idxName)
		return self._watchHandler[name]

	def stop_watch(self, name):
		self.check_init()
		if self._watchHandler.has_key(name):
			self._watchHandler[name].cancelMonitor()
			del self._watchHandler[name]
		return None

	def wait_for_event(self):
		self.check_init()
		try:
			select.select([self._fam], [], [])
		except select.error, er:
			errnumber, strerr = er
			if errnumber != errno.EINTR:
				raise strerr

	def event_pending(self):
		self.check_init()
		return self._fam.pending()

	def handle_events(self):
		self.check_init()
		fe = self._fam.nextEvent()
		#pathName, event, idxName
		self._eventHandler(fe.filename, fe.code2str(), fe.userData)

