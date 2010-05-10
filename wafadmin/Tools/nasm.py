#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008

"""
Nasm processing
"""

import os
import TaskGen, Task, Utils
from TaskGen import taskgen, before, extension

nasm_str = '${NASM} ${NASM_FLAGS} ${_INCFLAGS} ${SRC} -o ${TGT}'

EXT_NASM = ['.s', '.S', '.asm', '.ASM', '.spp', '.SPP']

@feature('asm')
@before('apply_link')
def apply_nasm_vars(self):
	if hasattr(self, 'nasm_flags'):
		for flag in self.to_list(self.nasm_flags):
			self.env.append_value('NASM_FLAGS', flag)

@extension(*EXT_NASM)
def nasm_file(self, node):
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

 	task = self.create_task('nasm', node, node.change_ext(obj_ext))
	self.compiled_tasks.append(task)

# create our action here
Task.simple_task_type('nasm', nasm_str, color='BLUE', ext_out='.o')

def detect(conf):
	nasm = conf.find_program(['nasm', 'yasm'], var='NASM')

