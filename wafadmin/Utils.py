#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Utility functions"

import os, sys, imp, types, string, time, errno, inspect
from UserDict import UserDict
import Params
from Constants import *

try:
	from fnv import new as md5
except ImportError:
	try:
		import hashlib
		md5 = hashlib.md5
	except ImportError:
		import md5
		md5 = md5.md5

g_trace = 0
g_debug = 0
g_error = 0

g_ind_idx = 0
g_ind = ['\\', '|', '/', '-']
"the rotation thing"

def test_full():
	try:
		f=open('.waf-full','w')
		f.write('test')
		f.close()
		os.unlink('.waf-full')
	except IOError, e:
		import errno
		if e.errno == errno.ENOSPC:
			Params.fatal('filesystem full', e.errno)
		else:
			Params.fatal(str(e), e.errno)

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
	"throws an exception if the waf version is wrong"
	ver = HEXVERSION
	try: min_val = mini + 0
	except TypeError: min_val = int(mini.replace('.', '0'), 16)

	if min_val > ver:
		Params.fatal("waf version should be at least %s (%x found)" % (mini, ver))

	try: max_val = maxi + 0
	except TypeError: max_val = int(maxi.replace('.', '0'), 16)

	if max_val < ver:
		Params.fatal("waf version should be at most %s (%x found)" % (maxi, ver))

def python_24_guard():
	if sys.hexversion<0x20400f0:
		raise ImportError,"Waf requires Python >= 2.3 but the raw source requires Python 2.4"

def reset():
	import Params, TaskGen, Environment
	Params.g_build = None
	TaskGen.g_allobjs = []
	Environment.g_cache_max = {}

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
		Params.fatal('The file %s could not be opened!' % file_path)

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

def progress_line(state, total, col1, col2):
	n = len(str(total))

	global g_ind, g_ind_idx
	g_ind_idx += 1
	ind = g_ind[g_ind_idx % 4]

	try:
		ini = Params.g_build.ini
	except AttributeError:
		ini = Params.g_build.ini = time.time()

	pc = (100.*state)/total
	eta = time.strftime('%H:%M:%S', time.gmtime(time.time() - ini))
	fs = "[%%%dd/%%%dd][%%s%%2d%%%%%%s][%s][" % (n, n, ind)
	left = fs % (state, total, col1, pc, col2)
	right = '][%s%s%s]' % (col1, eta, col2)

	cols = get_term_cols() - len(left) - len(right) + 2*len(col1) + 2*len(col2)
	if cols < 7: cols = 7

	ratio = int((cols*state)/total) - 1

	bar = ('='*ratio+'>').ljust(cols)
	msg = Params.g_progress % (left, bar, right)

	return msg

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

def hash_fun(fun):
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

