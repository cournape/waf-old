#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan, cpp
from Params import debug, error, trace, fatal

# first, we define an action to build something
bison_vardeps = ['BISON']
def bison_build(task):
	reldir = task.m_inputs[0].cd_to()
	src = task.m_inputs[0].bldpath()
	tgt = src[:len(src)-3]+'.tab.cc'
	cmd = '%s -b %s %s %s' % (task.m_env['BISON'], os.path.join(reldir, src[:len(src)-3]), task.m_env['BISONFLAGS'], src)
	return Runner.exec_command(cmd)
bisonact = Action.GenAction('bison', bison_vardeps)
bisonact.m_function_to_run = bison_build

def yc_file(obj, node):

	fi = obj.file_in

	yctask = obj.create_task('bison', obj.env, 4)

	base, ext = os.path.splitext(node.m_name)
	yctask.m_inputs  = fi(node.m_name)
	yctask.m_outputs = fi(base+'.tab.cc')

	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = yctask.m_outputs
	cpptask.m_outputs = fi(base+'.tab.o')
	obj.p_compiletasks.append(cpptask)

def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['bison']='\033[94m'

	# register the hook for use with cppobj
	if not env['handlers_cppobj_.yc']: env['handlers_cppobj_.yc'] = yc_file

def detect(conf):
	bison = conf.checkProgram('bison', var='BISON')
	if not bison: return 0
	conf.env['BISON'] = bison
	conf.env['BISONFLAGS'] = '-d'
	return 1

