#! /usr/bin/env python
# encoding: UTF-8
# Thomas Nagy 2008

import re
import pproc
import Task, Utils
from TaskGen import feature

DOXY_EXTS = """
.c .cc .cxx .cpp .c++ .C
.h .hh .hxx .hpp .h++ .H
.py .java .cs
.ii .ixx .ipp .i++ .inl
.idl .odl .php .php3 .inc .m .mm
""".split()

def runnable_status(self):
	if not getattr(self, 'pars', None):
		infile = self.inputs[0].abspath(self.env)
		self.pars = read_into_dict(infile)
		if not self.pars.get('OUTPUT_DIRECTORY', None):
			self.pars['OUTPUT_DIRECTORY'] = self.inputs[0].parent.abspath(self.env)
	return Task.Task.runnable_status(self)

def doxy_scan(self):
	def nodes_files_of(node):
		node.__class__.bld.rescan(node)
		for x in node.childs:
			print x
	print nodes_files_of(self.inputs[0].parent)
	return [[], []]

def doxy_run(self):
	code = '\n'.join(['%s = %s' % (x, self.pars[x]) for x in self.pars])
	if not self.env['DOXYFLAGS']:
		self.env['DOXYFLAGS'] = ''
	cmd = Utils.subst_vars('cd %s && ${DOXYGEN} ${DOXYFLAGS} -' % (self.inputs[0].parent.abspath()), self.env)
	proc = pproc.Popen(cmd, shell=True, stdin=pproc.PIPE)
	proc.communicate(code)
	return proc.returncode

cls = Task.task_type_from_func('doxygen', func=doxy_run, vars=['DOXYGEN', 'DOXYFLAGS'])
cls.runnable_status = runnable_status
cls.scan = doxy_scan
cls.color = 'BLUE'
cls.after = 'cxx_link cc_link'
cls.quiet = True

re_join = re.compile(r'\\(\r)*\n', re.M)
re_nl = re.compile('\r*\n', re.M)

def read_into_dict(name):
	f = open(name, 'rb')
	txt = f.read()
	f.close()

	ret = {}

	txt = re_join.sub('', txt)
	lines = re_nl.split(txt)
	vals = []

	for x in lines:
		x.strip()
		if len(x) < 2: continue
		if x[0] == '#': continue
		tmp = x.split('=')
		if len(tmp) < 2: continue
		ret[tmp[0].strip()] = '='.join(tmp[1:]).strip()
	return ret

@feature('doxygen')
def process_doxy(self):
	if not getattr(self, 'doxyfile', None):
		return

	node = self.path.find_resource(self.doxyfile)
	if not node: raise ValueError, 'doxygen file not found'

	# the task instance
	tsk = self.create_task('doxygen')
	tsk.set_inputs(node)

def detect(conf):
	swig = conf.find_program('doxygen', var='DOXYGEN')

