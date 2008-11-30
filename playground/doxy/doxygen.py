#! /usr/bin/env python
# encoding: UTF-8
# Thomas Nagy 2008

import Task, Utils
from TaskGen import feature

doxy_str = '${DOXYGEN} ${DOXYFLAGS} ${SRC}'
cls = Task.simple_task_type('doxygen', doxy_str, color='BLUE')

@feature('doxygen')
def process_doxy(self):
	if not getattr(self, 'doxyfile', None):
		return

	node = self.path.find_resource(self.doxyfile)
	print node

	return

	# the task instance
	tsk = self.create_task('doxygen')
	tsk.set_inputs(node)
	tsk.set_outputs(out_node)
	tsk.module = module
	tsk.env['SWIGFLAGS'] = flags

	if not '-outdir' in flags:
		flags.append('-outdir')
		flags.append(node.parent.abspath(self.env))

	if not '-o' in flags:
		flags.append('-o')
		flags.append(out_node.abspath(self.env))

	# add the language-specific output files as nodes
	# call funs in the dict swig_langs
	for x in flags:
		# obtain the language
		x = x[1:]
		try:
			fun = swig_langs[x]
		except KeyError:
			pass
		else:
			fun(tsk)

	self.allnodes.append(out_node)

def detect(conf):
	swig = conf.find_program('doxygen', var='DOXYGEN')

