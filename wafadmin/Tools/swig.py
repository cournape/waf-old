#! /usr/bin/env python
# encoding: UTF-8
# Petar Forai
# Thomas Nagy

import re
import Action, Scan, Params
from Params import fatal, set_globals

swig_str = '${SWIG} ${SWIGFLAGS} -o ${TGT[0].bldpath(env)} ${SRC}'

set_globals('EXT_SWIG_C','.swigwrap.c')
set_globals('EXT_SWIG_CC','.swigwrap.cc')
set_globals('EXT_SWIG_OUT','.swigwrap.os')

re_1 = re.compile('%module (.*)', re.M)
re_2 = re.compile('%include "(.*.i)"', re.M)
re_3 = re.compile('#include "(.*.i)"', re.M)

class swig_class_scanner(Scan.scanner):
	def __init__(self):
		Scan.scanner.__init__(self)
	def scan(self, node, env):
		variant = node.variant(env)

		lst_names = []
		lst_src = []

		fi = open(node.abspath(env), 'r')
		content = fi.read()
		fi.close()

		names = re_1.findall(content)
		if names: lst_names.append(names[0])

		names = re_2.findall(content)
		for n in names:
			u = node.m_parent.find_source(n)
			if u: lst_src.append(u)

		names = re_3.findall(content)
		for n in names:
			u = node.m_parent.find_source(n)
			if u: lst_src.append(u)

		print lst_src, lst_names
		return (lst_src, lst_names)

swig_scanner = swig_class_scanner()

def i_file(self, node):
	if self.__class__.__name__ == 'ccobj':
		ext = self.env['EXT_SWIG_C']
	elif self.__class__.__name__ == 'cppobj':
		ext = self.env['EXT_SWIG_CC']
	else:
		fatal('neither c nor c++ for swig.py')

	if Params.g_build.needs_rescan(node, self.env):
		swig_scanner.do_scan(node, self.env, hashparams={})

	# get the name of the swig module to process
	variant = node.variant(self.env)
	try: modname = Params.g_build.m_raw_deps[variant][node][0]
	except: return

	# set the output files
	outs = [node.change_ext(ext)]
	# swig generates a python file in python mode TODO: other modes ?
	if '-python' in self.env['SWIGFLAGS']:
		outs.append(node.m_parent.find_build(modname+'.py'))

	# create the swig task
	ltask = self.create_task('swig', nice=4)
	ltask.set_inputs(node)
	ltask.set_outputs(outs)

	# create the build task (c or cpp)
	task = self.create_task(self.m_type_initials)
	task.set_inputs(ltask.m_outputs[0])
	task.set_outputs(node.change_ext(self.env['EXT_SWIG_OUT']))

def setup(env):
	Action.simple_action('swig', swig_str, color='BLUE')

	# register the hook for use with cppobj and ccobj
	try: env.hook('cpp', 'SWIG_EXT', i_file)
	except: pass
	try: env.hook('cc', 'SWIG_EXT', i_file)
	except: pass

def detect(conf):
	swig = conf.find_program('swig', var='SWIG')
	if not swig: return 0
	env = conf.env
	env['SWIG']      = swig
	env['SWIGFLAGS'] = ''
	env['SWIG_EXT']  = ['.swig']
	return 1

