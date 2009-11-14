#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Demo: '.coin' files are converted into cpp files using 'cat': {.coin -> .cpp -> .o}"

import TaskGen

TaskGen.declare_chain(
	name = 'copy',
	action = '${COPY} ${SRC} ${TGT}',
	ext_in = '.coin',
	ext_out = '.cpp',
	reentrant = False
)

def detect(conf):
	#dang = conf.find_program('cat', var='DANG')
	#if not dang: conf.fatal('cannot find the program "cat"')
	import os
	conf.env['COPY'] = os.getcwd() + os.sep + "cp.py"

