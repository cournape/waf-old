#!/usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)
# Thomas Nagy, 2006 (ita)

"Custom command-line options"

import os, sys, imp, types, tempfile
from optparse import OptionParser
import Logs, Utils
from Constants import *

cmds = 'distclean configure build install clean uninstall check dist distcheck'.split()

options = {}
commands = {}
arg_line = []
launch_dir = ''
tooldir = ''
lockfile = os.environ.get('WAFLOCK', '.lock-wscript')
try: cache_global = os.path.abspath(os.environ['WAFCACHE'])
except KeyError: cache_global = ''
platform = Utils.detect_platform()
conf_file = 'conf-runs-%s-%d.pickle' % (platform, ABI)
is_install = False

# Such a command-line should work:  JOBS=4 PREFIX=/opt/ DESTDIR=/tmp/ahoj/ waf configure
default_prefix = os.environ.get('PREFIX')
if not default_prefix:
	if platform == 'win32': default_prefix = tempfile.gettempdir()
	else: default_prefix = '/usr/local/'

default_jobs = os.environ.get('JOBS', -1)
if default_jobs < 1:
	try:
		default_jobs = os.sysconf('SC_NPROCESSORS_ONLN')
	except:
		# environment var defined on win32
		default_jobs = int(os.environ.get('NUMBER_OF_PROCESSORS', 1))

default_destdir = os.environ.get('DESTDIR', '')

def create_parser(module=None):
	Logs.debug('options: create_parser is called')

	if module:
		cmds_str = []
		tbl = Utils.g_module.__dict__
		for x in tbl:
			if not x in ['set_options', 'init', 'shutdown']:
				if type(tbl[x]) is type(parse_args_impl):
					cmds_str.append(x)
		cmds_str = ' '.join(cmds_str)
	else:
		cmd_str = ' '.join(cmds)

	parser = OptionParser(conflict_handler="resolve", usage = '''waf [command] [options]

* Main commands: %s
* Example: ./waf build -j4''' % cmds_str, version = 'waf %s (%s)' % (WAFVERSION, WAFREVISION))

	parser.formatter.width = Utils.get_term_cols()
	p = parser.add_option

	p('-j', '--jobs',
		type    = 'int',
		default = default_jobs,
		help    = 'amount of parallel jobs [default: %r]' % default_jobs,
		dest    = 'jobs')

	p('-f', '--force',
		action  = 'store_true',
		default = False,
		help    = 'force file installation',
		dest    = 'force')

	p('-k', '--keep',
		action  = 'store_true',
		default = False,
		help    = 'keep running happily on independent task groups',
		dest    = 'keep')

	p('-p', '--progress',
		action  = 'count',
		default = 0,
		help    = '-p: progress bar; -pp: ide output',
		dest    = 'progress_bar')

	p('-v', '--verbose',
		action  = 'count',
		default = 0,
		help    = 'verbosity level -v -vv or -vvv [default: 0]',
		dest    = 'verbose')

	p('--destdir',
		help    = 'installation root [default: %r]' % default_destdir,
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
			help    = 'installation prefix (configuration) [default: %r]' % default_prefix,
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
		help    = 'build given task generators, e.g. "target1,target2"',
		dest    = 'compile_targets')

	return parser

def parse_args_impl(parser, _args=None):
	global options, commands, arg_line
	(options, args) = parser.parse_args(args=_args)

	arg_line = args

	# By default, 'waf' is equivalent to 'waf build'
	commands = {}
	for var in cmds:    commands[var] = 0
	if len(args) == 0:
		commands['build'] = 1
		arg_line.append('build')

	# Parse the command arguments
	for arg in args:
		arg = arg.strip()
		if arg in cmds:
			commands[arg]=True
		else:
			Utils.pprint('RED', 'Error: Invalid command specified %r' % arg)
			parser.print_help()
			sys.exit(1)
	if commands['check']:
		commands['build'] = True

	if commands['install'] or commands['uninstall']:
		global is_install
		is_install = True

	# TODO -k => -j0
	if options.keep: options.jobs = 1
	if options.jobs < 1: options.jobs = 1

	# absolute path only if set
	options.destdir = options.destdir and os.path.abspath(os.path.expanduser(options.destdir))

	Logs.verbose = options.verbose
	Logs.init_log()

	if options.zones:
		Logs.zones = options.zones.split(',')
		if not Logs.verbose: Logs.verbose = 1
	elif Logs.verbose > 0:
		Logs.zones = ['runner']
	if Logs.verbose > 2:
		Logs.zones = ['*']

class Handler(object):
	"loads wscript modules in folders for adding options"

	parser = None

	def __init__(self, module=None):
		self.parser = create_parser(module)
		self.cwd = os.getcwd()
		Handler.parser = self

	def add_option(self, *kw, **kwargs):
		self.parser.add_option(*kw, **kwargs)

	def add_option_group(self, *args, **kwargs):
		return self.parser.add_option_group(*args, **kwargs)

	def get_option_group(self, opt_str):
		return self.parser.get_option_group(opt_str)

	def sub_options(self, dir, option_group=None):
		"OBSOLETE - remove in Waf 1.6"
		try:
			current = self.cwd

			self.cwd = os.path.join(self.cwd, dir)
			cur = os.path.join(self.cwd, WSCRIPT_FILE)

			mod = Utils.load_module(cur)
			if hasattr(mod, 'set_options'):
				mod.set_options(option_group or self)

		finally:
			self.cwd = current

	def tool_options(self, *k, **kw):
		Utils.python_24_guard()

		if not k[0]:
			raise Utils.WscriptError('invalid tool_options call %r %r' % (k, kw))
		tools = Utils.to_list(k[0])

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

	def parse_args(self, args=None):
		parse_args_impl(self.parser, args)

