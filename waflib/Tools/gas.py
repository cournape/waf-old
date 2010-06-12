#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008-2010 (ita)

"as and gas"

import os, sys
import waflib.Tools.ccroot # - leave this
import waflib.Task
from waflib.TaskGen import extension

class asm(waflib.Task.Task):
	color = 'BLUE'
	run_str = '${AS} ${ASFLAGS} ${_INCFLAGS} ${SRC} -o ${TGT}'

@extension('.s', '.S', '.asm', '.ASM', '.spp', '.SPP')
def asm_hook(self, node):
	return self.create_compiled_task('asm', node)

def configure(conf):
	conf.find_program(['gas', 'as', 'gcc'], var='AS')

