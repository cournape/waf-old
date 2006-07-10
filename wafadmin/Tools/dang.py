#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import Action, Common, Object, Task, Params
from Params import debug, error, trace, fatal

dang_str = '${DANG} ${SRC} > ${TGT}'

# This function (hook) is called when the class cppobj encounters a '.coin' file
# .coin -> .cpp -> .o
def coin_file(obj, node):
	# Create the task for the coin file
	# the action 'dang' above is called for this
	# the number '4' in the parameters is the priority of the task
	# * lower number means high priority
	# * odd means the task can be run in parallel with others of the same priority number
	cointask = obj.create_task('dang', nice=4)
	cointask.set_inputs(node)
	cointask.set_outputs(node.change_ext('.cpp'))

	# now we also add the task that creates the object file ('.o' file)
	cpptask = obj.create_task('cpp')
	cpptask.set_inputs(cointask.m_outputs)
	cpptask.set_outputs(node.change_ext('.o'))

	# for debugging a task, use the following code:
	#cointask.debug(1)

def setup(env):
	# create our action, for use with coin_file
	Action.simple_action('dang', dang_str, color='BLUE')

	# register the hook for use with cppobj
	env.hook('cppobj', '.coin', coin_file)

def detect(conf):
	dang = conf.checkProgram('cat', var='CAT')
	if not dang: return 0
	conf.env['DANG'] = dang
	return 1

