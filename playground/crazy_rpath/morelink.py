#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

import os
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
@after('apply_link')
@before('default_link_install', 'apply_vnum')
def no_rpath(self):

	if self.link_task.__class__.__name__ != 'cc_link':
		return

	name = get_target_name(self).replace('.so', '___.so')
	tsk = self.create_task('inst_cc')
	tsk.inputs = self.link_task.inputs
	tsk.set_outputs(self.path.find_or_declare(name))

	tsk.set_run_after(self.link_task)
	tsk.env = self.link_task.env
	self.link_task.env = self.link_task.env.copy()

	env = self.link_task.env

	self.meths.remove('default_link_install')
	self.meths.remove('apply_vnum')
	if not getattr(self, 'vnum', None):
		self.bld.install_as(self.install_path + '/' + self.link_task.outputs[0].name, tsk.outputs[0], env=self.env, chmod=self.chmod)
		return


	# following is from apply_vnum
	link = self.link_task
	nums = self.vnum.split('.')
	node = link.outputs[0]

	libname = node.name
	if libname.endswith('.dylib'):
		name3 = libname.replace('.dylib', '.%s.dylib' % self.vnum)
		name2 = libname.replace('.dylib', '.%s.dylib' % nums[0])
	else:
		name3 = libname + '.' + self.vnum
		name2 = libname + '.' + nums[0]

	if self.env.SONAME_ST:
		v = self.env.SONAME_ST % name2
		self.env.append_value('LINKFLAGS', v.split())

	bld = self.bld
	nums = self.vnum.split('.')

	path = self.install_path
	if not path: return

	bld.install_as(path + os.sep + name3, tsk.outputs[0], env=self.env) # not the link task node
	bld.symlink_as(path + os.sep + name2, name3)
	bld.symlink_as(path + os.sep + libname, name3)

	# the following task is just to enable execution from the build dir :-/
	tsk = self.create_task('vnum')
	tsk.set_inputs([node])
	tsk.set_outputs(node.parent.find_or_declare(name2))

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

