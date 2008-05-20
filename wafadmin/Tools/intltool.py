#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"intltool support"

import os, re
import TaskGen, Action, Params, Common, Scan, Utils, Runner
import cc
from Params import fatal, error

# intltool
class intltool_in_taskgen(TaskGen.task_gen):
	def __init__(self, *k):
		TaskGen.task_gen.__init__(self, *k)
		self.source  = ''
		self.inst_var = ''
		self.inst_dir = ''
		self.flags   = ''
		self.podir   = 'po'
		self.intlcache = '.intlcache'
		self.m_tasks = []

	def apply(self):
		self.env = self.env.copy()
		tree = Params.g_build
		current = tree.m_curdirnode
		for i in self.to_list(self.source):
			node = self.path.find_resource(i)

			podirnode = self.path.find_dir(self.podir)

			self.env['INTLCACHE'] = os.path.join(self.path.bldpath(self.env), self.podir, self.intlcache)
			self.env['INTLPODIR'] = podirnode.srcpath(self.env)
			self.env['INTLFLAGS'] = self.flags

			task = self.create_task('intltool', self.env)
			task.set_inputs(node)
			task.set_outputs(node.change_ext(''))

			task.install = {'var': self.inst_var, 'dir': self.inst_dir, 'chmod': 0644}

class intltool_po_taskgen(TaskGen.task_gen):
	def __init__(self, *k, **kw):
		TaskGen.task_gen.__init__(self, *k)
		self.chmod = 0644
		self.inst_var_default = 'LOCALEDIR'
		self.appname = kw.get('appname', 'set_your_app_name')
		self.m_tasks=[]

	def apply(self):
		def install_translation(task):
			out = task.m_outputs[0]
			filename = out.m_name
			(langname, ext) = os.path.splitext(filename)
			inst_file = langname + os.sep + 'LC_MESSAGES' + os.sep + self.appname + '.mo'
			Common.install_as(self.inst_var, inst_file, out.abspath(self.env), chmod=self.chmod)

		linguas = self.path.find_resource('LINGUAS')
		if linguas:
			# scan LINGUAS file for locales to process
			f = open(linguas.abspath())
			re_linguas = re.compile('[-a-zA-Z_@.]+')
			for line in f.readlines():
				# Make sure that we only process lines which contain locales
				if re_linguas.match(line):
					node = self.path.find_resource(re_linguas.match(line).group() + '.po')
					task = self.create_task('po', self.env)
					task.set_inputs(node)
					task.set_outputs(node.change_ext('.mo'))
					if Params.g_install: task.install = install_translation
		else:
			Params.pprint('RED', "Error no LINGUAS file found in po directory")

Action.simple_action('po', '${POCOM} -o ${TGT} ${SRC}', color='BLUE', prio=10)
Action.simple_action('intltool',
	'${INTLTOOL} ${INTLFLAGS} -q -u -c ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}',
	color='BLUE', prio=200)

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
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except Exception:
		pass

	for i in "datadir".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

