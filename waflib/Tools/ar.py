#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)

"Create static libraries with ar"

import os, sys
from wafadmin import Task, Utils
from wafadmin.Configure import conf

class static_link(Task.Task):
	color = 'YELLOW'
	run_str = '${AR} ${ARFLAGS} ${AR_TGT_F}${TGT} ${AR_SRC_F}${SRC}'
	ext_in = ['.o']
	def run(self):
		"""remove the output in case it already exists"""
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

