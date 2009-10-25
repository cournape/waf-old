#!/usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)
# Thomas Nagy, 2006 (ita)

"Custom command-line options"

import os, sys, imp, types, tempfile, optparse
import Logs, Utils
from Utils import command_context
from Constants import *

cmds = 'distclean configure build install clean uninstall check dist distcheck'.split()

# TODO remove in waf 1.6 the following two
# commands = {}
is_install = False

options = {}
"""A dictionary of options received from parsing"""
commands = []
"""List of commands to execute"""
launch_dir = ''
"""Directory from which Waf was executed"""
tooldir = ''
"""Directory where the tool modules are located"""

lockfile = os.environ.get('WAFLOCK', '.lock-wscript')
try: cache_global = os.path.abspath(os.environ['WAFCACHE'])
except KeyError: cache_global = ''
platform = Utils.unversioned_sys_platform()
conf_file = 'conf-runs-%s-%d.pickle' % (platform, ABI)

# Such a command-line should work:  JOBS=4 PREFIX=/opt/ DESTDIR=/tmp/ahoj/ waf configure
default_prefix = os.environ.get('PREFIX')
if not default_prefix:
	if platform == 'win32': default_prefix = tempfile.gettempdir()
	else: default_prefix = '/usr/local/'

default_jobs = os.environ.get('JOBS', -1)
if default_jobs < 1:
	default_jobs = Utils.cpu_count()

default_destdir = os.environ.get('DESTDIR', '')

def get_usage(self):
	"""Function to replace the default get_usage function of optparse.OptionParser;
	Provides help for Waf commands defined in a wscript"""
	cmds_str = []
	module = Utils.g_module
	if module:
		# create the help messages for commands
		tbl = module.__dict__
		keys = list(tbl.keys())
		keys.sort()

		if 'build' in tbl:
			if not module.build.__doc__:
				module.build.__doc__ = 'builds the project'
		if 'configure' in tbl:
			if not module.configure.__doc__:
				module.configure.__doc__ = 'configures the project'

		ban = ['set_options', 'init', 'shutdown']

		optlst = [x for x in keys if not x in ban
			and type(tbl[x]) is type(get_usage)
			and tbl[x].__doc__
			and not x.startswith('_')]

		just = max([len(x) for x in optlst])

		for x in optlst:
			cmds_str.append('  %s: %s' % (x.ljust(just), tbl[x].__doc__))
		ret = '\n'.join(cmds_str)
	else:
		ret = ' '.join(cmds)
	return '''waf [command] [options]

Main commands (example: ./waf build -j4)
%s
''' % ret


setattr(optparse.OptionParser, 'get_usage', get_usage)

def create_parser(module=None):
	Logs.debug('options: create_parser is called')
	parser = optparse.OptionParser(conflict_handler="resolve", version = 'waf %s (%s)' % (WAFVERSION, WAFREVISION))

	parser.formatter.width = Utils.get_term_cols()
	p = parser.add_option

	# Add standard options here
	p('-j', '--jobs',
		type    = 'int',
		default = default_jobs,
		help    = 'amount of parallel jobs (%r)' % default_jobs,
		dest    = 'jobs')

	p('-k', '--keep',
		action  = 'store_true',
		default = False,
		help    = 'keep running happily on independent task groups',
		dest    = 'keep')

	p('-v', '--verbose',
		action  = 'count',
		default = 0,
		help    = 'verbosity level -v -vv or -vvv [default: 0]',
		dest    = 'verbose')

	p('--nocache',
		action  = 'store_true',
		default = False,
		help    = 'ignore the WAFCACHE (if set)',
		dest    = 'nocache')

	p('--zones',
		action  = 'store',
		default = '',
		help    = 'debugging zones (task_gen, deps, tasks, etc)',
		dest    = 'zones')

	p('-p', '--progress',
		action  = 'count',
		default = 0,
		help    = '-p: progress bar; -pp: ide output',
		dest    = 'progress_bar')

	p('--targets',
		action  = 'store',
		default = '',
		help    = 'build given task generators, e.g. "target1,target2"',
		dest    = 'compile_targets')

	gr = optparse.OptionGroup(parser, 'configuration options')
	parser.add_option_group(gr)
	gr.add_option('-b', '--blddir',
		action  = 'store',
		default = '',
		help    = 'build dir for the project (configuration)',
		dest    = 'blddir')
	gr.add_option('-s', '--srcdir',
		action  = 'store',
		default = '',
		help    = 'src dir for the project (configuration)',
		dest    = 'srcdir')
	gr.add_option('--prefix',
		help    = 'installation prefix (configuration) [default: %r]' % default_prefix,
		default = default_prefix,
		dest    = 'prefix')

	gr = optparse.OptionGroup(parser, 'installation options')
	parser.add_option_group(gr)
	gr.add_option('--destdir',
		help    = 'installation root [default: %r]' % default_destdir,
		default = default_destdir,
		dest    = 'destdir')
	gr.add_option('-f', '--force',
		action  = 'store_true',
		default = False,
		help    = 'force file installation',
		dest    = 'force')

	return parser

# TODO waf 1.6
# 2. instead of a class attribute, use a module (static 'parser')

@command_context('OPTIONS','set_options')
class OptionsContext(Utils.Context):
	"""Collects custom options from wscript files and parses the command line.
	Sets the global Options.commands and Options.options attributes."""

	def __init__(self, start_dir=None, module=None):
		super(self.__class__, self).__init__(start_dir)
		self.parser = create_parser(module)

	# pass through to optparse
	def add_option(self, *k, **kw):
		self.parser.add_option(*k, **kw)
	def add_option_group(self, *k, **kw):
		return self.parser.add_option_group(*k, **kw)
	def get_option_group(self, opt_str):
		return self.parser.get_option_group(opt_str)

	# deprecated - use the generic "recurse" method instead
	def sub_options(self, d):
		self.recurse(d, name='set_options')

	def tool_options(self, tool_list, *k, **kw):
		Utils.python_24_guard()

		#if not k[0]:
		#	raise Utils.WscriptError('invalid tool_options call %r %r' % (k, kw))
		tools = Utils.to_list(tool_list)

		# TODO waf 1.6 remove the global variable tooldir
		path = Utils.to_list(kw.get('tdir', kw.get('tooldir', tooldir)))

		for tool in tools:
			tool = tool.replace('++', 'xx')
			module = Utils.load_tool(tool, path)
			try:
				fun = module.set_options
			except AttributeError:
				pass
			else:
				fun(kw.get('option_group', self))

	# parse_args is defined separately to allow parsing arguments from somewhere else
	# than the Waf command line
	def parse_args(self, _args=None):
		global options, commands
		(options, leftover_args) = self.parser.parse_args(args=_args)
		commands = leftover_args

	def finalize(self):
		self.parse_args()
