#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)

"Create static libraries with ar"

import os
from waflib import Task
from waflib.Configure import conf

class static_link(Task.Task):
	color   = 'YELLOW'
	run_str = '${AR} ${ARFLAGS} ${AR_TGT_F}${TGT} ${AR_SRC_F}${SRC}'
	inst_to = None
	def run(self):
		"""remove the file before creating it (ar behaviour is to append to the existin file)"""
		try:
			os.remove(self.outputs[0].abspath())
		except OSError:
			pass
		return Task.Task.run(self)

@conf
def find_ar(conf):
	conf.check_tool('ar')

def configure(conf):
	conf.find_program('ar', var='AR')
	conf.env.ARFLAGS = 'rcs'

