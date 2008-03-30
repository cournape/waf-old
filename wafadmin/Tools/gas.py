#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

"as and gas"

import os, sys
import Action
from Object import extension, taskgen, after

EXT_ASM = ['.s', '.S', '.asm', '.ASM', '.spp', '.SPP']

as_str = '${AS} ${ASFLAGS} ${_ASINCFLAGS} ${SRC} -o ${TGT}'
Action.simple_action('asm', as_str, 'PINK', prio=100)

@extension(EXT_ASM)
def asm_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('asm', self.env)
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%s.o' % self.m_type[:2]

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

@taskgen
@after('apply_obj_vars_cc')
@after('apply_obj_vars_cxx')
def asm_incflags(self):
	if self.env['ASINCFLAGS']: self.env['_ASINCFLAGS'] = self.env['ASINCFLAGS']
	if 'cxx' in self.features: self.env['_ASINCFLAGS'] = self.env['_CCINCFLAGS']
	else: self.env['_ASINCFLAGS'] = self.env['_CXXINCFLAGS']

def detect(conf):
	comp = os.environ.get('AS', '')
	if not comp: comp = conf.find_program('as', var='AS')
	if not comp: comp = conf.find_program('gas', var='AS')
	if not comp: comp = conf.env['CC']
	if not comp: return

	v = conf.env
	v['ASFLAGS']  = ''

