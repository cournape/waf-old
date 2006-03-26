#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, md5, types, sys, string, stat, imp
import Params

g_trace=1
g_debug=1
g_error=1

def error(msg):
	Params.niceprint(msg, 'ERROR', 'Configuration')

def h_md5_file(filename):
	f = file(filename,'rb')
	m = md5.new()
	readBytes = 1024 # read 1024 bytes per time
	while (readBytes):
		readString = f.read(readBytes)
		m.update(readString)
		readBytes = len(readString)
	f.close()
	return m.hexdigest()

def h_md5_str(str):
	m = md5.new()
	m.update( str )
	return m.hexdigest()

def h_md5_lst(lst):
	m = md5.new()
	for el in lst: m.update(str(el))
	return m.hexdigest()

# --

def h_simple_file(filename):
	f = file(filename,'rb')
	s = f.read().__hash__()
	f.close()
	return s
	#return os.stat(filename).st_mtime

def h_simple_str(str):
	return str.__hash__()

def h_simple_lst(lst):
	val = reduce( lambda a,b : a.__hash__() ^ b.__hash__(), ['']+lst )
	return val+1

def reset():
	import Deptree, Object, Node, Task

	Deptree.reset()
	Object.reset
	Node.reset()
	Task.reset()

	import Params
	Params.g_rootname = "" # might be c: (without '\')
	Params.g_dbfile='.dblite'
	Params.g_default_env=None
	Params.g_excludes = ['.svn', 'scons-local-0.96.91', 'cache', '{arch}', '.arch-ids']
	Params.g_pattern_excludes = ['_build_']

	Params.g_outstanding_objs=[]
	Params.g_posted_objs = []
	
	Params.g_tasks_done  = []

	Params.g_build    = None
	
	Params.g_maxjobs = 1
	
	Params.g_inroot = 1
	Params.g_curdirnode = None
	Params.g_subdirs=[]
	Params.g_srcnode = None
	Params.g_startnode = None

	Params.g_scanned_folders=[]

def options(**kwargs):
	pass

# === part below is borrowed from scons === #
DictType        = types.DictType
InstanceType    = types.InstanceType
ListType        = types.ListType
StringType      = types.StringType

def is_Dict(obj):
	t = type(obj)
	return t is DictType or (t is InstanceType and isinstance(obj, UserDict))

def is_List(obj):
	t = type(obj)
	return t is ListType or (t is InstanceType and isinstance(obj, UserList))

if hasattr(types, 'UnicodeType'):
	def is_String(obj):
		t = type(obj)
		return t is StringType or t is UnicodeType or (t is InstanceType and isinstance(obj, UserString))
else:
	def is_String(obj):
		t = type(obj)
		return t is StringType or (t is InstanceType and isinstance(obj, UserString))

if sys.platform == 'win32':
	def where_is(file, path=None, pathext=None, reject=[]):
		if path is None:
			try:
				path = os.environ['PATH']
			except KeyError:
				return None
		if is_String(path):
			path = string.split(path, os.pathsep)
		if pathext is None:
			try:
				pathext = os.environ['PATHEXT']
			except KeyError:
				pathext = '.COM;.EXE;.BAT;.CMD'
		if is_String(pathext):
			pathext = string.split(pathext, os.pathsep)
		for ext in pathext:
			if string.lower(ext) == string.lower(file[-len(ext):]):
				pathext = ['']
				break
		if not is_List(reject):
			reject = [reject]
		for dir in path:
			f = os.path.join(dir, file)
			for ext in pathext:
				fext = f + ext
				if os.path.isfile(fext):
					try: reject.index(fext)
					except ValueError: return os.path.normpath(fext)
					continue
		return None

elif sys.platform == 'cygwin':
	def where_is(file, path=None, pathext=None, reject=[]):
		if path is None:
			try:
				path = os.environ['PATH']
				print path
			except KeyError:
				return None
		if is_String(path):
			path = string.split(path, os.pathsep)
		if pathext is None:
			pathext = ':.exe:.sh'
		if is_String(pathext):
			pathext = string.split(pathext, os.pathsep)
		for ext in pathext:
			if string.lower(ext) == string.lower(file[-len(ext):]):
				pathext = ['']
				break
		if not is_List(reject):
			reject = [reject]
		for dir in path:
			f = os.path.join(dir, file)
			for ext in pathext:
				fext = f + ext
				if os.path.isfile(fext):
					try: reject.index(fext)
					except ValueError: return os.path.normpath(fext)
					continue
		return None

else:
	def where_is(file, path=None, pathext=None, reject=[]):
		if path is None:
			try: path = os.environ['PATH']
			except KeyError: return None
		if is_String(path):
			path = string.split(path, os.pathsep)
		if not is_List(reject):
			reject = [reject]
		for d in path:
			f = os.path.join(d, file)
			if os.path.isfile(f):
				try:
					st = os.stat(f)
				except OSError:
					# os.stat() raises OSError, not IOError if the file
					# doesn't exist, so in this case we let IOError get
					# raised so as to not mask possibly serious disk or
					# network issues.
					continue
				if stat.S_IMODE(st[stat.ST_MODE]) & 0111:
					try: reject.index(f)
					except ValueError: return os.path.normpath(f)
					continue
		return None

## index modules by absolute path
g_loaded_modules={}
## the main module is special
g_module=None

# this function requires an absolute path
def load_module(file_path, name='wscript'):
	try: return g_loaded_modules[file_path]
	except: pass

	module = imp.new_module(name)

	file = open(file_path, 'r')
	code = file.read()

	exec code in module.__dict__
	if file: file.close()

	g_loaded_modules[file_path] = module

	return module

def set_main_module(file_path):
	# Load custom options, if defined
	global g_module
	g_module = load_module(file_path, 'wscript_main')
	
	# remark: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

def fetch_options(file_path):
	import Options
	# Load custom options, if defined
	file = open(file_path, 'r')
	name = 'wscript'
	desc = ('', 'U', 1)

	module = imp.load_module(file_path, file, name, desc)
	try:
		Options.g_custom_options.append(module.set_options)
	finally:
		if file: file.close()

