#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import Task, Node
from TaskGen import feature

cls = Task.simple_task_type('tar', '${TAR} ${TAROPTS} ${TGT} ${SRC}', color='RED')
def runnable_status(self):
	if not getattr(self, 'tar_done', None):
		self.tar_done = True
		if not getattr(self.generator, 'start', None) or not instanceof(self.generator.start, Node.Node):
			self.generator.start = self.generator.path
		nodes = [x for x in self.generator.start.find_iter(ex_pat=getattr(self.generator, 'excludes', ''))]
		self.inputs = nodes

		for x in self.outputs:
			try:
				self.inputs.remove(x)
			except ValueError:
				pass
		#print "and the nodes are", nodes

	return Task.Task.runnable_status(self)
cls.runnable_status = runnable_status

def to_string(self):
	tgt_str = ' '.join([a.nice_path(self.env) for a in self.outputs])
	return '%s: %s\n' % (self.__class__.__name__, tgt_str)
cls.__str__ = to_string

@feature('archiver')
def pack(self):
	ar_type = 'tar' # TODO
	tsk = self.create_task('tar')
	tsk.outputs = [self.path.find_or_declare(self.target)]
	tsk.env.append_value('TAROPTS', self.taropts)


