#!/usr/bin/env python
# encoding: utf-8
# go.py - Waf tool for the Go programming language
# By: Tom Wambold <tom5760@gmail.com>

import platform

import Task
import Utils
from TaskGen import feature, extension, before, after

if platform.machine() == 'x86_64':
	GO_COMPILER = '6g'
	GO_LINKER = '6l'
	GO_EXTENSION = '.6'
elif platform.machine() == 'i386':
	GO_COMPILER = '8g'
	GO_LINKER = '8l'
	GO_EXTENSION = '.8'
else:
	raise OSError('Unsupported platform ' + platform.machine())

GO_PACK = 'gopack'
GO_PACK_EXTENSION = '.a'

Task.simple_task_type('gocompile', '${GOC} ${GOCFLAGS} -o ${TGT} ${SRC}')
Task.simple_task_type('gopack', '${GOP} grc ${TGT} ${SRC}')
Task.simple_task_type('golink', '${GOL} ${GOLFLAGS} -o ${TGT} ${SRC}')

def detect(conf):
	conf.find_program(GO_COMPILER, var='GOC', mandatory=True)
	conf.find_program(GO_LINKER, var='GOL', mandatory=True)
	conf.find_program(GO_PACK, var='GOP', mandatory=True)

@feature('go')
@before('apply_core')
def apply_go(self):
	self.go_nodes = []
	self.go_compile_task = None
	self.go_link_task = None
	self.go_package_task = None

@extension('.go')
def compile_go(self, node):
	self.go_nodes.append(node)

@feature('go')
@after('apply_core')
def apply_compile_go(self):
	self.go_compile_task = self.create_task('gocompile', self.go_nodes,
			[self.path.find_or_declare(self.target + GO_EXTENSION)])

@feature('gopackage', 'goprogram')
@after('apply_compile_go')
def apply_goinc(self):
	names = self.to_list(getattr(self, 'uselib_local', []))
	for name in names:
		obj = self.name_to_obj(name)
		if not obj:
			raise Utils.WafError('object %r was not found in uselib_local '
					'(required by %r)' % (lib_name, self.name))
		obj.post()
		self.go_compile_task.set_run_after(obj.go_package_task)
		self.go_compile_task.deps_nodes.extend(obj.go_package_task.outputs)
		self.env.append_unique('GOCFLAGS', '-I ' + obj.path.abspath(obj.env))
		self.env.append_unique('GOLFLAGS', '-L ' + obj.path.abspath(obj.env))

@feature('gopackage')
@after('apply_goinc')
def apply_gopackage(self):
	self.go_package_task = self.create_task('gopack',
			self.go_compile_task.outputs[0],
			self.path.find_or_declare(self.target + GO_PACK_EXTENSION))
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

