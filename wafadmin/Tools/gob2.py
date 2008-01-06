#! /usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

import Action, Object

gob2_str = '${GOB2} -o ${TGT[0].bld_dir(env)} ${GOB2FLAGS} ${SRC}'

def gob2_file(self, node):
	gob2task = self.create_task('gob2', nice=40)
	gob2task.set_inputs(node)
	gob2task.set_outputs(node.change_ext('.c'))

	task = self.create_task('cc')
	task.set_inputs(gob2task.m_outputs)
	task.set_outputs(node.change_ext('.o'))

def setup(bld):
	# create our action here
	Action.simple_action('gob2', gob2_str, color='BLUE')
	Object.hook('cc', 'GOB2_EXT', gob2_file)

def detect(conf):
	gob2 = conf.find_program('gob2', var='GOB2')
	if not gob2: return
	conf.env['GOB2'] = gob2
	conf.env['GOB2FLAGS'] = ''
	conf.env['GOB2_EXT'] = ['.gob']

