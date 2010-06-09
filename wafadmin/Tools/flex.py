#!/usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006
# Thomas Nagy, 2006-2010 (ita)

"Flex processing"

import wafadmin.TaskGen

def decide_ext(self, node):
	if 'cxx' in self.features:
		return '.lex.cc'
	return '.lex.c'

wafadmin.TaskGen.declare_chain(
	name = 'flex',
	rule = '${FLEX} -o${TGT} ${FLEXFLAGS} ${SRC}',
	ext_in = '.l',
	decider = decide_ext,
)

def configure(conf):
	conf.find_program('flex', var='FLEX')

