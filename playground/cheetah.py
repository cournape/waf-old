#!/usr/bin/env python
# encoding: utf-8
# hhasemann 2008

import sys, os, os.path
from TaskGen import taskgen, extension
import Task, Utils

def cheetah_build(task):
	from Cheetah.Template import Template

	env = bld.env()
	builddir = task.m_inputs[0].bld_dir(env)
	src = task.m_inputs[0].bldpath(env)
	src_dir = os.path.dirname(src)
	output_file = open(os.path.join(builddir, task.m_outputs[0].m_name), 'w')
	source_data = str(open(src, 'r').read())

	# Change working directory temporarily to source dir because
	# "#include" misbehaves if we don't
	olddir = os.getcwd()
	os.chdir(src_dir)
	# This is for '#extends' to work
	sys.path = [os.path.abspath(".")] + sys.path

	tclass = Template.compile(source_data)
	output_file.write(str(tclass(namespaces=[task.cheetah_namespace])))
	output_file.close()

	sys.path = sys.path[1:]
	os.chdir(olddir)
	return 0

Task.task_type_from_func('cheetah', func=cheetah_build)

@taskgen
@extension('.templ')
def cheetah_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('cheetah', self.env)
	task.set_inputs(node)
	task.set_outputs(node.change_ext(''))
	task.cheetah_namespace = getattr(self, 'namespace', '') or raise Utils.WafError('the cheetah transformation require an attribute "namespace"')

def detect(conf):
	try:
		from Cheetah.Template import Template
	except ImportError:
		conf.fatal('python-cheetah was not found')
	else:
		conf.check_message('Cheetah engine', '', 'found')

