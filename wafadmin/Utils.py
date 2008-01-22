#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Utility functions"

import os, sys, imp, types, string, time
import Params

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

# TODO DEPRECATED: to be removed in waf 1.4
def waf_version(mini = "0.0.1", maxi = "100.0.0"):
	"throws an exception if the waf version is wrong"
	min_lst = map(int, mini.split('.'))
	max_lst = map(int, maxi.split('.'))
	waf_lst = map(int, Params.g_version.split('.'))

	mm = min(len(min_lst), len(waf_lst))
	for (a, b) in zip(min_lst[:mm], waf_lst[:mm]):
		if a < b:
			break
		if a > b:
			Params.fatal("waf version should be at least %s (%s found)" % (mini, Params.g_version))

	mm = min(len(max_lst), len(waf_lst))
	for (a, b) in zip(max_lst[:mm], waf_lst[:mm]):
		if a > b:
			break
		if a < b:
			Params.fatal("waf version should be at most %s (%s found)" % (maxi, Params.g_version))

def reset():
	import Params, Object, Node
	Params.g_build = None
	Object.g_allobjs = []
	Node.g_launch_node = None

def to_list(sth):
	if type(sth) is types.ListType:
		return sth
	else:
		return sth.split()

def options(**kwargs):
	pass

g_loaded_modules = {}
"index modules by absolute path"

g_module=None
"the main module is special"

def load_module(file_path, name='wscript'):
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

	import Common
	d = module.__dict__
	d['install_files'] = Common.install_files
	d['install_as'] = Common.install_as
	d['symlink_as'] = Common.symlink_as

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
	tbl = {}
	lst = s.split('\n')
	for line in lst:
		if not line: continue
		mems = line.split('=')
		tbl[mems[0]] = mems[1]
	return tbl

try:
	import struct, fcntl, termios
except ImportError:
	def get_term_cols():
		return 55
else:
	def get_term_cols():
		dummy_lines, cols = struct.unpack("HHHH", \
		fcntl.ioctl(sys.stdout.fileno(),termios.TIOCGWINSZ , \
		struct.pack("HHHH", 0, 0, 0, 0)))[:2]
		return cols


def progress_line(state, total, col1, col2):
	n = len(str(total))

	global g_ind, g_ind_idx
	g_ind_idx += 1
	ind = g_ind[g_ind_idx % 4]

	if hasattr(Params.g_build, 'ini'):
		ini = Params.g_build.ini
	else:
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
	"Split path into components. Supports UNC paths on Windows"
	if sys.platform != 'win32':
		if not path: return ['']
		x = path.split('/')
		if path[0] == '/': x = ['/']+x[1:]
		return x
	h,t = os.path.splitunc(path)
	if not h: return __split_dirs(t)
	return [h] + __split_dirs(t)[1:]
	return __split_dirs(path)

def __split_dirs(path):
	h,t = os.path.split(path)
	if not h: return [t]
	if h == path: return [h]
	if not t: return __split_dirs(h)
	else: return __split_dirs(h) + [t]

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

class UndefinedType(object):
	def __repr__(self):
		return 'Undefined'

Undefined = UndefinedType()
"""Special value to denote an explicitly undefined name"""

