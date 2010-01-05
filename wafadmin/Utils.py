#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"""
Utilities and cross-platform fixes.
"""

"""
Utilities, the stable ones are the following:

* h_file: compute a unique value for a file (hash), it uses
  the module fnv if it is installed (see waf/utils/fnv & http://code.google.com/p/waf/wiki/FAQ)
  else, md5 (see the python docs)

  For large projects (projects with more than 15000 files) or slow hard disks and filesystems (HFS)
  it is possible to use a hashing based on the path and the size (may give broken cache results)
  The method h_file MUST raise an OSError if the file is a folder

	import stat
	def h_file(filename):
		st = os.stat(filename)
		if stat.S_ISDIR(st[stat.ST_MODE]): raise IOError('not a file')
		m = Utils.md5()
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

import os, sys, imp, string, errno, traceback, inspect, re, shutil, datetime, gc

# In python 3.0 we can get rid of all this
try: from UserDict import UserDict
except ImportError: from collections import UserDict
if sys.hexversion >= 0x2060000 or os.name == 'java':
	import subprocess as pproc
else:
	import pproc
import Logs
from Constants import *

try:
	from collections import deque
except ImportError:
	class deque(list):
		def popleft(self):
			return self.pop(0)

is_win32 = sys.platform == 'win32'

try:
	# defaultdict in python 2.5
	from collections import defaultdict as DefaultDict
except ImportError:
	class DefaultDict(dict):
		def __init__(self, default_factory):
			super(DefaultDict, self).__init__()
			self.default_factory = default_factory
		def __getitem__(self, key):
			try:
				return super(DefaultDict, self).__getitem__(key)
			except KeyError:
				value = self.default_factory()
				self[key] = value
				return value

class WafError(Exception):
	"""
	Base class for all Waf-specific exceptions.
	"""
	def __init__(self, *args):
		self.args = args
		try:
			self.stack = traceback.extract_stack()
		except:
			pass
		Exception.__init__(self, *args)
	def __str__(self):
		return str(len(self.args) == 1 and self.args[0] or self.args)

class WscriptError(WafError):
	"""
	Exception raised when an error is encountered in user code (wscript).
	@type  message: string
	@param message: Message intended for the user
	@type  wscript_file: string
	@param wscript_file: Absolute path of wscript where the error happened
	"""
	def __init__(self, message, wscript_file=None):
		if wscript_file:
			self.wscript_file = wscript_file
			self.wscript_line = None
		else:
			try:
				(self.wscript_file, self.wscript_line) = self.locate_error()
			except:
				(self.wscript_file, self.wscript_line) = (None, None)

		msg_file_line = ''
		if self.wscript_file:
			msg_file_line = "%s:" % self.wscript_file
			if self.wscript_line:
				msg_file_line += "%s:" % self.wscript_line
		err_message = "%s error: %s" % (msg_file_line, message)
		WafError.__init__(self, err_message)

	def locate_error(self):
		"""
		Locate the line in wscript on which the error happened,
		based on the stack trace.
		"""
		stack = traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name = os.path.basename(frame[0])
			is_wscript = (file_name == WSCRIPT_FILE or file_name == WSCRIPT_BUILD_FILE)
			if is_wscript:
				return (frame[0], frame[1])
		return (None, None)

indicator = is_win32 and '\x1b[A\x1b[K%s%s%s\r' or '\x1b[K%s%s%s\r'

try:
	from fnv import new as md5
	import Constants
	Constants.SIG_NIL = 'signofnv'

	def h_file(filename):
		m = md5()
		try:
			m.hfile(filename)
			x = m.digest()
			if x is None: raise OSError("not a file")
			return x
		except SystemError:
			raise OSError("not a file" + filename)

except ImportError:
	try:
		from hashlib import md5
	except ImportError:
		from md5 import md5

	def h_file(filename):
		f = open(filename, 'rb')
		m = md5()
		while (filename):
			filename = f.read(100000)
			m.update(filename)
		f.close()
		return m.digest()

class ordered_dict(UserDict):
	"""
	Dictionary with well-defined ordering. Each item is stored in a dictionary
	as well as a list.
	"""
	def __init__(self, dict = None):
		"""
		Ordered dictionary constructor.
		@type  dict: dict
		@param dict: Dictionary to copy (optional)
		"""
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
	Execute a command and wait until it completes. Accepts the command
	either as a list of arguments or as a full command line.
	@param s: Command list or list of command arguments
	@param log: ??
	"""
	if 'log' in kw:
		kw['stdout'] = kw['stderr'] = kw['log']
		del(kw['log'])
	kw['shell'] = isinstance(s, str)

	try:
		proc = pproc.Popen(s, **kw)
		return proc.wait()
	except OSError:
		return -1

if is_win32:
	def exec_command(s, **kw):
		if 'log' in kw:
			kw['stdout'] = kw['stderr'] = kw['log']
			del(kw['log'])
		kw['shell'] = isinstance(s, str)

		if len(s) > 2000:
			startupinfo = pproc.STARTUPINFO()
			startupinfo.dwFlags |= pproc.STARTF_USESHOWWINDOW
			kw['startupinfo'] = startupinfo

		try:
			if 'stdout' not in kw:
				kw['stdout'] = pproc.PIPE
				kw['stderr'] = pproc.PIPE
				proc = pproc.Popen(s,**kw)
				(stdout, stderr) = proc.communicate()
				Logs.info(stdout)
				if stderr:
					Logs.error(stderr)
				return proc.returncode
			else:
				proc = pproc.Popen(s,**kw)
				return proc.wait()
		except OSError:
			return -1

listdir = os.listdir
if is_win32:
	def listdir_win32(s):
		if re.match('^[A-Za-z]:$', s):
			# os.path.isdir fails if s contains only the drive name... (x:)
			s += os.sep
		if not os.path.isdir(s):
			e = OSError()
			e.errno = errno.ENOENT
			raise e
		return os.listdir(s)
	listdir = listdir_win32

def waf_version(mini = 0x010000, maxi = 0x100000):
	"""
	Halt execution if the version of Waf is not in the range.

	Versions should be supplied as hex. 0x01000000 means 1.0.0,
	0x010408 means 1.4.8, etc.

	@type  mini: number
	@param mini: Minimum required version
	@type  maxi: number
	@param maxi: Maximum allowed version
	"""
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
	"""
	Abort if running on an old (< 2.4) version of Python.
	"""
	if sys.hexversion<0x20400f0:
		raise ImportError("Waf requires Python >= 2.3 but the raw source requires Python 2.4")

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

g_loaded_modules = {}
"""
Dictionary holding already loaded modules, keyed by their absolute path.
"""

g_module=None
"""
Currently executing module.
"""

def load_module(file_path, name=WSCRIPT_FILE):
	"""
	Load a Python source file containing user code.
	@type  file_path: string
	@param file_path: Directory of the python file
	@type  name: string
	@param name: Basename of file with user code (default: "wscript")
	@rtype: module
	@return: Loaded Python module
	"""
	try:
		return g_loaded_modules[file_path]
	except KeyError:
		pass

	module = imp.new_module(name)

	try:
		code = readf(file_path, m='rU')
	except (IOError, OSError):
		raise WscriptError('Could not read the file %r' % file_path)

	module.waf_hash_val = code

	module_dir = os.path.dirname(file_path)
	sys.path.insert(0, module_dir)
	try:
		exec(code, module.__dict__)
	except Exception, e:
		try:
			raise WscriptError(traceback.format_exc(), file_path)
		except:
			raise e
	sys.path.remove(module_dir)

	g_loaded_modules[file_path] = module

	return module

def set_main_module(file_path):
	"Load custom options, if defined"
	global g_module
	g_module = load_module(file_path, 'wscript_main')
	g_module.root_path = file_path

	# note: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

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

def get_term_cols():
	"""
	Get console width in characters.
	@rtype: number
	@return: Number of characters per line
	"""
	return 80

# If console packages are available, replace the dummy function with a real
# implementation
try:
	import struct, fcntl, termios
except ImportError:
	pass
else:
	if Logs.got_tty:
		def get_term_cols_real():
			dummy_lines, cols = struct.unpack("HHHH", \
			fcntl.ioctl(sys.stderr.fileno(),termios.TIOCGWINSZ , \
			struct.pack("HHHH", 0, 0, 0, 0)))[:2]
			return cols
		# we actually try the function once to see if it is suitable
		try:
			get_term_cols_real()
		except IOError:
			pass
		else:
			get_term_cols = get_term_cols_real

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

def def_attrs(cls, **kw):
	'''
	set attributes for class.
	@param cls [any class]: the class to update the given attributes in.
	@param kw [dictionary]: dictionary of attributes names and values.

	if the given class hasn't one (or more) of these attributes, add the attribute with its value to the class.
	'''
	for k, v in kw.iteritems():
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
	m.update(str(lst))
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

def pprint(col, str, label='', sep=os.linesep):
	"print messages in color"
	sys.stderr.write("%s%s%s %s%s" % (Logs.colors(col), str, Logs.colors.NORMAL, label, sep))

def check_dir(dir):
	"""
	Ensure that a directory exists. Equivalent to mkdir -p.
	@type  dir: string
	@param dir: Path to directory
	"""
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError, e:
			raise WafError("Cannot create folder '%s' (original error: %s)" % (dir, e))

def cmd_output(cmd, **kw):
	"""
	Execute a command and return its output as a string.
	Supports the same keyword arguments as subprocess.Popen.
	@param cmd: Command line or list of arguments
	@rtype: string
	@return: Output of the command
	"""
	silent = False
	if 'silent' in kw:
		silent = kw['silent']
		del(kw['silent'])

	if 'e' in kw:
		tmp = kw['e']
		del(kw['e'])
		kw['env'] = tmp

	kw['shell'] = isinstance(cmd, str)
	kw['stdout'] = pproc.PIPE
	if silent:
		kw['stderr'] = pproc.PIPE

	try:
		p = pproc.Popen(cmd, **kw)
		output = p.communicate()[0]
	except OSError, e:
		raise ValueError(str(e))

	if p.returncode:
		if not silent:
			msg = "command execution failed: %s -> %r" % (cmd, str(output))
			raise ValueError(msg)
		output = ''
	return output

reg_subst = re.compile(r"(\\\\)|(\$\$)|\$\{([^}]+)\}")
def subst_vars(expr, params):
	"""
	Substitute variables in a string.
	Replaces ${VAR} with the value of VAR taken from the dictionary
	or the environment supplied as the second parameter.
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
			# environments may contain lists
			return params.get_flat(m.group(3))
		except AttributeError:
			return params[m.group(3)]
	return reg_subst.sub(repl_var, expr)

def unversioned_sys_platform_to_binary_format(unversioned_sys_platform):
	"""
	Get the binary format based on the unversioned platform name.
	"""
	if unversioned_sys_platform in ('linux', 'freebsd', 'netbsd', 'openbsd', 'sunos'):
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

#@deprecated('use unversioned_sys_platform instead')
def detect_platform():
	"""
	@deprecated
	"""
	s = sys.platform

	# known POSIX
	for x in 'cygwin linux irix sunos hpux aix darwin'.split():
		# sys.platform may be linux2
		if s.find(x) >= 0:
			return x

	# unknown POSIX
	if os.name in 'posix java os2'.split():
		return os.name

	return s

def load_tool(tool, tooldir=None):
	"""
	Import the Python module that contains the specified tool from
	the tools directory.
	@type  tool: string
	@param tool: Name of the tool
	@type  tooldir: list
	@param tooldir: List of directories to search for the tool module
	"""
	if tooldir:
		assert isinstance(tooldir, list)
		sys.path = tooldir + sys.path
	try:
		try:
			return __import__(tool)
		except ImportError, e:
			raise WscriptError('Could not load the tool %r in %r' % (tool, sys.path))
	finally:
		if tooldir:
			for d in tooldir:
				sys.path.remove(d)

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

def cpu_count():
	"""
	Get the number of processors.
	@rtype: number
	@return: Number of processors
	"""
	count = 0
	if sys.platform == 'win32':
		# on Windows, use the NUMBER_OF_PROCESSORS environmental variable
		return int(os.environ.get('NUMBER_OF_PROCESSORS', 1))
	else:
		# on everything else, first try the POSIX sysconf values
		if hasattr(os, 'sysconf_names'):
			if 'SC_NPROCESSORS_ONLN' in os.sysconf_names:
				return int(os.sysconf('SC_NPROCESSORS_ONLN'))
			elif 'SC_NPROCESSORS_CONF' in os.sysconf_names:
				return int(os.sysconf('SC_NPROCESSORS_CONF'))
		else:
			count = Utils.cmd_output(['sysctl', '-n', 'hw.ncpu'])
			if re.match('^[0-9]+$', count):
				return int(count)
	return 1

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

context_dict = {}

class command_context(object):
	"""
	Command context decorator. Indicates which command should receive
	this context as its argument (first arg), and which function should be
	executed in user scripts (second arg).
	"""
	def __init__(self, command_name, function_name=None):
		self.command_name = command_name
		self.function_name = function_name if function_name else command_name
	def __call__(self, cls):
		context_dict[self.command_name] = cls
		setattr(cls, 'function_name', self.function_name)
		return cls

class Context(object):
	"""
	Base class for command contexts. Those objects are passed as the arguments
	of user functions (commands) defined in Waf scripts.
	"""
	def __init__(self, start_dir=None):
		self.curdir = start_dir or os.getcwd()
	def get_curdir(self):
		return self.curdir

	# TODO these hooks seem useless
	def pre_recurse(self, obj, f, d):
		pass
	def post_recurse(self, obj, f, d):
		pass

	def user_function_name(self):
		"""
		Get the user function name. First use an instance variable, then
		try the class variable. The instance variable will be set by
		Scripting.py if the class variable is not set.
		"""
		name = getattr(self, 'function_name', None)
		if not name:
			name = getattr(self.__class__, 'function_name', None)
		if not name:
			raise Utils.WafError('%s does not have an associated user function name.' % self.__class__.__name__)
		return name

	def recurse(self, dirs, name=None):
		"""
		Run user code from the supplied list of directories.
		The directories can be either absolute, or relative to the directory
		of the wscript file.
		@param dirs: List of directories to visit
		@type  name: string
		@param name: Name of function to invoke from the wscript
		"""
		function_name = name or self.user_function_name()

		# convert to absolute paths
		dirs = to_list(dirs)
		dirs = [x if os.path.isabs(x) else os.path.join(self.curdir, x) for x in dirs]

		for d in dirs:
			wscript_file = os.path.join(d, WSCRIPT_FILE)
			partial_wscript_file = wscript_file + '_' + function_name
			
			# if there is a partial wscript with the body of the user function,
			# use it in preference
			if os.path.exists(partial_wscript_file):
				exec_dict = {'ctx':self, 'conf':self, 'bld':self, 'opt':self}
				function_code = readf(partial_wscript_file, m='rU')
				
				self.pre_recurse(function_code, partial_wscript_file, d)
				old_dir = self.curdir
				self.curdir = d
				try:
					exec(function_code, exec_dict)
				except Exception:
					raise WscriptError(traceback.format_exc(), d)
				finally:
					self.curdir = old_dir
				self.post_recurse(function_code, partial_wscript_file, d)
			
			# if there is only a full wscript file, use a suitably named
			# function from it
			elif os.path.exists(wscript_file):
				# do not catch any exceptions here
				wscript_module = load_module(wscript_file)
				user_function = getattr(wscript_module, function_name, None)
				if not user_function:
					raise WscriptError('No function %s defined in %s'
						% (function_name, wscript_file))
				self.pre_recurse(user_function, wscript_file, d)
				old_dir = self.curdir
				self.curdir = d
				try:
					user_function(self)
				except TypeError:
					user_function()
				finally:
					self.curdir = old_dir
				self.post_recurse(user_function, wscript_file, d)
			
			# no wscript file - raise an exception
			else:
				raise WscriptError('No wscript file in directory %s' % d)
	
	def prepare(self):
		"""Executed before the context is passed to the user function."""
		pass

	def run_user_code(self):
		"""Call the user function to which this context is bound."""
		f = getattr(g_module, self.user_function_name(), None)
		if f is None:
			raise WscriptError('Undefined command: %s' % self.user_function_name())
		try:
			f(self)
		except TypeError:
			f()

	def finalize(self):
		"""Executed after the user function finishes."""
		pass

	def execute(self):
		"""Run the command represented by this context."""
		self.prepare()
		self.run_user_code()
		self.finalize()

def create_context(cmd_name, *k, **kw):
	if cmd_name in context_dict:
		return context_dict[cmd_name](*k, **kw)
	else:
		return Context(*k, **kw)

class Timer(object):
	"""
	Simple object for timing the execution of commands.
	Its string representation is the current time.
	"""
	def __init__(self):
		self.start()
	def _now(self):
		# use utcnow(), otherwise we can display bogus values for example when
		# a DST change happens during a Waf run
		return datetime.datetime.utcnow()
	def start(self):
		"""Start the timer. Note that the timer is started on construction."""
		self.start_time = self._now()
		self.stop_time = None
	def stop(self):
		"""Stop the timer."""
		self.stop_time = self._now()
	def __str__(self):
		delta = (self.stop_time or self._now()) - self.start_time
		days = int(delta.days)
		hours = int(delta.seconds / 3600)
		minutes = int((delta.seconds - hours * 3600) / 60)
		seconds = delta.seconds - hours * 3600 - minutes * 60 \
			+ float(delta.microseconds) / 1000 / 1000
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

