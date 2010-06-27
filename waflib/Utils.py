#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"""
Utilities and cross-platform fixes.
"""

import os, sys, errno, traceback, inspect, re, shutil, datetime, gc, subprocess
from collections import deque # do not touch
from waflib import Errors

try:
	from collections import UserDict
except:
	from UserDict import UserDict

try:
	from hashlib import md5
except:
	try:
		from md5 import md5
	except:
		# never fail to enable fixes from another module
		pass

try:
	import threading
except:
	# broken platforms
	class threading(object):
		pass
	class Lock(object):
		def acquire(self):
			pass
		def release(self):
			pass
	threading.Lock = threading.Thread = Lock
else:
	run_old = threading.Thread.run
	def run(*args, **kwargs):
		try:
			run_old(*args, **kwargs)
		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			sys.excepthook(*sys.exc_info())
	threading.Thread.run = run

SIG_NIL = b'iluvcuteoverload'
"""if you change the hash type, do not forget to change SIG_NIL"""

O644 = 420
"""permission for regular files"""

O755 = 493
"""permission for executable files"""

try:
	from collections import defaultdict
except ImportError:
	# defaultdict was introduced in python 2.5
	class defaultdict(dict):
		def __init__(self, default_factory):
			super(defaultdict, self).__init__()
			self.default_factory = default_factory
		def __getitem__(self, key):
			try:
				return super(defaultdict, self).__getitem__(key)
			except KeyError:
				value = self.default_factory()
				self[key] = value
				return value

is_win32 = sys.platform == 'win32'
indicator = is_win32 and '\x1b[A\x1b[K%s%s%s\r' or '\x1b[K%s%s%s\r'

def readf(fname, m='r'):
	"""
	Read an entire file into a string.
	@type  fname: string
	@param fname: Path to file
	@type  m: string
	@param m: Open mode
	@rtype: string
	@return: Content of the file
	"""
	f = open(fname, m)
	try:
		txt = f.read()
	finally:
		f.close()
	return txt

def h_file(filename):
	f = open(filename, 'rb')
	m = md5()
	while (filename):
		filename = f.read(100000)
		m.update(filename)
	f.close()
	return m.digest()

try:
	x = ''.encode('hex')
except:
	import binascii
	def to_hex(s):
		ret = binascii.hexlify(s)
		if not isinstance(ret, str):
			ret = ret.decode('utf-8')
		return ret
else:
	def to_hex(s):
		return s.encode('hex')

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

def exec_command(s, **kw):
	"""
	@param s: args for subprocess.Popen
	@param log: logger for suppressing the output at configuration time
	"""
	if 'log' in kw:
		kw['stdout'] = kw['stderr'] = kw['log']
		del(kw['log'])
	kw['shell'] = isinstance(s, str)

	try:
		proc = subprocess.Popen(s, **kw)
		return proc.wait()
	except OSError:
		return -1

if is_win32:
	def exec_command(s, **kw):
		if 'log' in kw:
			kw['stdout'] = kw['stderr'] = kw['log']
			del(kw['log'])
		kw['shell'] = isinstance(s, str)

		if isinstance(s, str) and len(s) > 2000:
			startupinfo = subprocess.STARTUPINFO()
			startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
			kw['startupinfo'] = startupinfo

		try:
			proc = subprocess.Popen(s,**kw)
			return proc.wait()
		except OSError:
			return -1

listdir = os.listdir
if is_win32:
	def listdir_win32(s):

		if not s:
			return []

		if re.match('^[A-Za-z]:$', s):
			# os.path.isdir fails if s contains only the drive name... (x:)
			s += os.sep
		if not os.path.isdir(s):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		return os.listdir(s)
	listdir = listdir_win32

def num2ver(ver):
	"""
	convert a string, tuple or version number into an integer
	"""
	if isinstance(ver, str):
		ver = tuple(ver.split('.'))
	if isinstance(ver, tuple):
		ret = 0
		for i in xrange(len(ver)):
			ret += 256**(2 - i) * int(ver[i])
		return ret
	return ver

def ex_stack():
	exc_type, exc_value, tb = sys.exc_info()
	exc_lines = traceback.format_exception(exc_type, exc_value, tb)
	return ''.join(exc_lines)

def to_list(sth):
	"""
	Convert a string argument to a list by splitting on spaces, and pass
	through a list argument unchanged.

	@param sth: List or a string of items separated by spaces
	@rtype: list
	@return: Argument converted to list
	"""
	if isinstance(sth, str):
		return sth.split()
	else:
		return sth

def to_hashtable(s):
	"""
	Parse a string with key = value pairs into a dictionary.
	@type  s: string
	@param s: String to parse
	@rtype: dict
	@return: Dictionary containing parsed key-value pairs
	"""
	tbl = {}
	lst = s.split('\n')
	for line in lst:
		if not line: continue
		mems = line.split('=')
		tbl[mems[0]] = mems[1]
	return tbl

rot_chr = ['\\', '|', '/', '-']
"List of characters to use when displaying the throbber"
rot_idx = 0
"Index of the current throbber character"

def split_path(path):
	return path.split('/')

def split_path_cygwin(path):
	if path.startswith('//'):
		ret = path.split('/')[2:]
		ret[0] = '/' + ret[0]
		return ret
	return path.split('/')

re_sp = re.compile('[/\\\\]')
def split_path_win32(path):
	if path.startswith('\\\\'):
		ret = re.split(re_sp, path)[2:]
		ret[0] = '\\' + ret[0]
		return ret
	return re.split(re_sp, path)

if sys.platform == 'cygwin':
	split_path = split_path_cygwin
elif is_win32:
	split_path = split_path_win32

def copy_attrs(orig, dest, names, only_if_set=False):
	for a in to_list(names):
		u = getattr(orig, a, ())
		if u or not only_if_set:
			setattr(dest, a, u)

def check_dir(path):
	"""
	Ensure that a directory exists, and try to avoid thread issues (similar to mkdir -p)
	@type  dir: string
	@param dir: Path to directory
	"""
	if not os.path.isdir(path):
		try:
			os.makedirs(path)
		except OSError as e:
			if not os.path.isdir(path):
				raise Errors.WafError('Cannot create folder %r (original error: %r)' % (path, e))

def def_attrs(cls, **kw):
	'''
	set attributes for class.
	@param cls [any class]: the class to update the given attributes in.
	@param kw [dictionary]: dictionary of attributes names and values.

	if the given class hasn't one (or more) of these attributes, add the attribute with its value to the class.
	'''
	for k, v in kw.items():
		if not hasattr(cls, k):
			setattr(cls, k, v)

def quote_define_name(s):
	"""
	Convert a string to an identifier suitable for C defines.
	@type  s: string
	@param s: String to convert
	@rtype: string
	@return: Identifier suitable for C defines
	"""
	fu = re.compile("[^a-zA-Z0-9]").sub("_", s)
	fu = fu.upper()
	return fu

def quote_whitespace(path):
	return (path.strip().find(' ') > 0 and '"%s"' % path or path).replace('""', '"')

def trimquotes(s):
	if not s: return ''
	s = s.rstrip()
	if s[0] == "'" and s[-1] == "'": return s[1:-1]
	return s

def h_list(lst):
	"""Hash a list."""
	m = md5()
	m.update(str(lst).encode())
	return m.digest()

def h_fun(fun):
	"""Get the source of a function for hashing."""
	try:
		return fun.code
	except AttributeError:
		try:
			h = inspect.getsource(fun)
		except IOError:
			h = "nocode"
		try:
			fun.code = h
		except AttributeError:
			pass
		return h

def cmd_output(cmd, **kw):
	"""
	Execute a command and return its output as a string.
	@param cmd: Command line or list of arguments for subprocess.Popen
	@rtype: string
	@return: Command output or throws a WafError
	"""
	if 'log' in kw:
		kw['log'].write('command: %s\n' % cmd)

	args = {}
	args['shell'] = isinstance(cmd, str)
	args['stderr'] = args['stdout'] = subprocess.PIPE
	if 'env' in kw:
		args['env'] = kw['env']

	try:
		p = subprocess.Popen(cmd, **args)
		(out, err) = p.communicate()
	except Exception as e:
		try:
			kw['log'].write(str(err))
		except:
			pass
		raise Errors.WafError('execution failure %r' % e)

	if 'log' in kw:
		if out:
			kw['log'].write('out: %r\n' % out)
		if err:
			kw['log'].write('err: %r\n' % err)

	if not isinstance(out, str):
		out = out.decode('utf-8')

	if p.returncode:
		e = Errors.WafError('command %r returned %r' % (cmd, p.returncode))
		e.returncode = p.returncode
		raise e
	return out

reg_subst = re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr, params):
	"""
	Replaces ${VAR} with the value of VAR taken from the dictionary
	@type  expr: string
	@param expr: String to perform substitution on
	@param params: Dictionary to look up variable values.
	"""
	def repl_var(m):
		if m.group(1):
			return '\\'
		if m.group(2):
			return '$'
		try:
			# ConfigSet instances may contain lists
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var, expr)

def unversioned_sys_platform_to_binary_format(unversioned_sys_platform):
	"""
	Get the binary format based on the unversioned platform name.
	"""
	if unversioned_sys_platform in ('linux', 'freebsd', 'netbsd', 'openbsd', 'sunos', 'gnu'):
		return 'elf'
	elif unversioned_sys_platform == 'darwin':
		return 'mac-o'
	elif unversioned_sys_platform in ('win32', 'cygwin', 'uwin', 'msys'):
		return 'pe'
	# TODO we assume all other operating systems are elf, which is not true.
	# we may set this to 'unknown' and have ccroot and other tools handle
	# the case "gracefully" (whatever that means).
	return 'elf'

def unversioned_sys_platform():
	"""
	Get the unversioned platform name.
	Some Python platform names contain versions, that depend on
	the build environment, e.g. linux2, freebsd6, etc.
	This returns the name without the version number. Exceptions are
	os2 and win32, which are returned verbatim.
	@rtype: string
	@return: Unversioned platform name
	"""
	s = sys.platform
	if s == 'java':
		# The real OS is hidden under the JVM.
		from java.lang import System
		s = System.getProperty('os.name')
		# see http://lopica.sourceforge.net/os.html for a list of possible values
		if s == 'Mac OS X':
			return 'darwin'
		elif s.startswith('Windows '):
			return 'win32'
		elif s == 'OS/2':
			return 'os2'
		elif s == 'HP-UX':
			return 'hpux'
		elif s in ('SunOS', 'Solaris'):
			return 'sunos'
		else: s = s.lower()
	if s == 'win32' or s.endswith('os2') and s != 'sunos2': return s
	return re.split('\d+$', s)[0]

def job_count():
	"""
	Amount of threads to use
	"""
	count = int(os.environ.get('JOBS', 0))
	if count < 1:
		if sys.platform == 'win32':
			# on Windows, use the NUMBER_OF_PROCESSORS environmental variable
			count = int(os.environ.get('NUMBER_OF_PROCESSORS', 1))
		else:
			# on everything else, first try the POSIX sysconf values
			if hasattr(os, 'sysconf_names'):
				if 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
					count = int(os.sysconf('SC_NPROCESSORS_ONLN'))
				elif 'SC_NPROCESSORS_CONF' in os.sysconf_names:
					count = int(os.sysconf('SC_NPROCESSORS_CONF'))
			else:
				tmp = cmd_output(['sysctl', '-n', 'hw.ncpu'])
				if re.match('^[0-9]+$', tmp):
					count = int(tmp)
	if count < 1:
		count = 1
	elif count > 1024:
		count = 1024
	return count

def nada(*k, **kw):
	"""A function that does nothing."""
	pass

def diff_path(top, subdir):
	"""difference between two absolute paths"""
	top = os.path.normpath(top).replace('\\', '/').split('/')
	subdir = os.path.normpath(subdir).replace('\\', '/').split('/')
	if len(top) == len(subdir): return ''
	diff = subdir[len(top) - len(subdir):]
	return os.path.join(*diff)

class Timer(object):
	"""
	Simple object for timing the execution of commands.
	Its string representation is the current time.
	"""
	def __init__(self):
		self.start_time = datetime.datetime.utcnow()

	def __str__(self):
		delta = datetime.datetime.utcnow() - self.start_time
		days = int(delta.days)
		hours = int(delta.seconds / 3600)
		minutes = int((delta.seconds - hours * 3600) / 60)
		seconds = delta.seconds - hours * 3600 - minutes * 60 + float(delta.microseconds) / 1000 / 1000
		result = ''
		if days:
			result += '%dd' % days
		if days or hours:
			result += '%dh' % hours
		if days or hours or minutes:
			result += '%dm' % minutes
		return '%s%.3fs' % (result, seconds)

if is_win32:
	old = shutil.copy2
	def copy2(src, dst):
		old(src, dst)
		shutil.copystat(src, src)
	setattr(shutil, 'copy2', copy2)

if os.name == 'java':
	# For Jython (they should really fix the inconsistency)
	try:
		gc.disable()
		gc.enable()
	except NotImplementedError:
		gc.disable = gc.enable

def read_la_file(path):
	"""untested, used by msvc.py, unclosed file risk"""
	sp = re.compile(r'^([^=]+)=\'(.*)\'$')
	dc = {}
	file = open(path, "r")
	for line in file.readlines():
		try:
			_, left, right, _ = sp.split(line.strip())
			dc[left] = right
		except ValueError:
			pass
	file.close()
	return dc

def nogc(fun):
	def f(*k, **kw):
		try:
			gc.disable()
			ret = fun(*k, **kw)
		finally:
			gc.enable()
		return ret
	return f

