#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, sys, types, inspect, md5, random
import Utils

### CONSTANTS ###

g_version='0.8.3' # ph34r
g_rootname = ''
if sys.path=='win32':
	# get the first two letters (c:)
	g_rootname = os.getcwd()[:2]

# it is unlikely that we change the name of this file
g_dbfile='.dblite'

# preprocessor for c/c++
g_preprocess = 1

# deptree
g_excludes = ['.svn', 'CVS', 'wafadmin', 'cache', '{arch}', '.arch-ids']
g_pattern_excludes = ['_build_']
g_strong_hash = 1

def sig_nil():
	if g_strong_hash: return '\xaea\x86\xf0T\xbd\x93\xc5V\x01\xc6Y"\x7fi\xd4'
	else: return 0

### NO RESETS BETWEEN RUNS ###

# used by environment, this is the directory containing our Tools
g_tooldir=''

# parsed command-line arguments in the options module
g_options = None
g_commands = {}
g_verbose = 0

# max jobs
g_maxjobs = 1

### EXTENSIONS ###

## the only Build object
g_build    = None


g_cachedir = ''

### HELPERS ####

# no colors on win32 :-/
if sys.platform=='win32':
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

# IMPORTANT debugging helpers
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

# IMPORTANT helper functions
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
		s = (o1^o2)-0
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

import base64
def vsig(s):
	if type(s) is types.StringType:
		n = base64.encodestring(s)
		if len(n)>2:
			return n[:len(n)-2]
		return n
	else:
		return str(s)
