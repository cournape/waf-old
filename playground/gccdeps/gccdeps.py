#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import Task, Utils
import preproc

ccvars = "CC CCFLAGS CPPFLAGS _CCINCFLAGS _CCDEFFLAGS".split()
cxxvars = "CXX CXXFLAGS CPPFLAGS _CXXINCFLAGS _CXXDEFFLAGS".split()

def c_fun(tsk, vars):
	vars = [tsk.env.get_flat(k) for k in vars]
	vars.append('-M')
	vars.append(tsk.inputs[0].abspath(tsk.env))
	return " ".join(vars)

def scan(self):
	if self.__class__.__name__ == 'cxx':
		vars = cxxvars
	else:
		vars = ccvars

	try:
		deps = Utils.cmd_output(c_fun(self, vars))
	except ValueError:
		# the code does not compile, let it fail for real to display the errors
		return ([], [])

	deps = deps.replace('\\\n', '')
	deps = ":".join(deps.split(':')[1:])
	deps = deps.split()

	nodes = [self.generator.bld.root.find_resource(x) for x in deps]
	# we should display which nodes cannot be found
	nodes = [x for x in nodes if x]

	return (nodes, [])

t = Task.TaskBase.classes
if 'cc' in t:
	t['cc'].scan = scan

if 'cxx' in t:
	t['cxx'].scan = scan

