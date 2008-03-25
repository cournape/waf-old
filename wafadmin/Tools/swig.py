#! /usr/bin/env python
# encoding: UTF-8
# Petar Forai
# Thomas Nagy

print """
WARNING: You are using the swig tool!
  This tool is marked as beeing deprecated! use with caution!
  it is not maintained actively
"""

import re
import Action, Scan, Params, Object
from Params import fatal

swig_str = '${SWIG} ${SWIGFLAGS} -o ${TGT[0].bldpath(env)} ${SRC}'

re_1 = re.compile(r'^%module.*?\s+([\w]+)\s*?$', re.M)
re_2 = re.compile('%include "(.*)"', re.M)
re_3 = re.compile('#include "(.*)"', re.M)

class swig_class_scanner(Scan.scanner):
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

swig_scanner = swig_class_scanner()

def i_file(self, node):
	ext = '.swigwrap.c'
	if self.__class__.__name__ == 'cpp_taskgen':
		ext = '.swigwrap.cc'

	variant = node.variant(self.env)

	ltask = self.create_task('swig')
	ltask.set_inputs(node)

	tree = Params.g_build
	def check_rec(task, node_):
		for j in tree.m_depends_on[0][node_]:
			if j.m_name.endswith('.i'):
				check_rec(task, j)
	check_rec(ltask, node)

	# get the name of the swig module to process
	try: modname = Params.g_build.m_raw_deps[0][node][0]
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

Action.simple_action('swig', swig_str, color='BLUE', prio=40)

# register the hook for use with cpp and cc task generators
try: Object.hook('cpp', 'SWIG_EXT', i_file)
except KeyError: pass
try: Object.hook('cc', 'SWIG_EXT', i_file)
except KeyError: pass

def check_swig_version(conf, minver=None):
	"""Check for a minimum swig version  like conf.check_swig_version("1.3.28")
	or conf.check_swig_version((1,3,28)) """
	import pproc as subprocess
	reg_swig = re.compile(r'SWIG Version\s(.*)', re.M)
	proc = subprocess.Popen([conf.env['SWIG'], "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	swig_out = proc.communicate()[0]
	swigver = [int(s) for s in reg_swig.findall(swig_out)[0].split(".")]
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
		conf.check_message('swig version', ">= %s" % (minver_str,), result, option=swigver_full)
	return result

def detect(conf):
	swig = conf.find_program('swig', var='SWIG')
	env = conf.env
	env['SWIG']      = swig
	env['SWIGFLAGS'] = ''
	env['SWIG_EXT']  = ['.swig']
	conf.hook(check_swig_version)

