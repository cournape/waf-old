#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, string, sys, imp

# Climb up to the folder containing the main wscript and chdir to it
# It is also possible that the project was configured as a sub-module
# in this case, stop when a ".lock-wscript" file is found
cwd = os.getcwd()
candidate = None

# Some people want to configure their projects gcc-style:
# mkdir build && cd build && ../waf.py configure && ../waf.py
# check that this is really what is wanted
build_dir_override = None
if 'configure' in sys.argv:
	#if not os.listdir(cwd):
	if not 'wscript' in os.listdir(cwd):
		build_dir_override = cwd

try:
	while 1:
		if len(cwd)<=3: break # stop at / or c:
		dirlst = os.listdir(cwd)
		if 'wscript'      in dirlst: candidate = cwd
		if 'configure' in sys.argv and candidate: break
		if '.lock-wscript' in dirlst: break
		cwd = cwd[:cwd.rfind(os.sep)] # climb up
except:
	print '\033[91mMain wscript file was not found in dir or above, exiting now\033[0m'
	sys.exit(1)

if not candidate:
	print '\033[91mMain wscript file was not found in dir or above, exiting now\033[0m'
	sys.exit(1)

# We have found wscript, but there is no guarantee that it is valid
os.chdir(candidate)

# The following function returns the first wafadmin folder found in the list of candidates
def find_wafdir(lst_cand):
	for dir in lst_cand:
		try:
			os.stat(dir)
			return dir
		except:
			pass
	print 'The waf directory was not found'
	print str(lst_cand)
	sys.exit(1)

wafadmin_dir1 = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'wafadmin')
wafadmin_dir2 = os.path.join(os.path.abspath('.'), 'wafadmin')
if sys.platform == "win32":
	lst=[wafadmin_dir1, wafadmin_dir2]
else:
	lst=[wafadmin_dir1, wafadmin_dir2, '/usr/lib/wafadmin','/usr/local/lib/wafadmin']

dir = find_wafdir(lst)

# The sys.path is updated, so we can now import our modules
sys.path=[dir, dir+os.sep+'Tools']+sys.path

import Options, Params, Utils

# Set the directory containing the tools
Params.g_tooldir = [os.path.join(dir, 'Tools')]

# For now, no debugging output
Params.set_trace(0,0,0)

# define the main module containing the functions init, shutdown, ..
Utils.set_main_module(os.path.join(candidate, 'wscript'))

if build_dir_override:
	try:
		# test if user has set the blddir in wscript.
		blddir = Utils.g_module.blddir
		msg = 'Overriding blddir %s with %s' % (mblddir, bldcandidate)
		Params.niceprint('YELLOW', msg)
	except: pass
	Utils.g_module.blddir = build_dir_override

# fix the path of the cachedir - it is mandatory
if sys.platform=='win32':
	try:
		lst = Utils.g_module.cachedir.split('/')
		Utils.g_module.cachedir = os.sep.join(lst)
	except:
		Params.niceprint('RED', 'No cachedir specified in wscript!')
		raise

# fetch the custom command-line options recursively and in a procedural way
opt_obj = Options.Handler()
opt_obj.sub_options('')
opt_obj.parse_args()

# we use the results of the parser
if Params.g_commands['dist']:
	# try to use the user-defined dist function first, fallback to the waf scheme
	try:
		Utils.g_module.dist()
		sys.exit(0)
	except:
		pass
	appname         = 'noname'
	try:    appname = Utils.g_module.APPNAME
	except: pass

	version         = '1.0'
	try:    version = Utils.g_module.VERSION
	except: pass

	from Scripting import Dist
	Dist(appname, version)
	sys.exit(0)
elif Params.g_commands['distclean']:
	# try to use the user-defined distclean first, fallback to the waf scheme
	try:
		Utils.g_module.distclean()
		sys.exit(0)
	except:
		pass

	from Scripting import DistClean
	DistClean()
	sys.exit(0)

try:
	fun = None
	try:
		fun = Utils.g_module.init
	except:
		pass
	if fun: fun()
except SystemExit:
	raise

from Scripting import Main
Main()

