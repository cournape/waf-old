#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, string, sys

# TODO remove
#os.popen("rm -rf _build_ .dblite")

# Climb up to the folder containing the sconstruct and chdir to it
cwd = os.getcwd()
try:
	while 1:
		dirlst = os.listdir(cwd)
		if 'sconstruct' in dirlst:
			os.chdir(cwd)
			break
		# dir up
		cwd = cwd[:cwd.rfind(os.sep)]
except:
	print '\033[91msconstruct file was not found in dir or above, exiting\033[0m'
	sys.exit(1)

# Setup the waf directory path
def find_wafdir(cand):
	for dir in cand:
		try:
			os.stat(dir)
			return dir
		except:
			pass
	print 'The waf directory was not found'
	print str(cand)
	sys.exit(1)

wafadmin_dir1 = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),'wafadmin')
wafadmin_dir2 = os.path.join(os.path.abspath('.'), 'wafadmin')
if sys.platform == "win32":
	lst=[wafadmin_dir1, wafadmin_dir2]
else:
	lst=[wafadmin_dir1, wafadmin_dir2, '/usr/lib/wafadmin','/usr/local/lib/wafadmin']

dir = find_wafdir(lst)
sys.path=lst+sys.path
import Options, Params
Params.g_tooldir = [os.path.join(dir, 'Tools')]

# Try to find the custom options

# For now, no debugging output
Params.set_trace(0,0,0)

try:
	file_content = open('sconfigure', 'rb').read()
	import re
	add_opt_regexp = re.compile('[\n](add_option\(.*\))')
	Options.g_custom_options = add_opt_regexp.findall(file_content)
except:
	#print "error reading the sconfigure script"
	pass

if 'dist' in sys.argv:
	from Scripting import Dist
	import re

	version_regexp = re.compile('VERSION\s*=\s*[\'\"](.+)[\'\"]\s*', re.M)
	appname_regexp = re.compile('APPNAME\s*=\s*[\'\"](.+)[\'\"]\s*', re.M)

	try:
		string = open('sconstruct', 'r').read()
		vnum = version_regexp.findall( string )[0]
		app  = appname_regexp.findall( string )[0]
	except:
		print "\033[91mError in dist, sconstruct file cannot be opened or does not contain APPNAME and VERSION\033[0m"
	Dist(app, vnum)
	sys.exit(0)
elif 'distclean' in sys.argv:
	from Scripting import DistClean
	DistClean()
	sys.exit(0)

# Process command-line options
Options.parse_args()

from Scripting import Main
Main()

