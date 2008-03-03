#! /usr/bin/env python
# encoding: utf-8
# Sebastian Schlingmann, 2008
# Thomas Nagy, 2008 (ita)

import Object

Object.declare_chain(
	name = 'luac',
	action = '${LUAC} -s -o ${TGT} ${SRC}',
	ext_in = '.lua',
	ext_out = '.luac',
	reentrant = 0,
	install = "Object.install_results('PREFIX', 'luac/', 0644)", # TODO predefined functions ?
)

class luaobj(Object.task_gen):
	def __init__(self):
		Object.task_gen.__init__(self)
		self.chmod = 0755
		self.inst_var = ''
		self.inst_dir = ''
Object.register('lua', luaobj)

def detect(conf):
	luac = conf.find_program('luac', var='LUAC')
	if not luac: conf.fatal('cannot find the compiler "luac"')

