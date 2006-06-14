#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan, cpp
from Params import debug, error, trace, fatal

# first, we define an action to build something
flex_vardeps = ['FLEX']
def flex_build(task):
	reldir = task.m_inputs[0].cd_to()
	src = task.m_inputs[0].bldpath()
	tgt = src[:len(src)-2]+'.lex.cc'
	cmd = '%s -o%s %s %s' % (task.m_env['FLEX'], os.path.join(reldir, tgt), task.m_env['FLEXFLAGS'], src)
	return Runner.exec_command(cmd)
lexact = Action.GenAction('flex', flex_vardeps)
lexact.m_function_to_run = flex_build

def l_file(obj, node):

	fi = obj.file_in

	ltask = obj.create_task('flex', obj.env, 4)

	base, ext = os.path.splitext(node.m_name)
	ltask.m_inputs  = fi(node.m_name)
	ltask.m_outputs = fi(base+'.lex.cc')

	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = ltask.m_outputs
	cpptask.m_outputs = fi(base+'.lex.o')
	obj.p_compiletasks.append(cpptask)

def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['flex']='\033[94m'

	# register the hook for use with cppobj
	if not env['handlers_cppobj_.l']: env['handlers_cppobj_.l'] = l_file

def detect(conf):
	flex = conf.checkProgram('flex')
	if not flex: return 0
	conf.env['FLEX'] = flex
	conf.env['FLEXFLAGS'] = ''
	return 1

