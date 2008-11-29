#! /usr/bin/env python
# encoding: UTF-8
# Petar Forai
# Thomas Nagy 2008

import re
import Task, Utils
from Configure import conf

swig_str = '${SWIG} ${SWIGFLAGS} ${SRC}'
Task.simple_task_type('swig', swig_str, color='BLUE', before='cc cxx')

re_1 = re.compile(r'^%module.*?\s+([\w]+)\s*?$', re.M)
re_2 = re.compile('%include "(.*)"', re.M)
re_3 = re.compile('#include "(.*)"', re.M)

class swig_class_scanner(object):
	def __init__(self):
		Scan.scanner.__init__(self)
	def scan(self, task, node):
		env = task.m_env
		variant = node.variant(env)
		tree = Params.g_build

		lst_names = []
		lst_src = []

		# read the file
		fi = open(node.abspath(env), 'r')
		content = fi.read()
		fi.close()

		# module name, only for the .swig file
		names = re_1.findall(content)
		if names: lst_names.append(names[0])

		# find .i files (and perhaps .h files)
		names = re_2.findall(content)
		for n in names:
			u = node.m_parent.find_source(n)
			if u: lst_src.append(u)

		# find project headers
		names = re_3.findall(content)
		for n in names:
			u = node.m_parent.find_source(n)
			if u: lst_src.append(u)

		# list of nodes this one depends on, and module name if present
		#print "result of ", node, lst_src, lst_names
		return (lst_src, lst_names)

def i_file(self, node):
	ext = '.swigwrap.c'
	if self.__class__.__name__ == 'cpp_taskgen':
		ext = '.swigwrap.cc'

	variant = node.variant(self.env)

	ltask = self.create_task('swig')
	ltask.set_inputs(node)

	tree = Params.g_build
	def check_rec(task, node_):
		for j in tree.node_deps[0][node_]:
			if j.m_name.endswith('.i'):
				check_rec(task, j)
	check_rec(ltask, node)

	# get the name of the swig module to process
	try: modname = Params.g_build.raw_deps[0][node.id][0]
	except KeyError: return

	# set the output files
	outs = [node.change_ext(ext)]
	# swig generates a python file in python mode TODO: other modes ?
	if '-python' in self.env['SWIGFLAGS']:
		outs.append(node.m_parent.find_build(modname+'.py'))
	elif '-ocaml' in self.env['SWIGFLAGS']:
		outs.append(node.m_parent.find_build(modname+'.ml'))
		outs.append(node.m_parent.find_build(modname+'.mli'))

	ltask.set_outputs(outs)

	# create the build task (c or cpp)
	task = self.create_task(self.m_type_initials)
	task.set_inputs(ltask.m_outputs[0])
	task.set_outputs(node.change_ext('.swigwrap.os'))

@conf
def check_swig_version(conf, minver=None):
	"""Check for a minimum swig version  like conf.check_swig_version('1.3.28')
	or conf.check_swig_version((1,3,28)) """
	reg_swig = re.compile(r'SWIG Version\s(.*)', re.M)

	swig_out = Utils.cmd_output('%s -version' % conf.env['SWIG'])

	swigver = [int(s) for s in reg_swig.findall(swig_out)[0].split('.')]
	if isinstance(minver, basestring):
		minver = [int(s) for s in minver.split(".")]
	if isinstance(minver, tuple):
		minver = [int(s) for s in minver]
	result = (minver is None) or (minver[:3] <= swigver[:3])
	swigver_full = '.'.join(map(str, swigver))
	if result:
		conf.env['SWIG_VERSION'] = swigver_full
	minver_str = '.'.join(map(str, minver))
	if minver is None:
		conf.check_message_custom('swig version', '', swigver_full)
	else:
		conf.check_message('swig version', '>= %s' % (minver_str,), result, option=swigver_full)
	return result

def detect(conf):
	swig = conf.find_program('swig', var='SWIG')
	env = conf.env
	env['SWIG']      = swig
	env['SWIGFLAGS'] = ''
	env['SWIG_EXT']  = ['.swig']

