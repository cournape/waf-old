#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)

"""
C# support
"""

from waflib import TaskGen, Utils, Task, Options, Logs
from TaskGen import before, after, feature
from waflib.Tools import ccroot

ccroot.USELIB_VARS['cs'] = set(['FLAGS', 'ASSEMBLIES', 'RESOURCES'])

@feature('cs')
@after('apply_uselib_cs')
@before('process_source')
def apply_cs(self):
	try: self.meths.remove('process_source')
	except ValueError: pass

	# process the flags for the assemblies
	for i in self.to_list(self.assemblies) + self.env['ASSEMBLIES']:
		self.env.append_unique('_ASSEMBLIES', '/r:'+i)

	# process the flags for the resources
	for i in self.to_list(self.resources):
		self.env.append_unique('_RESOURCES', '/resource:'+i)

	# what kind of assembly are we generating?
	self.env['_TYPE'] = getattr(self, 'type', 'exe')

	# additional flags
	self.env.append_unique('_FLAGS', self.to_list(self.flags))
	self.env.append_unique('_FLAGS', self.env.FLAGS)

	# process the sources
	nodes = [self.path.find_resource(i) for i in self.to_list(self.source)]
	self.create_task('mcs', nodes, self.path.find_or_declare(self.target))

Task.task_factory('mcs', '${MCS} ${SRC} /target:${_TYPE} /out:${TGT} ${_FLAGS} ${_ASSEMBLIES} ${_RESOURCES}', color='YELLOW')

def configure(conf):
	csc = getattr(Options.options, 'cscbinary', None)
	if csc:
		conf.env.MCS = csc
	conf.find_program(['gmcs', 'mcs'], var='MCS')

def options(opt):
	opt.add_option('--with-csc-binary', type='string', dest='cscbinary')

