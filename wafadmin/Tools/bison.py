#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import Action, Common, Object, Task, Params
from Params import debug, error, trace, fatal

bison_str = 'cd ${SRC[0].bld_dir(env)} && ${BISON} ${BISONFLAGS} ${SRC[0].abspath()}'

def yc_file(obj, node):
	yctask = obj.create_task('bison', nice=4)
	yctask.set_inputs(node)
	yctask.set_outputs(node.change_ext('.tab.cc'))

	cpptask = obj.create_task('cpp')
	cpptask.set_inputs(yctask.m_outputs)
	cpptask.set_outputs(node.change_ext('.tab.o'))

def setup(env):
	# create our action here
	Action.simple_action('bison', bison_str, color='BLUE')

	# register the hook for use with cppobj
	env.hook('cppobj', '.y', yc_file)
	env.hook('cppobj', '.yc', yc_file)

def detect(conf):
	bison = conf.checkProgram('bison', var='BISON')
	if not bison: return 0
	v = conf.env
	v['BISON']      = bison
	v['BISONFLAGS'] = '-d'
	return 1

