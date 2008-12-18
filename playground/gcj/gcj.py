#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)

import os, re
from Configure import conf
import TaskGen, Task, Utils
from TaskGen import feature, taskgen

class java_taskgen(TaskGen.task_gen):
	def __init__(self, *k, **kw):
		TaskGen.task_gen.__init__(self, *k, **kw)

@taskgen
@feature('java')
def apply_java(self):
	Utils.def_attrs(self, jarname='', jaropts='', classpath='',
		source_root='.', jar_mf_attributes={}, jar_mf_classpath=[])

	nodes_lst = []

	if not self.classpath:
		if not self.env['CLASSPATH']:
			self.env['CLASSPATH'] = '..' + os.pathsep + '.'
	else:
		self.env['CLASSPATH'] = self.classpath

	re_foo = re.compile(self.source)

	source_root_node = self.path.find_dir(self.source_root)

	src_nodes = []
	bld_nodes = []

	prefix_path = source_root_node.abspath()
	for (root, dirs, filenames) in os.walk(source_root_node.abspath()):
		for x in filenames:
			file = root + '/' + x
			file = file.replace(prefix_path, '')
			if file.startswith('/'):
				file = file[1:]

			if re_foo.search(file) > -1:
				node = source_root_node.find_resource(file)
				src_nodes.append(node)

				node2 = node.change_ext(".class")
				bld_nodes.append(node2)

	self.env['OUTDIR'] = source_root_node.abspath(self.env)

	tsk = self.create_task('javac')
	tsk.set_inputs(src_nodes)
	tsk.set_outputs(bld_nodes)

	if self.jarname:
		tsk = self.create_task('jar_create')
		tsk.set_inputs(bld_nodes)
		tsk.set_outputs(self.path.find_or_declare(self.jarname))

		if not self.env['JAROPTS']:
			if self.jaropts:
				self.env['JAROPTS'] = self.jaropts
			else:
				dirs = '.'
				self.env['JAROPTS'] = '-C %s %s' % (self.env['OUTDIR'], dirs)

cls = Task.simple_task_type('gcj', '${GCJ} ${GCJFLAGS} -classpath ${CLASSPATH} -d ${OUTDIR} ${SRC}', before='jar_create')
cls.color = 'BLUE'

def detect(conf):
	conf.find_program('gcj', var='GCJ', path_list=java_path)

