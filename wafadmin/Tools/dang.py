#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Demo: this hook is called when the class cppobj encounters a '.coin' file: X{.coin -> .cpp -> .o}"

import Action, Object

dang_str = '${DANG} ${SRC} > ${TGT}'
"our action"

EXT_DANG = ['.coin']

def coin_file(self, node):
	"""Create the task for the coin file
	the action 'dang' above is called for this
	the number '4' in the parameters is the priority of the task (optional)
	 - lower number means high priority
	 - odd means the task can be run in parallel with others of the same priority number
	"""
	out_source = node.change_ext('.cpp')

	cointask = self.create_task('dang')
	cointask.set_inputs(node)
	cointask.set_outputs(out_source)

	# the out file is to be processed elsewhere
	self.allnodes.append(out_source)

	# for debugging a task, use the following code:
	#cointask.debug(1)

def setup(bld):
	# create our action, for use with coin_file
	Action.simple_action('dang', dang_str, color='BLUE', prio=40)

	# register the hook
	Object.declare_extension(EXT_DANG, coin_file)

def detect(conf):
	dang = conf.find_program('cat', var='DANG')
	if not dang: return

