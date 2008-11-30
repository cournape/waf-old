#! /usr/bin/env python
# encoding: UTF-8
# Thomas Nagy 2008

import Task, Utils
from TaskGen import feature

doxy_str = 'cd ${SRC[0].parent.abspath(env)} && ${DOXYGEN} ${DOXYFLAGS} ${SRC[0].abspath(env)}'
cls = Task.simple_task_type('doxygen', doxy_str, color='BLUE')
cls.quiet = True

@feature('doxygen')
def process_doxy(self):
	if not getattr(self, 'doxyfile', None):
		return

	node = self.path.find_resource(self.doxyfile)

	# the task instance
	tsk = self.create_task('doxygen')
	tsk.set_inputs(node)

def detect(conf):
	swig = conf.find_program('doxygen', var='DOXYGEN')

