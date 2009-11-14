#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2009 (ita)

import datetime
import Task, Build, Options, Constants
from Logs import debug

# assumptions
Task.algotype = Task.MAXPARALLEL
Task.file_deps = Task.extract_deps

def set_options(opt):
	opt.add_option('--bf', type='string', default='', dest='bf', help='space-separated list of specific files to build')

old = Build.BuildContext.flush

def flush(self):
	if not Options.options.bf:
		return old(self)

	lst = Options.options.bf.split(',')

	self.ini = datetime.datetime.now()
	# force the initialization of the mapping name->object in flush
	# name_to_obj can be used in userland scripts, in that case beware of incomplete mapping
	self.task_gen_cache_names = {}
	self.name_to_obj('', self.env)

	debug('build: delayed operation TaskGen.flush() called')

	ln = self.srcnode

	for i in xrange(len(self.task_manager.groups)):
		g = self.task_manager.groups[i]
		self.task_manager.current_group = i
		for tg in g.tasks_gen:
			if not tg.path.is_child_of(ln):
				continue
			tg.post()

	# find the nodes corresponding to the names given
	nodes = []
	alltasks = []
	for i in xrange(len(self.task_manager.groups)):
		g = self.task_manager.groups[i]
		self.task_manager.current_group = i
		for t in g.tasks:
			alltasks.append(t)
			for k in t.outputs:
				if k.name in lst:
					nodes.append(k)
					break

	# and now we must perform a search over all tasks to find what might generate the nodes from the above
	while True:
		newnodes = []
		skipped = []
		for t in alltasks:
			for x in nodes:
				if x in t.outputs:
					newnodes.extend(t.inputs)
					break
			else:
				skipped.append(t)
		alltasks = skipped

		if newnodes:
			nodes = nodes + newnodes
		else:
			break

	# the tasks that need not be executed remain
	for x in alltasks:
		x.hasrun = Constants.SKIPPED

setattr(Build.BuildContext, 'flush', flush)

