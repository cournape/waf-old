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
		if not self.generator.bld.is_install:
			return Constants.SKIP_ME
		return Task.Task.runnable_status(self)

old = TaskGen.task_gen.apply_link

@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_core')
@before('default_link_install')
def apply_link(self):
	"""replace the method apply_link"""
	link = getattr(self, 'link', None)

	if link and link != 'cc_link':
		return old(self)

	rpath = get_target_name(self)
	target = rpath.replace('.so', '_.so')

	tsk = self.create_task('inst_cc')
	outputs = [t.outputs[0] for t in self.compiled_tasks]
	tsk.set_inputs(outputs)
	tsk.set_outputs(self.path.find_or_declare(target))

	rp = self.create_task('cc_link')
	rp.inputs = tsk.inputs
	rp.set_outputs(self.path.find_or_declare(rpath))
	tsk.set_run_after(rp) # to link we need the .so files present
	rp.env = tsk.env.copy()

	# wrong names, we know
	self.rpath_task = tsk
	self.link_task = rp

	if not getattr(self, 'vnum', None):
		if self.install_path:
			self.bld.install_as(self.install_path + '/' + rpath, tsk.outputs[0], env=self.env, chmod=0755)
		self.meths.remove('default_link_install')

@feature('cprogram', 'cshlib', 'cstaticlib')
@after('apply_link')
@before('apply_obj_vars')
def evil_rpath(self):
	"""disable normal rpath processing"""
	rp = self.rpath_task

	# rpath flag mess
	rpath_st = rp.env['RPATH_ST']
	app = rp.env.append_unique
	for i in rp.env['RPATH']:
		if i and rpath_st:
			app('LINKFLAGS', rpath_st % i)

	self.env['RPATH'] = []

