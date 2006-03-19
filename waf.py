#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, string, sys, imp

# TODO remove
#os.popen("rm -rf _build_ .dblite")

# Climb up to the folder containing the main wscript and chdir to it
# It is also possible that the project was configured as a sub-module
# in this case, stop when a ".stopwscript" file is found
cwd = os.getcwd()
candidate = None
try:
	while 1:
		if len(cwd)<=3: break # stop at / or c:\
		dirlst = os.listdir(cwd)
		if 'wscript'      in dirlst: candidate = cwd
		if '.stopwscript' in dirlst: break
		cwd = cwd[:cwd.rfind(os.sep)] # climb up
except:
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
sys.path=lst+sys.path

import Options, Params, Utils

# Set the directory containing the tools
Params.g_tooldir = [os.path.join(dir, 'Tools')]

# For now, no debugging output
Params.set_trace(0,0,0)

# fetch the custom command-line options
Utils.fetch_options(os.path.join(candidate, 'wscript'))

# TODO We should parse the command-line arguments first
if 'dist' in sys.argv:
	version    = '1.0'
	appname    = 'noname'

	file_path = os.path.join(candidate, 'wscript')

	file = open(file_path, 'r')
	name = 'wscript'
	desc = ('', 'U', 1)

	module = imp.load_module(file_path, file, name, desc)
	try:    version = module.VERSION
	except: pass
	try:    appname = module.APPNAME
	except: pass

	if file: file.close()

	from Scripting import Dist
	Dist(appname, version)
	sys.exit(0)
elif 'distclean' in sys.argv:
	from Scripting import DistClean
	DistClean()
	sys.exit(0)

# Process command-line options
Options.parse_args()

from Scripting import Main
Main()

