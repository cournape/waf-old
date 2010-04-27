#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

"Cython"

import TaskGen

def cscan(self):
	return ((), ())

TaskGen.declare_chain(name='cython', rule='${CYTHON} ${CYTHONFLAGS} ${SRC} -o ${TGT}', ext_in=['.pyx'], ext_out=['.c'], scan=cscan)

def detect(conf):
	conf.find_program('cython', var='CYTHON', mandatory=True)

