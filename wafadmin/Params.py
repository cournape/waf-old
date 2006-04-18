#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, sys, types, inspect
import Utils

g_version='0.7.4' # ph34r
g_rootname = ""
if sys.path=='win32':
	# get the first two letters (c:)
	g_rootname = os.getcwd()[:2]

# by default
g_dbfile='.dblite'

## == ACTIONS and SCANNERS == ##
## actions defined globally
g_actions ={}
g_scanners={}
#g_recursive_scanner=[]
# fake builders, for development and testing purposes
g_fake = 0

# contains additional handler functions to add language support
# to cpp files: for example an idl file which compiles into a cpp file
g_handlers={}

# avoid importing tools several times
g_tools = []

## == ENVIRONMENT == ##
# map a name to an environment, the 'default' must be defined
g_envs={}

## == DEPTREE == ##
g_excludes = ['.svn', 'CVS', 'wafadmin', 'cache', '{arch}', '.arch-ids']
g_pattern_excludes = ['_build_']
g_strong_hash = 0

def sig_nil():
	if g_strong_hash: return 'c01a85d0a38b176482a6e529f81f5251'
	else: return 0

# yes, i was focusing on imitating scons where this really was not necessary (ita)
#g_mode = 'copy'
#g_mode = 'slnk'
#g_mode = 'hlnk'
g_mode = 'nocopy'

# cygwin supports symlinks though ..
if sys.platform == 'win32': g_mode = 'copy'

## == TASK AND RUNNER == ##
# objects that are not posted and objects already posted
# -> delay task creation
g_outstanding_objs=[]
g_posted_objs=[]

# tasks that have been run
# this is used in tests to check which tasks were launched
g_tasks_done=[]

## == BUILD == ##

## the only Build object
g_build    = None

g_maxjobs = 1

## == SCRIPTING == ##
# tells if we are reading the code from the root directory or not
g_inroot = 1

## IMPORTANT
# the current directory from which the code is run
# the folder changes everytime a sconscript is read
g_curdirnode = None

# temporary holding the subdirectories containing scripts
g_subdirs=[]

# node representing the source directory
g_srcnode = None
g_bldnode = None

# node representing the directory from which the program was started
g_startnode = None

## == OPTIONS == ##
# parsed command-line arguments
g_options = []
g_commands = {}
g_verbose = 0

# list of folders that are already scanned
# so that we do not need to stat them one more time
g_scanned_folders=[]


# used by environment, this is the directory containing our Tools
g_tooldir=''

## Mapping between extensions and languages
g_exts = {
'.c'   : 'cc',

'.cpp' : 'cpp',
'.cc'  : 'cpp',
'.cxx' : 'cpp',

'.ui'  : 'uic',
'.moc' : 'moc',

'.java': 'java',
'.ml'  : 'caml',
'.tex' : 'tex',
}

# no colors on win32 :-/
if sys.platform=='win32':
	g_colors = {
	'BOLD'  :"",
	'RED'   :"",
	'REDP'  :"",
	'GREEN' :"",
	'YELLOW':"",
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
	'CYAN'  :"\033[96m",
	'NORMAL':"\033[0m",
	}

def pprint(col, str, label=''):
	try: mycol=g_colors[col]
	except: mycol=''
	print "%s%s%s %s" % (mycol, str, g_colors['NORMAL'], label)

## IMPORTANT debugging helpers
g_levels={
	'Action'  : 'GREEN',
	'Build'   : 'CYAN',
	'Deptree' : 'CYAN',
	'KDE'     : 'REDP',
	'Node'    : 'GREEN',
	'Object'  : 'GREEN',
	'Runner'  : 'REDP',
	'Task'    : 'GREEN',
	'Test'    : 'GREEN',
}

g_trace_exclude = "Deptree Node Object ".split()

def set_trace(a, b, c):
	Utils.g_trace=a
	Utils.g_debug=b
	Utils.g_error=c

## IMPORTANT helper functions
def niceprint(msg, type='', module=''):
	if not module:
		print '%s: %s'% (type, msg)
		return
	if type=='ERROR':
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
	try:
		# TODO why the hell ?
		s = (o1^o2)-1
		return s
	except:
		try:
			#return o1+o2
			return "".join( map(lambda a, b: chr(ord(a) ^ ord(b)), o1, o2) )
		except:
			print "exception xor_sig with incompatible objects", o1, o2
			raise


