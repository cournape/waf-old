#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn 2006
# rewritten by Thomas Nagy 2009

"""
This tool is supposed to help starting a new build as soon as something changes
in the build directory.

PyInotify, Fam, Gamin or time-threshold are used for the detection

For now only PyInotify and time threshold are supported
"""

import select, errno, os, time
import Utils, Scripting, Logs, Build, Node

w_pyinotify = w_fam = w_gamin = None
def check_support():
	global w_pyinotify, w_fam, w_gamin
	try:
		import pyinotify as w_pyinotify
	except ImportError:
		w_pyinotify = None
	else:
		try:
			wm = w_pyinotify.WatchManager()
			wm = w_pyinotify.Notifier(wm)
			wm = None
		except:
			raise
			w_pyinotify = None

	try:
		import gamin as w_gamin
	except ImportError:
		w_gamin = None
	else:
		try:
			test = w_gamin.WatchMonitor()
			test.disconnect()
			test = None
		except:
			w_gamin = None

	try:
		import _fam as w_fam
	except ImportError:
		w_fam = None
	else:
		try:
			test = w_fam.open()
			test.close()
			test = None
		except:
			w_fam = None

def daemon(ctx):
	"""waf command: rebuild as soon as something changes"""
	bld = None
	while True:
		try:
			bld = Utils.g_module.build_context()
			Scripting.build(bld)
		except Build.BuildError, e:
			Logs.warn(e)
		except KeyboardInterrupt:
			Utils.pprint('RED', 'interrupted')
			break

		try:
			x = ctx.state
		except AttributeError:
			setattr(ctx, 'state', DirWatch())
			x = ctx.state

		x.wait(bld)

def set_options(opt):
	"""So this shows how to add new commands from tools"""
	Utils.g_module.__dict__['daemon'] = daemon

class DirWatch(object):
	def __init__(self):
		check_support()
		if w_pyinotify:
			self.sup = 'pyinotify'
		elif w_gamin:
			self.sup = 'gamin'
		elif w_fam:
			self.sup = 'fam'
		else:
			self.sup = 'dumb'
		#self.sup = 'dumb'

	def wait(self, bld):
		return getattr(self.__class__, 'wait_' + self.sup)(self, bld)

	def enumerate(self, node):
		yield node.abspath()
		for x in node.childs.values():
			if x.id & 3 == Node.DIR:
				for k in self.enumerate(x):
					yield k
		raise StopIteration

	def wait_pyinotify(self, bld):

		class PE(w_pyinotify.ProcessEvent):
			def stop(self, event):
				self.notif.ev = True
				self.notif.stop()
				raise ValueError("stop for delete")

			process_IN_DELETE = stop
			process_IN_CLOSE = stop
			process_default = stop

		proc = PE()
		wm = w_pyinotify.WatchManager()
		notif = w_pyinotify.Notifier(wm, proc)
		proc.notif = notif

		# well, we should add all the folders to watch here
		for x in self.enumerate(bld.srcnode):
			wm.add_watch(x, w_pyinotify.IN_DELETE | w_pyinotify.IN_CLOSE_WRITE)

		try:
			# pyinotify uses an infinite loop ... not too nice, so we have to use an exception
			notif.loop()
		except ValueError:
			pass
		if not hasattr(notif, 'ev'):
			raise KeyboardInterrupt

	def wait_dumb(self, bld):
		time.sleep(5)


# TODO: all the code below

g_dirwatch = None
g_daemonlock = 0


def call_back(idxName, pathName, event):
	#print "idxName=%s, Path=%s, Event=%s "%(idxName, pathName, event)
	# check the daemon lock state
	global g_daemonlock
	if g_daemonlock: return
	g_daemonlock = 1

	try:
		main()
	except Utils.WafError, e:
		error(e)
	g_daemonlock = 0

def start_daemon():
	"if it does not exist already:start a new directory watcher; else: return immediately"
	global g_dirwatch
	if not g_dirwatch:
		g_dirwatch = DirectoryWatcher()
		dirs=[]
		for nodeDir in Build.bld.srcnode.dirs():
			tmpstr = "%s" %nodeDir
			tmpstr = "%s" %(tmpstr[6:])
			dirs.append(tmpstr)
		g_dirwatch.add_watch("tmp Test", call_back, dirs)
		# infinite loop, no need to exit except on ctrl+c
		g_dirwatch.loop()
		g_dirwatch = None
	else:
		g_dirwatch.suspend_all_watch()
		dirs=[]
		for nodeDir in Build.bld.srcnode.dirs():
			tmpstr = "%s" % nodeDir
			tmpstr = "%s" % (tmpstr[6:])
			dirs.append(tmpstr)
		g_dirwatch.add_watch("tmp Test", call_back, dirs)



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
		global module
		if not module:
			check_support()
		if module is None:
			self._adaptor = FallbackAdaptor(self._processDirEvents)
		if not module:
			self._adaptor = FallbackAdaptor(self._processDirEvents)
		elif module.__name__ == "fam":
			self._adaptor = FamAdaptor(self._processDirEvents)
		elif module.__name__ == "gamin":
			self._adaptor = GaminAdaptor(self._processDirEvents)
		else:
			self._adaptor = FallbackAdaptor(self._processDirEvents)

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

class adaptor(object):
	def __init__(self, event_handler):
		self.event_handler = event_handler
		self.watch_handler = {}

	def __del__(self):
		if self.data:
			for handle in self.watch_handler.keys():
				self.stop_watch(handle)

	def event_pending(self):
		self.check_init()
		return self.data.event_pending()

	def watch_directory(self, name, idxName):
		self.check_init()
		if self.watch_handler.has_key(name):
			raise "dir already watched"
		self.watch_handler[name] = self.watch_directory(name, idxName)
		return self.watch_handler[name]

	def watch_file(self, name, idxName):
		self.check_init()
		if self.watch_handler.has_key(name):
			raise "file already watched"
		self.watch_handler[name] = self.do_watch_file(name, idxName)
		return self.watch_handler[name]

	def stop_watch(self, name):
		self.check_init()
		if self.watch_handler.has_key(name):
			self.do_stop_watch(name)
			del self.watch_handler[name]
		return None

	def handle_events(self):
		self.check_init()
		self.data.handle_events()

	def check_init(self):
		if not self.data:
			raise OSError, "Adapter not initialized"

## FAM #############################################################

class FamAdaptor(adaptor):
	def __init__(self, event_handler):
		adaptor.__init__(self, event_handler)
		global module
		self.data = module.open()

	def __del__(self):
		adaptor.__del__(self)
		if self.data: self.data.close()

	def do_add_watch_dir(self, name, idx_name):
		return self.data.monitorDirectory(name, idxName)

	def do_add_watch_file(self, name, idx_name):
		return self.data.monitorFile(name, idxName)

	def do_stop_watch(self, name):
		self.watch_handler[name].cancelMonitor()

	def wait_for_event(self):
		self.check_init()
		try:
			select.select([self.data], [], [])
		except select.error, er:
			errnumber, strerr = er
			if errnumber != errno.EINTR:
				raise strerr

	def handle_events(self):
		"override the default"
		self.check_init()
		fe = self.data.nextEvent()
		#pathName, event, idxName
		self._eventHandler(fe.filename, fe.code2str(), fe.userData)

## GAMIN #############################################################

class GaminAdaptor(adaptor):
	def __init__(self, eventHandler):
		adaptor.__init__(self, event_handler)
		global module
		self.data = module.WatchMonitor()

	def __del__(self):
		adaptor.__del__(self)
		if self.data: self.data.disconnect()

	def check_init(self):
		"""is gamin connected"""
		if self._gamin == None:
			raise "gamin not init"

	def _code2str(self, event):
		"""convert event numbers to string"""
		gaminCodes = {
			1:"changed",
			2:"deleted",
			3:"StartExecuting",
			4:"StopExecuting",
			5:"created",
			6:"moved",
			7:"acknowledge",
			8:"exists",
			9:"endExist"
		}
		try:
			return gaminCodes[event]
		except KeyError:
			return "unknown"

	def _eventhandler_helper(self, pathName, event, idxName):
		"""local eventhandler helps to convert event numbers to string"""
		self._eventHandler(pathName, self._code2str(event), idxName)

	def do_add_watch_dir(self, name, idx_name):
		return self.data.watch_directory(name, self._eventhandler_helper, idxName)

	def do_add_watch_file(self, name, idx_name):
		return self.data.watch_directory(name, self._eventhandler_helper, idxName)

	def do_stop_watch(self, name):
		self.data.stop_watch(name)

	def wait_for_event(self):
		self.check_init()
		try:
			select.select([self._gamin.get_fd()], [], [])
		except select.error, er:
			errnumber, strerr = er
			if errnumber != errno.EINTR:
				raise strerr

class FallbackAdaptor(adaptor):
	def __init__(self, event_handler):
		adaptor.__init__(self, event_handler)
		self.data = Fallback()

	def do_add_watch_dir(self, name, idx_name):
		return self.data.watch_directory(name, self._eventHandler, idxName)

	def do_add_watch_file(self, name, idx_name):
		return self.data.watch_directory(name, self._eventHandler, idxName)

	def do_stop_watch(self, name):
		self.data.unwatch_directory(name)

	def wait_for_event(self):
		self.check_init()
		time.sleep(1)


## Fallback #############################################################

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

"""
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
"""
