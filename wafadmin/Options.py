#! /usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)

import os, sys, string
from types import *
from optparse import OptionParser
import Params, Utils
from Params import debug, trace, fatal, error

def create_parser():
	Params.trace("create_parser is called")

	def to_list(sth):
		if type(sth) is ListType: return sth
		else: return [sth]

	parser = OptionParser(usage = """waf [options] [commands ...]

* Main commands: configure build install clean dist distclean uninstall
* Example: ./waf build -j4""", version = 'waf %s' % Params.g_version)
	
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
	
	p('-e', '--evil', 
		action = 'store_true',
		default = False,
		help = 'IMPLEMENTED ME (Run as a daemon). [Default: False]',
		dest = 'daemon')
	
	p('-v', '--verbose', 
		action = 'count',
		default = 0,
		help = 'Show verbose output [Default: False]',
		dest = 'verbose')

	if 'configure' in sys.argv:
		p('-b', '--blddir',
			action = 'store',
			default='',
			help='build dir for the project (configuration)',
			dest = 'blddir')

		p('-s', '--srcdir',
			action = 'store',
			default='',
			help='src dir for the project (configuration)',
			dest = 'srcdir')

	return parser

def parse_args_impl(parser):

	(Params.g_options, args) = parser.parse_args()
	#print Params.g_options, " ", args

	# Now check the options that have been defined
	lst=['ultradebug', 'debug', 'release', 'optimized']
	if Params.g_options.debug_level not in lst:
		print 'Error: Invalid debug level specified'
		print parser.print_help()
		sys.exit(1)

	# By default, 'waf' is equivalent to 'waf build'
	lst=['dist','configure','clean','distclean','build','install','uninstall','doc']
	for var in lst:    Params.g_commands[var]    = 0
	if len(args) == 0: Params.g_commands['build'] = 1

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

# TODO bad name for a useful class
# loads wscript modules in folders for adding options
class Handler:
	def __init__(self):
		self.parser    = create_parser()
		self.cwd = os.getcwd()
	def add_option(self, *kw, **kwargs):
		self.parser.add_option(*kw, **kwargs)
	def sub_options(self, dir):
		current = self.cwd

		self.cwd = os.path.join(self.cwd, dir)
		cur = os.path.join(self.cwd, 'wscript')

		try:
			mod = Utils.load_module(cur)
		except:
			msg = "no module was found for wscript (sub_options)\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
			fatal(msg % self.cwd)
		try:
			mod.set_options(self)
		except AttributeError:
			msg = "no set_options function was found in wscript\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
			fatal(msg % self.cwd)

		self.cwd = current

	def parse_args(self):
		parse_args_impl(self.parser)

