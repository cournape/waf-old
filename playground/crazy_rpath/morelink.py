#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import TaskGen
from TaskGen import feature, after, before
from ccroot import get_target_name
import Constants
import Task

cc = Task.TaskBase.classes['cc_link']
class inst_cc(cc):
	"""identical to the link task except that it only runs at install time"""
	def runnable_status(self):
		#if not self.generator.bld.is_install:
		#	return Constants.SKIP_ME
		return Task.Task.runnable_status(self)

old = TaskGen.task_gen.apply_link

@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_link')
@before('default_link_install', 'apply_vnum')
def no_rpath(self):

	name = get_target_name(self).replace('.so', '__.so')
	tsk = self.create_task('inst_cc')
	tsk.inputs = self.link_task.outputs
	tsk.set_outputs(self.path.find_or_declare(name))

	tsk.set_run_after(self.link_task)
	tsk.env = self.link_task.env
	self.link_task.env = self.link_task.env.copy()

	env = self.link_task.env

	self.rpath_task = tsk

	if not getattr(self, 'vnum', None):
	#	if self.install_path:
	#		self.bld.install_as(self.install_path + '/' + rpath, tsk.outputs[0], env=self.env, chmod=0755)
		self.meths.remove('default_link_install')


@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_lib_vars', 'apply_link', 'no_rpath')
@before('apply_obj_vars')
def evil_rpath(self):

	env = self.env
	rpath_st = env['RPATH_ST']
	app = self.link_task.env.append_unique
	for i in self.env['RPATH']:
		if i and rpath_st:
			app('LINKFLAGS', rpath_st % i)

	self.env['RPATH'] = []



