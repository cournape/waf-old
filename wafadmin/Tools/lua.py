#!/usr/bin/env python
# encoding: utf-8
# Sebastian Schlingmann, 2008
# Thomas Nagy, 2008 (ita)

import TaskGen
from TaskGen import taskgen, feature

TaskGen.declare_chain(
	name = 'luac',
	action = '${LUAC} -s -o ${TGT} ${SRC}',
	ext_in = '.lua',
	ext_out = '.luac',
	reentrant = 0,
	install = 'LUADIR', # env variable
)

@taskgen
@feature('lua')
def init_lua(self):
	self.default_chmod = 0755

def detect(conf):
	luac = conf.find_program('luac', var='LUAC')
	if not luac: conf.fatal('cannot find the compiler "luac"')

