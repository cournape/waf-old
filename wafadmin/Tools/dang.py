#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Demo: this hook is called when the class cppobj encounters a '.coin' file: X{.coin -> .cpp -> .o}"

import Object

Object.declare_chain(
	name = 'dang',
	action = '${DANG} ${SRC} > ${TGT}',
	ext_in = ['.coin'],
	ext_out = '.cpp'
)

def detect(conf):
	dang = conf.find_program('cat', var='DANG')
	if not dang: conf.fatal('cannot find the program "cat"')

