#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, sys, types, inspect, md5, random, base64
import Utils

# =================================== #
# Fixed constants, change with care

g_version="0.9.0"
g_rootname = ''
if sys.path=='win32':
	# get the first two letters (c:)
	g_rootname = os.getcwd()[:2]

# It is unlikely that we change the name of this file
g_dbfile='.dblite'

# Preprocessor for c/c++
g_preprocess = 1

# Dependency tree
g_excludes = ['.svn', 'CVS', 'wafadmin', '.arch-ids']

# Hash method: md5 or simple scheme over integers
g_strong_hash = 1

# The null signature depends upon the Hash method in use
def sig_nil():
	if g_strong_hash: return 'iluvcuteoverload'
	else: return 0

# =================================== #
# Constants set on runtime

g_globals = {}
def set_globals(name, value):
	g_globals[name] = value
def globals(name):
	try: return g_globals[name]
	except: return []

# Set by waf.py
g_launchdir = None

# This is the directory containing our Tools (used in particular by Environment.py)
g_tooldir=''

# Parsed command-line arguments in the options module
g_options = None
g_commands = {}

# Verbosity: -v displays warnings, -vv displays developper info
g_verbose = 0

# The only Build object
g_build    = None

# Our cache directory
g_cachedir = ''

# =================================== #
# HELPERS

# no colors on win32 :-/
if sys.platform=='win32' or 'NOCOLOR' in os.environ:
	g_colors = {
	'BOLD'  :"",
	'RED'   :"",
	'REDP'  :"",
	'GREEN' :"",
	'YELLOW':"",
	'BLUE'  :"",
	'CYAN'  :"",
	'NORMAL':"",
	}
else:
	g_colors= {
	'BOLD'  :"\033[1m",
	'RED'   :"\033[91m",
	'REDP'  :"\033[33m",
	'GREEN' :"\033[92m",
	'YELLOW':"\033[93m", # if not readable on white backgrounds, bug in YOUR terminal
	'BLUE'  :"\033[94m",
	'CYAN'  :"\033[96m",
	'NORMAL':"\033[0m",
	}

def set_color(name, color):
	if not color in g_colors:
		error('color does not exist as an alias ! '+color)
	else:
		g_colors[name]=g_colors[color]

def pprint(col, str, label=''):
	try: mycol=g_colors[col]
	except: mycol=''
	print "%s%s%s %s" % (mycol, str, g_colors['NORMAL'], label)

g_levels={
	'Action'  : 'GREEN',
	'Build'   : 'CYAN',
	'KDE'     : 'REDP',
	'Node'    : 'GREEN',
	'Object'  : 'GREEN',
	'Runner'  : 'REDP',
	'Task'    : 'GREEN',
	'Test'    : 'GREEN',
}

g_trace_exclude = "Object ".split()

def set_trace(a, b, c):
	Utils.g_trace=a
	Utils.g_debug=b
	Utils.g_error=c

def get_trace():
	return (Utils.g_trace, Utils.g_debug, Utils.g_error)

def niceprint(msg, type='', module=''):
	if not module:
		print '%s: %s'% (type, msg)
		return
	if type=='ERROR':
		print '%s: %s == %s == %s %s'% (type, g_colors['RED'], module, g_colors['NORMAL'], msg)
		return
	if type=='WARNING':
		print '%s: %s == %s == %s %s'% (type, g_colors['RED'], module, g_colors['NORMAL'], msg)
		return
	if type=='DEBUG':
		print '%s: %s == %s == %s %s'% (type, g_colors['YELLOW'], module, g_colors['NORMAL'], msg)
		return
	if module in g_levels:
		print '%s: %s == %s == %s %s'% (type, g_colors[g_levels[module]], module, g_colors['NORMAL'], msg)
		return
	print 'TRACE: == %s == %s'% (module, msg)

def trace(msg):
	module = inspect.stack()[1][0].f_globals['__name__']

	if not Utils.g_trace: return
	if module in g_trace_exclude: return
	niceprint(msg, 'TRACE', module)
def warning(msg):
	module = inspect.stack()[1][0].f_globals['__name__']
	niceprint(msg, 'WARNING', module)
def debug(msg):
	module = inspect.stack()[1][0].f_globals['__name__']

	if not Utils.g_debug: return
	if module in g_trace_exclude: return
	niceprint(msg, 'DEBUG', module)
def error(msg):
	module = inspect.stack()[1][0].f_globals['__name__']

	if not Utils.g_error: return
	if module in g_trace_exclude: return
	niceprint(msg, 'ERROR', module)
def fatal(msg):
	module = inspect.stack()[1][0].f_globals['__name__']

	# this one is fatal
	#niceprint(msg, 'ERROR', module)
	pprint('RED', msg+" \n(error raised in module "+module+")")
	sys.exit(1)

def h_file(fname):
	global g_strong_hash
	if g_strong_hash: return Utils.h_md5_file(fname)
	return Utils.h_simple_file(fname)

def h_string(string):
	global g_strong_hash
	if g_strong_hash: return Utils.h_md5_str(string)
	return Utils.h_simple_str(string)

def h_list(lst):
	global g_strong_hash
	if g_strong_hash: return Utils.h_md5_lst(lst)
	return Utils.h_simple_lst(lst)

def xor_sig(o1, o2):
	#if o1 == o2: return o1
	try:
		# we add -0 to make sure these are integer values
		s = int(int(33*o1)+o2)
		return s
	except:
		try:
			#m = md5.new()
			#m.update(o1)
			#m.update(o2)
			#return m.digest()
	
			return "".join( map(lambda a, b: chr(ord(a) ^ ord(b)), o1, o2) )
		except:
			print len(o1), len(o2)
			print repr(o1), repr(o2)
			print "exception xor_sig with incompatible objects", str(o1), str(o2)
			raise

# used for displaying signatures
def vsig(s):
	if type(s) is types.StringType:
		n = base64.encodestring(s)
		try: return n[-2]
		except: return n
	else:
		return str(s)

