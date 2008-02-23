#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

"Bison processing"

import Action, Object, os

bison_str = 'cd ${SRC[0].bld_dir(env)} && ${BISON} ${BISONFLAGS} ${SRC[0].abspath()} -o ${TGT[0].m_name}'

EXT_BISON = ['.y', '.yc']

def yc_file(self, node):
	c_ext = '.tab.c'
	if node.m_name.endswith('.yc'): c_ext = '.tab.cc'
	h_ext = c_ext.replace('c', 'h')

	# set up the nodes
	c_node = node.change_ext(c_ext)
	if '-d' in self.env['BISONFLAGS']: newnodes = [c_node, node.change_ext(h_ext)]
	else: newnodes = [c_node]

	yctask = self.create_task('bison')
	yctask.set_inputs(node)
	yctask.set_outputs(newnodes)

	self.allnodes.append(c_node)

# create our action here
Action.simple_action('bison', bison_str, color='BLUE', prio=40)
# register the hook
Object.declare_extension(EXT_BISON, yc_file)

def detect(conf):
	bison = conf.find_program('bison', var='BISON')
	if not bison: conf.fatal("bison was not found")
	v = conf.env
	v['BISON']      = bison
	v['BISONFLAGS'] = '-d'

