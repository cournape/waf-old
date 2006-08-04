#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import Action, Common, Object, Task, Params, os
from Params import debug, error, trace, fatal

bison_str = 'cd ${SRC[0].bld_dir(env)} && ${BISON} ${BISONFLAGS} ${SRC[0].abspath()}'

def yc_file(self, node):
	yctask = self.create_task('bison', nice=4)
	yctask.set_inputs(node)

	# figure out what nodes bison will build
	sep=node.m_name.rfind(os.extsep)
	endstr = node.m_name[sep+1:]
	if len(endstr) > 1:
		endstr = endstr[1:]
	else:
		endstr = ""
	# set up the nodes
	newnodes = [node.change_ext('.tab.c' + endstr)]
	if "-d" in self.env['BISONFLAGS']:
		newnodes.append(node.change_ext('.tab.h'+endstr))
	yctask.set_outputs(newnodes)
	
	task = self.create_task(self.m_type_initials)
	task.set_inputs(yctask.m_outputs[0])
	task.set_outputs(node.change_ext('.tab.o'))

def setup(env):
	# create our action here
	Action.simple_action('bison', bison_str, color='BLUE')

	# register the hook for use with cppobj and ccobj
	Object.hook('cpp', '.y', yc_file)
	Object.hook('cpp', '.yc', yc_file)
	Object.hook('cc', '.y', yc_file)
	Object.hook('cc', '.yc', yc_file)

def detect(conf):
	bison = conf.checkProgram('bison', var='BISON')
	if not bison: return 0
	v = conf.env
	v['BISON']      = bison
	v['BISONFLAGS'] = '-d'
	return 1

