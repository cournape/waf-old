#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

"Bison processing"

import Object

def decide_ext(self, node):
	c_ext = '.tab.c'
	if node.m_name.endswith('.yc'): c_ext = '.tab.cc'
	if '-d' in self.env['BISONFLAGS']:
		return [c_ext, c_ext.replace('c', 'h')]
	else:
		return c_ext

Object.declare_chain(
	name = 'bison',
	action = 'cd ${SRC[0].bld_dir(env)} && ${BISON} ${BISONFLAGS} ${SRC[0].abspath()} -o ${TGT[0].m_name}',
	ext_in = ['.y', '.yc'],
	ext_out = decide_ext
)

def detect(conf):
	bison = conf.find_program('bison', var='BISON')
	if not bison: conf.fatal("bison was not found")
	v = conf.env
	v['BISONFLAGS'] = '-d'

