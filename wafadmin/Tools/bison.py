#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

"Bison processing"

import Action, Object, os

bison_str = 'cd ${SRC[0].bld_dir(env)} && ${BISON} ${BISONFLAGS} ${SRC[0].abspath()} -o ${TGT[0].m_name}'

EXT_BISON = ['.y', '.yc']

# we register our extensions to global variables
EXT_BISON_C = '.tab.c'

def yc_file(self, node):
	c_ext = EXT_BISON_C
	if 'cxx' in self.features: c_ext += 'pp'
	h_ext = c_ext.replace('.c', '.h')

	# figure out what nodes bison will build TODO simplify
	sep = node.m_name.rfind(os.extsep)
	endstr = node.m_name[sep+1:]
	if len(endstr) > 1:
		endstr = endstr[1:]
	else:
		endstr = ""

	# set up the nodes
	c_node = node.change_ext(c_ext + endstr)
	if '-d' in self.env['BISONFLAGS']:
		newnodes = [c_node, node.change_ext(h_ext+endstr)]
	else:
		newnodes = [c_node]

	yctask = self.create_task('bison')
	yctask.set_inputs(node)
	yctask.set_outputs(newnodes)

	self.allnodes.append(newnodes[0])

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

