#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

"""
Nasm processing
"""

import os
from wafadmin import TaskGen, Task, Utils
from wafadmin.TaskGen import before, extension

nasm_str = '${NASM} ${NASM_FLAGS} ${_INCFLAGS} ${SRC} -o ${TGT}'

@feature('asm')
@before('apply_link')
def apply_nasm_vars(self):
	self.env.append_value('NASM_FLAGS', self.to_list(getattr(self, 'nasm_flags', [])))

@extension('.s', '.S', '.asm', '.ASM', '.spp', '.SPP')
def nasm_file(self, node):
	return self.create_compiled_task('nasm', node)

# create our action here
Task.task_factory('nasm', nasm_str, color='BLUE', ext_out='.o')

def configure(conf):
	nasm = conf.find_program(['nasm', 'yasm'], var='NASM')

