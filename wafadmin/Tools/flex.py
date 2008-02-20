#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

"Flex processing"

import Action, Object
from Params import fatal

flex_str = '${FLEX} -o${TGT} ${FLEXFLAGS} ${SRC}'
EXT_FLEX = ['.l']

def l_file(self, node):
	if self.__class__.__name__ == 'cppobj': ext = '.lex.cc'
	else: ext = '.lex.c'

	out_source = node.change_ext(ext)

	ltask = self.create_task('flex')
	ltask.set_inputs(node)
	ltask.set_outputs(out_source)

	# make the source produced as 'to be processed'
	self.allnodes.append(out_source)

def setup(bld):
	# create our action here
	Action.simple_action('flex', flex_str, color='BLUE', prio=40)
	# register the hook
	Object.declare_extension(EXT_FLEX, l_file)

def detect(conf):
	flex = conf.find_program('flex', var='FLEX')
	if not flex: conf.fatal("flex was not found")
	v = conf.env
	v['FLEX']      = flex
	v['FLEXFLAGS'] = ''

