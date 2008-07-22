#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Utilities, the stable ones are the following:

* h_file: compute a unique value for a file (hash), it uses
  the module fnv if it is installed (see waf/utils/fnv & http://code.google.com/p/waf/wiki/FAQ)
  else, md5 (see the python docs)

  For large projects (projects with more than 15000 files) it is possible to use
  a hashing based on the path and the size (may give broken cache results)

	import stat
	def h_file(filename):
		st = os.stat(filename)
		if stat.S_ISDIR(st[stat.ST_MODE]): raise IOError, 'not a file'
		m = md5()
		m.update(str(st.st_mtime))
		m.update(str(st.st_size))
		m.update(filename)
		return m.digest()

    To replace the function in your project, use something like this:
	import Utils
	Utils.h_file = h_file

* h_list
* h_fun
* get_term_cols
* ordered_dict

"""

import os, sys, imp, types, string, errno, traceback, inspect
from UserDict import UserDict
import Logs, pproc
from Constants import *

class WafError(Exception):
	def __init__(self, message):
		self.message = message
		self.stack = traceback.extract_stack()
		Exception.__init__(self, self.message)
	def __str__(self):
		return self.message

class WscriptError(WafError):
	def __init__(self, message, wscript_file=None):
		self.message = ''

		if wscript_file:
			self.wscript_file = wscript_file
			self.wscript_line = None
		else:
			(self.wscript_file, self.wscript_line) = self.locate_error()

		if self.wscript_file:
			self.message += "%s:" % self.wscript_file
			if self.wscript_line:
				self.message += "%s:" % self.wscript_line
		self.message += " error: %s" % message
		WafError.__init__(self, self.message)

	def locate_error(self):
		stack = traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name = os.path.basename(frame[0])
			is_wscript = (file_name == WSCRIPT_FILE or file_name == WSCRIPT_BUILD_FILE)
			if is_wscript:
				return (frame[0], frame[1])
		return (None, None)

indicator = sys.platform=='win32' and '\x1b[A\x1b[K%s%s%s\r' or '\x1b[K%s%s%s\r'

try:
	from fnv import new as md5
	import Constants
	Constants.SIG_NIL = 'signofnv'

	def h_file(filename):
		m = md5()
		try:
			m.hfile(filename)
			x = m.digest()
			if x is None: raise OSError, "not a file"
			return x
		except SystemError:
			raise OSError, "not a file"+filename

except ImportError:
	try:
		from hashlib import md5
	except ImportError:
		from md5 import md5

	def h_file(filename):
		f = file(filename,'rb')
		m = md5()
		readBytes = 100000
		while (readBytes):
			readString = f.read(readBytes)
			m.update(readString)
			readBytes = len(readString)
		f.close()
		return m.digest()

class ordered_dict(UserDict):
	def __init__(self, dict = None):
		self.allkeys = []
		UserDict.__init__(self, dict)

	def __delitem__(self, key):
		self.allkeys.remove(key)
		UserDict.__delitem__(self, key)

	def __setitem__(self, key, item):
		if key not in self.allkeys: self.allkeys.append(key)
		UserDict.__setitem__(self, key, item)

listdir = os.listdir
if sys.platform == "win32":
	def listdir_win32(s):
		if not os.path.isdir(s):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		return os.listdir(s)
	listdir = listdir_win32

def waf_version(mini = 0x010000, maxi = 0x100000):
	"Halts if the waf version is wrong"
	ver = HEXVERSION
	try: min_val = mini + 0
	except TypeError: min_val = int(mini.replace('.', '0'), 16)

	if min_val > ver:
		Logs.error("waf version should be at least %s (%s found)" % (mini, ver))
		sys.exit(0)

	try: max_val = maxi + 0
	except TypeError: max_val = int(maxi.replace('.', '0'), 16)

	if max_val < ver:
		Logs.error("waf version should be at most %s (%s found)" % (maxi, ver))
		sys.exit(0)

def python_24_guard():
	if sys.hexversion<0x20400f0:
		raise ImportError,"Waf requires Python >= 2.3 but the raw source requires Python 2.4"

def to_list(sth):
	if type(sth) is types.ListType:
		return sth
	else:
		return sth.split()

g_loaded_modules = {}
"index modules by absolute path"

g_module=None
"the main module is special"

def load_module(file_path, name=WSCRIPT_FILE):
	"this function requires an absolute path"
	try:
		return g_loaded_modules[file_path]
	except KeyError:
		pass

	module = imp.new_module(name)

	try:
		file = open(file_path, 'r')
	except (IOError, OSError):
		raise WscriptError('The file %s could not be opened!' % file_path)

	module_dir = os.path.dirname(file_path)
	sys.path.insert(0, module_dir)
	exec file in module.__dict__
	sys.path.remove(module_dir)
	if file: file.close()

	g_loaded_modules[file_path] = module

	return module

def set_main_module(file_path):
	"Load custom options, if defined"
	global g_module
	g_module = load_module(file_path, 'wscript_main')

	# remark: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

def to_hashtable(s):
	"used for importing env files"
	tbl = {}
	lst = s.split('\n')
	for line in lst:
		if not line: continue
		mems = line.split('=')
		tbl[mems[0]] = mems[1]
	return tbl

def get_term_cols():
	"console width"
	return 80
try:
	import struct, fcntl, termios
except ImportError:
	pass
else:
	if sys.stdout.isatty():
		def myfun():
			dummy_lines, cols = struct.unpack("HHHH", \
			fcntl.ioctl(sys.stdout.fileno(),termios.TIOCGWINSZ , \
			struct.pack("HHHH", 0, 0, 0, 0)))[:2]
			return cols
		# we actually try the function once to see if it is suitable
		try:
			myfun()
		except IOError:
			pass
		else:
			get_term_cols = myfun

rot_idx = 0
rot_chr = ['\\', '|', '/', '-']
"the rotation thing"

def split_path(path):
	if not path: return ['']
	return path.split('/')

if sys.platform == 'win32':
	def split_path(path):
		h,t = os.path.splitunc(path)
		if not h: return __split_dirs(t)
		return [h] + __split_dirs(t)[1:]

	def __split_dirs(path):
		h,t = os.path.split(path)
		if not h: return [t]
		if h == path: return [h.replace('\\', '')]
		if not t: return __split_dirs(h)
		else: return __split_dirs(h) + [t]

def copy_attrs(orig, dest, names, only_if_set=False):
	for a in to_list(names):
		u = getattr(orig, a, ())
		if u or not only_if_set:
			setattr(dest, a, u)

_quote_define_name_translation = None
"lazily construct a translation table for mapping invalid characters to valid ones"

def quote_define_name(path):
	"Converts a string to a constant name, foo/zbr-xpto.h -> FOO_ZBR_XPTO_H"
	global _quote_define_name_translation
	if _quote_define_name_translation is None:
		invalid_chars = [chr(x) for x in xrange(256)]
		for valid in string.digits + string.uppercase: invalid_chars.remove(valid)
		_quote_define_name_translation = string.maketrans(''.join(invalid_chars), '_'*len(invalid_chars))

	return string.translate(string.upper(path), _quote_define_name_translation)

def quote_whitespace(path):
	return (path.strip().find(' ') > 0 and '"%s"' % path or path).replace('""', '"')

def trimquotes(s):
	if not s: return ''
	s = s.rstrip()
	if s[0] == "'" and s[-1] == "'": return s[1:-1]
	return s

def h_list(lst):
	m = md5()
	m.update(str(lst))
	return m.digest()

def h_fun(fun):
	try:
		return fun.code
	except AttributeError:
		try:
			hh = inspect.getsource(fun)
		except IOError:
			hh = "nocode"
		try:
			fun.code = hh
		except AttributeError:
			pass
		return hh

_hash_blacklist_types = (
	types.BuiltinFunctionType,
	types.ModuleType,
	types.FunctionType,
	types.ClassType,
	types.TypeType,
	types.NoneType,
	)

def hash_function_with_globals(prevhash, func):
	"""
	hash a function (object) and the global vars needed from outside
	ignore unhashable global variables (lists)

	prevhash: previous hash value to be combined with this one;
	if there is no previous value, zero should be used here

	func: a Python function object.
	"""
	assert type(func) is types.FunctionType
	for name, value in func.func_globals.iteritems():
		if type(value) in _hash_blacklist_types:
			continue
		if isinstance(value, type):
			continue
		try:
			prevhash = hash( (prevhash, name, value) )
		except TypeError: # raised for unhashable elements
			pass
		#else:
		#	print "hashed: ", name, " => ", value, " => ", hash(value)
	return hash( (prevhash, inspect.getsource(func)) )

def pprint(col, str, label=''):
	"print messages in color"
	print "%s%s%s %s" % (Logs.colors(col), str, Logs.colors.NORMAL, label)

def check_dir(dir):
	"""If a folder doesn't exists, create it."""
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError, e:
			raise WafError("Cannot create folder '%s' (original error: %s)" % (dir, e))

def cmd_output(cmd):
	p = pproc.Popen(to_list(cmd), stdout=pproc.PIPE)
	output = p.communicate()[0]
	if p.returncode:
		msg = "command execution failed: %s -> %r" % (cmd, str(output))
		raise ValueError, msg
	return output

