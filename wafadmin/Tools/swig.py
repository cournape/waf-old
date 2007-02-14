#! /usr/bin/env python
# encoding: UTF-8
# Petar Forai

"""SWIG file processing. This Tool assumes that the `main' swig file has the `.swig' extension (instead of .i like in the documentation). The reason for this is that one swig file can include others and via this assumption we make things easier."""

import Action
from Params import fatal
from Params import set_globals



swig_str = '${SWIG} ${SWIGFLAGS} -o ${TGT} ${SRC}'

set_globals('EXT_SWIG_C','.swigwrap.c')
set_globals('EXT_SWIG_CC','.swigwrap.cc')
set_globals('EXT_SWIG_OUT','.swigwrap.os')

def i_file(self, node):
	if self.__class__.__name__ == 'ccobj':
		ext = self.env['EXT_SWIG_C']
	elif self.__class__.__name__ == 'cppobj':
		ext = self.env['EXT_SWIG_CC']
	else:
		fatal('neither c nor c++ for swig.py')

	swig_file = open(node.abspath(), 'r')
	first_line = swig_file.readline()
	swig_file.close()
	if str(first_line).startswith("%module"):
		obj_ext = self.env['EXT_SWIG_OUT']

		ltask = self.create_task('swig', nice=4)
		ltask.set_inputs(node)
		ltask.set_outputs(node.change_ext(ext))

		task = self.create_task(self.m_type_initials)
		task.set_inputs(ltask.m_outputs)
		task.set_outputs(node.change_ext(obj_ext))



def setup(env):
	Action.simple_action('swig', swig_str, color='BLUE')

	# register the hook for use with cppobj and ccobj
	try: env.hook('cpp', 'SWIG_EXT', i_file)
	except: pass
	try: env.hook('cc', 'SWIG_EXT', i_file)
	except: pass

def detect(conf):
	swig = conf.find_program('swig', var='SWIG')
	if not swig: return 0
	env = conf.env
	env['SWIG']      = swig
	env['SWIGFLAGS'] = ''
	env['SWIG_EXT']  = ['.swig']
	return 1

