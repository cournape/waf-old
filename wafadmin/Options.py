#! /usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)

import sys
import string
from types import *
from optparse import OptionParser
import Params

g_custom_options=[]
g_funcs=[]

#def do_exec(parser, pargs):
#	exec 'parser.'+pargs

def parse_args():
	Params.trace("parse_args is called")

	def to_list(sth):
		if type(sth) is ListType: return sth
		else: return [sth]

	parser = OptionParser(usage = """waf [options] [commands ...]

* Main commands: configure make install clean distclean dist doc
* Example: ./waf make -j4""", version = 'waf %s' % Params.g_version)
	
	# Our options
	p=parser.add_option

	p('-d', '--debug-level',
		action = 'store',
		default = 'release',
		help = 'Specify the debug level. [Allowed Values: ultradebug, debug, release, optimized]',
		dest = 'debug_level')
	
	p('-j', '--jobs', 
		type = 'int',
		default = 1,
		help = 'Specify the number of parallel jobs [Default: 1]',
		dest = 'jobs')
	
	#p('-q', '--quiet', 
	#	action = 'store_true',
	#	default = False,
	#	help = 'Show no output. [Default: False]',
	#	dest = 'quiet')
	
	#p('-s', '--signature-type',
	#	type = 'string',
	#	default = 'timestamp',
	#	help = 'Specify the signature type to use - timestamp (fast) or md5 (slow). [Default: timestamp]',
	#	dest = 'signature_type')
	
	#p('-t', '--target',
	#	action = 'append',
	#	default = '',
	#	help = 'Specify the target os to build for. Can specify this option multiple times if required. [Allowed Values: linux, freebsd, solaris, darwin, win32]',
	#	dest = 'target')

	p('-v', '--verbose', 
		action = 'count',
		default = 0,
		help = 'Show verbose output [Default: False]',
		dest = 'verbose')

	global g_custom_options
	for fun in g_custom_options:
		fun(parser)

	# Now parse the arguments
	(Params.g_options, args) = parser.parse_args()
	#print Params.g_options, " ", args

	# Now check the options that have been defined
	lst=['ultradebug', 'debug', 'release', 'optimized']
	if Params.g_options.debug_level not in lst:
		print 'Error: Invalid debug level specified'
		print parser.print_help()
		sys.exit(1)

	# signatures in options is a really bad idea ..
	#if Params.g_options.signature_type not in ('timestamp', 'md5'):
	#	print 'Error: Invalid signature type specified'
	#	print parser.print_help()
	#	sys.exit(1)
	
	#lst=['', 'linux', 'freebsd', 'solaris', 'darwin', 'win32']
	#if Params.g_options.target not in lst:
	#	print 'Error: Invalid target specified'
	#	print parser.print_help()
	#	sys.exit(1)
	
	# By default, 'waf' is equivalent to 'waf make'
	lst=['dist','configure','clean','distclean','make','install','doc']
	for var in lst:    Params.g_commands[var]    = 0
	if len(args) == 0: Params.g_commands['make'] = 1
	

	# Parse the command arguments
	for arg in args:
		arg = arg.strip()
		if arg in lst:
			Params.g_commands[arg]=True
		else:
			print 'Error: Invalid command specified ',arg
			print parser.print_help()
			sys.exit(1)

	Params.g_maxjobs = Params.g_options.jobs
	Params.g_verbose = Params.g_options.verbose
	if Params.g_verbose>1: Params.set_trace(1,1,1)
	#if Params.g_options.wafcoder: Params.set_trace(1,1,1)


