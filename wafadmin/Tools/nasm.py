#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008

"""
Nasm processing

obj = bld.create_obj('cc', 'program')
#do not forget to call:
obj.meths += ['apply_nasm_vars']

"""

import os
import Action, Object

nasm_str = '${NASM} ${NASM_FLAGS} ${NASM_INCLUDES} ${SRC} -o ${TGT}'

EXT_NASM = ['.s']

def apply_nasm_vars(self):

	# flags
	if hasattr(self, 'nasm_flags'):
		for flag in self.to_list(self.nasm_flags):
			self.env.append_value('NASM_FLAGS', flag)

	# includes - well, if we suppose it works with c processing
	if hasattr(self, 'includes'):
		for inc in self.to_list(self.includes):
			self.env.append_value('NASM_INCLUDES', '-I %s' % inc.srcpath(self.env))

def nasm_file(self, node):
	o_node = node.change_ext('.o')

	task = self.create_task('nasm')
	task.set_inputs(node)
	task.set_outputs(o_node)

	self.compiled_tasks.append(task)

def setup(bld):
	# create our action here
	Action.simple_action('nasm', nasm_str, color='BLUE', prio=40)
	# register the hook
	Object.declare_extension(EXT_NASM, nasm_file)

def detect(conf):
	nasm = conf.find_program('nasm', var='NASM')
	if not nasm: conf.fatal("could not find nasm, install it or set PATH env var.")

Object.declare_order('apply_nasm_vars', 'apply_link')

