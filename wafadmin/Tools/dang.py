#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan, cpp
from Params import debug, error, trace, fatal

# first, we define an action to build something
Action.simple_action('dang', '${DANG} ${SRC} > ${TGT}')

# This function (hook) is called when the class cppobj encounters a '.coin' file
# .coin -> .cpp -> .o
def coin_file(obj, node):

	# this function is used several times
	fi = obj.file_in

	# Create the task for the coin file
	# the action 'dang' above is called for this
	# the number '4' in the parameters is the priority of the task
	# * lower number means high priority
	# * odd means the task can be run in parallel with others of the same priority number
	cointask = obj.create_task('dang', obj.env, 4)

	#base, ext = os.path.splitext(node.m_name)
	cointask.m_inputs  = [node]
	cointask.m_outputs = [node.change_ext('.cpp')]

	# debugging
	#cointask.debug(1)

	# now we also add the task that creates the object file ('.o' file)
	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = cointask.m_outputs
	cpptask.m_outputs = [node.change_ext('.o')]
	obj.p_compiletasks.append(cpptask)

def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['dang']='\033[94m'

	# register the hook for use with cppobj
	if not env['handlers_cppobj_.coin']: env['handlers_cppobj_.coin'] = coin_file

def detect(conf):
	dang = conf.checkProgram('cat', var='CAT')
	if not dang: return 0
	conf.env['DANG'] = dang
	return 1

