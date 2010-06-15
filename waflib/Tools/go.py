#!/usr/bin/env python
# encoding: utf-8
# go.py - Waf tool for the Go programming language
# By: Tom Wambold <tom5760@gmail.com>

import platform

import Utils, Task
from TaskGen import feature, extension, after

from waflib.Tools.ccroot import link_task, static_link

class go(Task.Task):
	run_str = '${GOC} ${GOCFLAGS} ${_INCFLAGS} -o ${TGT} ${SRC}'

class gopackage(static_link):
	run_str = '${GOP} grc ${TGT} ${SRC}'

class goprogram(link_task):
	run_str = '${GOL} ${GOLFLAGS} -o ${TGT} ${SRC}'
	inst_to = '${BINDIR}'


def configure(conf):

	def set_def(var, val):
		if not conf.env[var]:
			conf.env[var] = val

	set_def('GO_PLATFORM', platform.machine())

	if conf.env.GO_PLATFORM == 'x86_64':
		set_def('GO_COMPILER', '6g')
		set_def('GO_LINKER', '6l')
	elif conf.env.GO_PLATFORM == 'i386':
		set_def('GO_COMPILER', '8g')
		set_def('GO_LINKER', '8l')

	if not (conf.env.GO_COMPILER or conf.env.GO_LINKER):
		raise conf.fatal('Unsupported platform ' + platform.machine())

	set_def('GO_PACK', 'gopack')
	set_def('gopackage_PATTERN', '%s.a')

	conf.find_program(conf.env.GO_COMPILER, var='GOC')
	conf.find_program(conf.env.GO_LINKER,   var='GOL')
	conf.find_program(conf.env.GO_PACK,     var='GOP')

@extension('.go')
def compile_go(self, node):
	return self.create_compiled_task('go', node)

@feature('gopackage', 'goprogram')
@after('process_source', 'apply_incpaths')
def go_local_libs(self):
	names = self.to_list(getattr(self, 'uselib_local', []))
	for name in names:
		obj = self.bld.name_to_obj(name)
		if not obj:
			raise Utils.WafError('no target of name %r necessary for %r in go uselib local' % (name, self))
		obj.post()
		for tsk in self.tasks:
			tsk.set_run_after(obj.link_task)
			tsk.deps_nodes.extend(obj.link_task.outputs)
		path = obj.link_task.outputs[0].parent.abspath()
		self.env.append_unique('GOCFLAGS', ['-I%s' % path])
		self.env.append_unique('GOLFLAGS', ['-L%s' % path])

"""
@feature('gopackage')
@after('apply_goinc')
def apply_gopackage(self):
	self.go_package_task = self.create_task('gopack',
			self.go_compile_task.outputs[0],
			self.path.find_or_declare(self.target + self.env.GO_PACK_EXTENSION))
	self.go_package_task.set_run_after(self.go_compile_task)
	self.go_package_task.deps_nodes.extend(self.go_compile_task.outputs)

@feature('goprogram')
@after('apply_goinc')
def apply_golink(self):
	self.go_link_task = self.create_task('golink',
			self.go_compile_task.outputs[0],
			self.path.find_or_declare(self.target))
	self.go_link_task.set_run_after(self.go_compile_task)
	self.go_link_task.deps_nodes.extend(self.go_compile_task.outputs)
"""

