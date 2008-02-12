#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

"Flex processing"

import Action, Object
from Params import fatal
from Params import set_globals

flex_str = '${FLEX} -o${TGT} ${FLEXFLAGS} ${SRC}'
EXT_FLEX = ['.l']

# we register our extensions to global variables
set_globals('EXT_FLEX_C', '.lex.c')
set_globals('EXT_FLEX_CC', '.lex.cc')
set_globals('EXT_FLEX_OUT', '.lex.o')

def l_file(self, node):
	if self.__class__.__name__ == 'ccobj':
		ext = self.env['EXT_FLEX_C']
	elif self.__class__.__name__ == 'cppobj':
		ext = self.env['EXT_FLEX_CC']
	else:
		fatal('neither c nor c++ for flex.py')

	obj_ext = self.env['EXT_FLEX_OUT']

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

