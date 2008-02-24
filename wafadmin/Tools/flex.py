#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006
# Thomas Nagy, 2006-2008

"Flex processing"

import Object

def decide_ext(self, node):
	if 'cxx' in self.features: return '.lex.cc'
	else: return '.lex.c'

Object.declare_chain(
	name = 'flex',
	action = '${FLEX} -o${TGT} ${FLEXFLAGS} ${SRC}',
	ext_in = '.l',
	ext_out = decide_ext
)

def detect(conf):
	flex = conf.find_program('flex', var='FLEX')
	if not flex: conf.fatal("flex was not found")
	v = conf.env
	v['FLEXFLAGS'] = ''

