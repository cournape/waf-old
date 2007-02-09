#! /usr/bin/env python
# encoding: UTF-8
# Petar Forai

"""SWIG file processing. This Tool assumes that the `main' swig file has the `.swig' extension (instead of .i like in the documentation). The reason for this is that one swig file can include others and via this assumption we make things easier."""

import Action
from Params import fatal
from Params import set_globals


swig_str = '${SWIG} ${SWIGFLAGS} -o ${TGT} ${SRC}'


set_globals('EXT_SWIG_I', '.swig')
set_globals('EXT_SWIG_OUT','_swigwrap.cpp')
set_globals('EXT_SWIG_OBJ_OUT','_swigwrap.os')

def i_file(self, node):
	ext = self.env['EXT_SWIG_I']
	out_ext = self.env['EXT_SWIG_OUT']
	obj_ext = self.env['EXT_SWIG_OBJ_OUT']

	ltask = self.create_task('swig', nice=4)
	ltask.set_inputs(node)
	ltask.set_outputs(node.change_ext(out_ext))  

	task = self.create_task(self.m_type_initials)
	task.set_inputs(ltask.m_outputs)

	
	task.set_outputs(node.change_ext(obj_ext))


def setup(env):
	Action.simple_action('swig', swig_str, color='BLUE')

	try: env.hook('cpp', 'SWIG_EXT', i_file)
	except: pass

def detect(conf):
	swig = conf.find_program('swig', var='SWIG')
	if not swig: return 0
	env = conf.env
	env['SWIG']      = swig
	env['SWIGFLAGS'] = ''
	env['SWIG_EXT']  = ['.swig']
	return 1

