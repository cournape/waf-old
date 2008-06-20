#!/usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)
# Thomas Nagy, 2006 (ita)

"Custom command-line options"

import os, sys, imp, types, tempfile
from optparse import OptionParser
import Params, Utils
from logging import debug, fatal
from Constants import *

# Such a command-line should work:  JOBS=4 PREFIX=/opt/ DESTDIR=/tmp/ahoj/ waf configure
default_prefix = os.environ.get('PREFIX')
if not default_prefix:
	if sys.platform == 'win32': default_prefix = tempfile.gettempdir()
	else: default_prefix = '/usr/local/'

default_jobs = os.environ.get('JOBS', 1)
default_destdir = os.environ.get('DESTDIR', '')

def create_parser():
	debug('options: create_parser is called')

	parser = OptionParser(usage = """waf [options] [commands ...]

* Main commands: configure build install clean dist distclean uninstall distcheck
* Example: ./waf build -j4""", version = 'waf %s' % Params.g_version)

	parser.formatter.width = Utils.get_term_cols()
	p = parser.add_option

	p('-j', '--jobs',
		type    = 'int',
		default = default_jobs,
		help    = "amount of parallel jobs [Default: %s]" % default_jobs,
		dest    = 'jobs')

	p('', '--daemon',
		action  = 'store_true',
		default = False,
		help    = 'run as a daemon [Default: False]',
		dest    = 'daemon')

	p('-f', '--force',
		action  = 'store_true',
		default = False,
		help    = 'force file installation',
		dest    = 'force')

	p('-k', '--keep',
		action  = 'store_true',
		default = False,
		help    = 'keep running happily on independant task groups',
		dest    = 'keep')

	p('-p', '--progress',
		action  = 'count',
		default = 0,
		help    = '-p: progress bar; -pp: ide output',
		dest    = 'progress_bar')

	p('-v', '--verbose',
		action  = 'count',
		default = 0,
		help    = 'verbosity level -v -vv or -vvv [Default: 0]',
		dest    = 'verbose')

	p('--destdir',
		help    = "installation root [Default: '%s']" % default_destdir,
		default = default_destdir,
		dest    = 'destdir')

	p('--nocache',
		action  = 'store_true',
		default = False,
		help    = 'compile everything, even if WAFCACHE is set',
		dest    = 'nocache')

	if 'configure' in sys.argv:
		p('-b', '--blddir',
			action  = 'store',
			default = '',
			help    = 'build dir for the project (configuration)',
			dest    = 'blddir')

		p('-s', '--srcdir',
			action  = 'store',
			default = '',
			help    = 'src dir for the project (configuration)',
			dest    = 'srcdir')

		p('--prefix',
			help    = "installation prefix (configuration only) [Default: '%s']" % default_prefix,
			default = default_prefix,
			dest    = 'prefix')

	p('--zones',
		action  = 'store',
		default = '',
		help    = 'debugging zones (task_gen, deps, tasks, etc)',
		dest    = 'zones')

	p('--targets',
		action  = 'store',
		default = '',
		help    = 'compile the targets given only [targets in CSV format, e.g. "target1,target2"]',
		dest    = 'compile_targets')

	return parser

def parse_args_impl(parser, _args=None):
	(Params.g_options, args) = parser.parse_args(args=_args)
	opts = Params.g_options
	#print Params.g_options, " ", args

	# By default, 'waf' is equivalent to 'waf build'
	lst='dist configure clean distclean build install uninstall check distcheck'.split()
	Params.g_commands = {}
	for var in lst:    Params.g_commands[var] = 0
	if len(args) == 0: Params.g_commands['build'] = 1

	# Parse the command arguments
	for arg in args:
		arg = arg.strip()
		if arg in lst:
			Params.g_commands[arg]=True
		else:
			print 'Error: Invalid command specified ',arg
			parser.print_help()
			sys.exit(1)
	if Params.g_commands['check']:
		Params.g_commands['build'] = True

	if Params.g_commands['install'] or Params.g_commands['uninstall']:
		Params.g_install = 1

	# TODO -k => -j0
	if opts.keep: opts.jobs = 1

	Params.g_verbose = opts.verbose

	import logging
	log = logging.getLogger()
	log.handlers = []
	hdlr = logging.StreamHandler()
	hdlr.setFormatter(Utils.log_format())
	log.addHandler(hdlr)
	log.addFilter(Utils.log_filter())
	log.setLevel(logging.DEBUG)

	if opts.zones:
		Params.g_zones = opts.zones.split(',')
		if not Params.g_verbose: Params.g_verbose = 1

class Handler(object):
	"loads wscript modules in folders for adding options"
	def __init__(self):
		self.parser = create_parser()
		self.cwd = os.getcwd()
		global g_parser
		g_parser = self

	def add_option(self, *kw, **kwargs):
		self.parser.add_option(*kw, **kwargs)

	def add_option_group(self, *args, **kwargs):
		return self.parser.add_option_group(*args, **kwargs)

	def get_option_group(self, opt_str):
		return self.parser.get_option_group(opt_str)

	def sub_options(self, dir, option_group=None):
		"""set options defined by wscripts:
		- run by Scripting to set the options defined by main wscript.
		- run by wscripts to set options in sub directories."""
		try:
			current = self.cwd

			self.cwd = os.path.join(self.cwd, dir)
			cur = os.path.join(self.cwd, WSCRIPT_FILE)

			mod = Utils.load_module(cur)
			try:
				fun = mod.set_options
			except AttributeError:
				msg = "no set_options function was found in wscript\n[%s]:\n * make sure such a function is defined \n * run configure from the root of the project"
				fatal(msg % self.cwd)
			else:
				fun(option_group or self)

		finally:
			self.cwd = current

	def tool_options(self, tool, tooldir=None, option_group=None):
		Utils.python_24_guard()
		if type(tool) is types.ListType:
			for i in tool: self.tool_options(i, tooldir, option_group)
			return

		if not tooldir: tooldir = Params.g_tooldir
		tooldir = Utils.to_list(tooldir)
		try:
			file,name,desc = imp.find_module(tool, tooldir)
		except ImportError:
			fatal("no tool named '%s' found" % tool)
		module = imp.load_module(tool,file,name,desc)
		try:
			fun = module.set_options
		except AttributeError:
			pass
		else:
			fun(option_group or self)

	def parse_args(self, args=None):
		parse_args_impl(self.parser, args)

g_parser = None
"Last Handler instance in use"

