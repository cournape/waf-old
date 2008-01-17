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

			self.env['INTLCACHE'] = os.path.join(self.path.bldpath(self.env), self.podir, self.intlcache)
			self.env['INTLPODIR'] = podirnode.srcpath(self.env)
			self.env['INTLFLAGS'] = self.flags

			task = self.create_task('intltool', self.env)
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
		linguas = self.path.find_source ('LINGUAS')
		if linguas:
			# scan LINGUAS file for locales to process
			f = open (linguas.abspath())
			re_linguas = re.compile('[-a-zA-Z_@.]+')
			for line in f.readlines():
				# Make sure that we only process lines which contain locales
				if re_linguas.match(line):
					node = self.path.find_source(re_linguas.match(line).group() + '.po')
					task = self.create_task('po', self.env)
					task.set_inputs(node)
					task.set_outputs(node.change_ext('.mo'))
		else:
			Params.pprint('RED', "Error no LINGUAS file found in po directory")

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
		# after our targets are created, process the .c files, etc
		cc.ccobj.apply_core(self)

def setup(bld):
	Action.simple_action('po', '${POCOM} -o ${TGT} ${SRC}', color='BLUE', prio=10)
	Action.simple_action('intltool',
		'${INTLTOOL} ${INTLFLAGS} -q -u -c ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}',
		color='BLUE', prio=200)

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

	def getstr(varname):
		return getattr(Params.g_options, varname, '')

	prefix  = conf.env['PREFIX']
	datadir = getstr('datadir')
	if not datadir: datadir = os.path.join(prefix,'share')

	conf.define('LOCALEDIR', os.path.join(datadir, 'locale'))
	conf.define('DATADIR', datadir)

	#Define to 1 if you have the <locale.h> header file.
	conf.check_header('locale.h', 'HAVE_LOCALE_H')

def set_options(opt):
	try:
		# we do not know yet
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except:
		pass

	for i in "datadir".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

