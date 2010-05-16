#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

"as and gas"

import os, sys
import Task
from TaskGen import extension

as_str = '${AS} ${ASFLAGS} ${_INCFLAGS} ${SRC} -o ${TGT}'
Task.simple_task_type('asm', as_str, 'PINK', ext_out='.o')

@extension('.s', '.S', '.asm', '.ASM', '.spp', '.SPP')
def asm_hook(self, node):
	# create the compilation task: cpp or cc
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

	task = self.create_task('asm', node, node.change_ext(obj_ext))
	self.compiled_tasks.append(task)

def configure(conf):
	conf.find_program(['gas', 'as', 'gcc'], var='AS')

