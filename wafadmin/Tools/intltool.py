#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"intltool support"

import os, re
import Object, Action, Params, Common, Scan, Utils, Runner
import cc
from Params import fatal, error

# intltool
class intltool_in(Object.genobj):
	def __init__(self):
		Object.genobj.__init__(self, 'other')
		self.source  = ''
		self.destvar = ''
		self.subdir  = ''
		self.flags   = ''
		self.podir   = 'po'
		self.intlcache = '.intlcache'
		self.m_tasks = []

	def apply(self):
		self.env = self.env.copy()
		tree = Params.g_build
		current = tree.m_curdirnode
		for i in self.to_list(self.source):
			node = self.path.find_source(i)

			podirnode = self.path.find_source(self.podir)

			self.env['INTLCACHE'] = os.path.join(self.podir, self.intlcache)
			self.env['INTLPODIR'] = podirnode.srcpath(self.env)
			self.env['INTLFLAGS'] = self.flags

			task = self.create_task('intltool', self.env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext(''))

	def install(self):
		current = Params.g_build.m_curdirnode
		for task in self.m_tasks:
			out = task.m_outputs[0]
			Common.install_files(self.destvar, self.subdir, out.abspath(self.env), self.env)

class intltool_po(Object.genobj):
	def __init__(self, appname='set_your_app_name'):
		Object.genobj.__init__(self, 'other')
		self.chmod = 0644
		self.inst_var = 'LOCALEDIR'
		self.appname = appname
		self.m_tasks=[]

	def apply(self):
		for file in self.path.files():
			(base, ext) = os.path.splitext(file.m_name)
			if ext == '.po':
				node = self.path.find_source(file.m_name)
				task = self.create_task('po', self.env, 10)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.mo'))
							
	def install(self):
		for task in self.m_tasks:
			out = task.m_outputs[0]
			filename = out.m_name
			(langname, ext) = os.path.splitext(filename)
			inst_file = langname + os.sep + 'LC_MESSAGES' + os.sep + self.appname + '.mo'
			Common.install_as(self.inst_var, inst_file, out.abspath(self.env), chmod=self.chmod)

class intltoolobj(cc.ccobj):
	def __init__(self, type='program'):
		cc.ccobj.__init__(self, type)
		self.m_linktask = None
		self.m_latask   = None
		self.want_libtool = -1 # fake libtool here

	def apply_core(self):
		for i in self._marshal_lst:
			node = self.path.find_source(i[0])

			if not node:
				fatal('file not found on intltool obj '+i[0])

			env = self.env.copy()

		# after our targets are created, process the .c files, etc
		cc.ccobj.apply_core(self)

def setup(env):
	Action.simple_action('po', '${POCOM} -o ${TGT} ${SRC}', color='BLUE')
	Action.simple_action('intltool',
		'${INTLTOOL} ${INTLFLAGS} -q -u -c ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}',
		color='BLUE')

	Object.register('intltool_po', intltool_po)
	Object.register('intltool_in', intltool_in)
	Object.register('intltool', intltoolobj)

def detect(conf):

	conf.check_tool('checks')

	pocom = conf.find_program('msgfmt')
	#if not pocom:
	#	fatal('The program msgfmt (gettext) is mandatory!')
	conf.env['POCOM'] = pocom

	intltool = conf.find_program('intltool-merge')
	#if not intltool:
	#	fatal('The program intltool-merge (intltool, gettext-devel) is mandatory!')
	conf.env['INTLTOOL'] = intltool

	conf.define('LOCALEDIR', os.path.join(datadir, 'locale'))

	def getstr(varname):
		return getattr(Params.g_options, varname, '')

