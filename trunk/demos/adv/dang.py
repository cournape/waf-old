#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Demo: '.coin' files are converted into cpp files using 'cat': {.coin -> .cpp -> .o}"

import TaskGen

TaskGen.declare_chain(
	name = 'dang',
	action = '${DANG} ${SRC} > ${TGT}',
	ext_in = '.coin',
	ext_out = '.cpp',
	before = 'cxx cc',
)

def detect(conf):
	dang = conf.find_program('cat', var='DANG', mandatory=True)

