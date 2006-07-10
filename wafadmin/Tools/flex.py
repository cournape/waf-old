#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import Action, Common, Object, Task, Params
from Params import debug, error, trace, fatal

flex_str = '${FLEX} -o ${TGT} ${FLEXFLAGS} ${SRC}'

def l_file(obj, node):
	ltask = obj.create_task('flex', obj.env, 4)
	ltask.set_inputs(node)
	ltask.set_outputs(node.change_ext('.lex.cc'))

	cpptask = obj.create_task('cpp', obj.env)
	cpptask.set_inputs(ltask.m_outputs)
	cpptask.set_outputs(node.change_ext('.lex.o'))
	obj.p_compiletasks.append(cpptask)

def setup(env):
	# create our action here
	Action.simple_action('flex', flex_str, color='BLUE')

	# register the hook for use with cppobj
	env['hooks_cppobj_.l'] = l_file

def detect(conf):
	flex = conf.checkProgram('flex', var='FLEX')
	if not flex: return 0
	v = conf.env
	v['FLEX']      = flex
	v['FLEXFLAGS'] = ''
	return 1

