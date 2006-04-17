#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan, cpp
from Params import debug, error, trace, fatal

# first, we define an action to build something
dang_vardeps = ['DANG']
def dang_build(task):
	reldir = task.m_inputs[0].cd_to()
	#src = task.m_inputs[0].m_name
	src = task.m_inputs[0].bldpath()
	tgt = src[:len(src)-5]+'.cpp'
	cmd = '%s %s > %s' % (task.m_env['DANG'], src, os.path.join(reldir, tgt))
	return Runner.exec_command(cmd)
dangact = Action.GenAction('dang', dang_vardeps)
dangact.m_function_to_run = dang_build

# This function is called when the class cppobj encounters a '.coin' file
# .coin -> .cpp -> .o
def coin_file(obj, node):

	# this function is used several times
	fi = obj.file_in

	# we create the task for the coin file
	cointask = obj.create_task('dang', obj.env, 4)

	base, ext = os.path.splitext(node.m_name)
	cointask.m_inputs  = fi(node.m_name)
	cointask.m_outputs = fi(base+'.cpp')

	# debugging
	#cointask.debug(1)

	# now we also add the task that creates the object file ('.o' file)
	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = cointask.m_outputs
	cpptask.m_outputs = fi(base+'.o')
	obj.cpptasks.append(cpptask)

# This function is called when a build process is started 
def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['dang']='\033[94m'

	if not env['handlers_cppobj_.coin']: env['handlers_cppobj_.coin'] = coin_file

def detect(conf):
	dang = conf.checkProgram('cat')
	if not dang: return 0
	conf.env['DANG'] = dang
	return 1

