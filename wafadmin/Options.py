#!/usr/bin/env python
# encoding: utf-8
# Scott Newton, 2005 (scottn)
# Thomas Nagy, 2006-2010 (ita)

"Custom command-line options"

import os, types, tempfile, optparse
import Logs, Utils, Base

cmds = 'distclean configure build install clean uninstall check dist distcheck'.split()

options = {}
"""A dictionary of options received from parsing"""
commands = []
"""List of commands to execute"""

launch_dir = ''
"""Where Waf was executed"""
run_dir = ''
"""The wscript file to use as the entry point"""
top_dir = ''
"""project directory (top), if the project was configured"""
out_dir = ''
"""build directory (out), if the project was configured"""
waf_dir = ''
"""directory for the waf modules"""

local_repo = ''
"""local repository for the plugins"""
remote_repo = 'http://waf.googlecode.com/svn/'
"""remote directory for the plugins"""

lockfile = os.environ.get('WAFLOCK', '.lock-waf')
try: cache_global = os.path.abspath(os.environ['WAFCACHE'])
except KeyError: cache_global = ''
platform = Utils.unversioned_sys_platform()


class opt_parser(optparse.OptionParser):
	def __init__(self):
		optparse.OptionParser.__init__(self, conflict_handler="resolve", version = 'waf %s (%s)' % (Base.WAFVERSION, Base.WAFREVISION))

		self.formatter.width = Logs.get_term_cols()
		p = self.add_option

		jobs = Utils.job_count()
		p('-j', '--jobs',     dest='jobs',    default=jobs, type='int', help='amount of parallel jobs (%r)' % jobs)
		p('-k', '--keep',     dest='keep',    default=False, action='store_true', help='keep running happily on independent task groups')
		p('-v', '--verbose',  dest='verbose', default=0,     action='count', help='verbosity level -v -vv or -vvv [default: 0]')
		p('--nocache',        dest='nocache', default=False, action='store_true', help='ignore the WAFCACHE (if set)')
		p('--zones',          dest='zones',   default='',    action='store', help='debugging zones (task_gen, deps, tasks, etc)')
		p('-p', '--progress', dest='progress_bar', default=0, action='count', help= '-p: progress bar; -pp: ide output')
		p('--targets',        dest='compile_targets', default='', action='store', help='build given task generators, e.g. "target1,target2"')

		p('-d', '--download', dest='dl_tools', default='', action='store', help='download a plugin, e.g. "java:1.1,c:1.2"')

		gr = optparse.OptionGroup(self, 'configuration options')
		self.add_option_group(gr)

		#gr.add_option('-b', '--blddir', action  = 'store', default = '', help    = 'build dir for the project (configuration)', dest    = 'blddir')
		#gr.add_option('-s', '--srcdir', action  = 'store', default = '', help    = 'src dir for the project (configuration)', dest    = 'srcdir')

		default_prefix = os.environ.get('PREFIX')
		if not default_prefix:
			if platform == 'win32': default_prefix = tempfile.gettempdir()
			else: default_prefix = '/usr/local/'
		gr.add_option('--prefix', dest='prefix', default=default_prefix, help='installation prefix (configuration) [default: %r]' % default_prefix)

		default_destdir = os.environ.get('DESTDIR', '')
		gr = optparse.OptionGroup(self, 'installation options')
		self.add_option_group(gr)
		gr.add_option('--destdir', help='installation root [default: %r]' % default_destdir, default=default_destdir, dest='destdir')
		gr.add_option('-f', '--force', dest='force', default=False, action='store_true', help='force file installation')

	def get_usage(self):
		cmds_str = {}
		for cls in Base.classes:
			if not cls.cmd:
				continue

			s = cls.__doc__ or ''
			cmds_str[cls.cmd] = s

		if Base.g_module:
			for (k, v) in Base.g_module.__dict__.items():
				if k in ['options', 'init', 'shutdown']:
					continue

				if type(v) is type(Base.create_context):
					if v.__doc__ and not k.startswith('_'):
						cmds_str[k] = v.__doc__

		just = 0
		for k in cmds_str:
			just = max(just, len(k))

		lst = ['  %s: %s' % (k.ljust(just), v) for (k, v) in cmds_str.items()]
		lst.sort()
		ret = '\n'.join(lst)

		return '''waf [command] [options]

Main commands (example: ./waf build -j4)
%s
''' % ret


class OptionsContext(Base.Context):
	"""Collects custom options from wscript files and parses the command line.
	Sets the global Options.commands and Options.options attributes."""

	cmd = ''
	fun = 'options'

	def __init__(self):
		super(self.__class__, self).__init__()
		self.parser = opt_parser()

	# pass through to optparse
	def add_option(self, *k, **kw):
		self.parser.add_option(*k, **kw)
	def add_option_group(self, *k, **kw):
		return self.parser.add_option_group(*k, **kw)
	def get_option_group(self, opt_str):
		return self.parser.get_option_group(opt_str)

	def tool_options(self, tool_list, *k, **kw):
		#if not k[0]:
		#	raise Utils.WscriptError('invalid tool_options call %r %r' % (k, kw))
		tools = Utils.to_list(tool_list)

		path = Utils.to_list(kw.get('tooldir', ''))

		for tool in tools:
			module = Base.load_tool(tool, path)
			try:
				fun = module.options
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

		if options.destdir:
			options.destdir = os.path.abspath(os.path.expanduser(options.destdir))

	def finalize(self):
		self.parse_args()

