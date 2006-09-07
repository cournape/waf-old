#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os
import Action, Common, Object, Task, Params
from Params import debug, error, trace, fatal

class javaobj(Object.genobj):
	s_default_ext = ['.java']
	def __init__(self, type='all', library=0):
		Object.genobj.__init__(self, 'java')

		self.m_type       = type
		self.m_source     = ''
		self.m_target     = ''

	def apply(self):
		source_lst = self.source.split()
		nodes_lst = []

		self.env['CLASSPATH'] = '..:.'

		# first create the nodes corresponding to the sources
		for filename in source_lst:
			base, ext = os.path.splitext(filename)
			node = self.file_in(filename)[0]
			if not ext in self.s_default_ext:
				print "??? ", filename

			task = self.create_task('javac', self.env, 1)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.class'))

def setup(env):
	Object.register('java', javaobj)
	Action.simple_action('javac', '${JAVAC} -classpath ${CLASSPATH} -d ${TGT[0].cd_to(env)} ${SRC}', color='BLUE')

def detect(conf):
	javac = conf.checkProgram('javac', os.environ['PATH'].split(':'))
	if not javac: return 0
	conf.env['JAVAC'] = javac


	conf.env['JAVA_EXT'] = ['.java']
	return 1

