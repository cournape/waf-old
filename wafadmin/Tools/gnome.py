#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os
import Object, Action
from Params import fatal, error

# translations
class gnome_translations(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other')
		self.m_tasks=[]
		self.m_appname = appname
	def apply(self):
		for file in self.m_current_path.m_files:
			try:
				base, ext = os.path.splitext(file.m_name)
				if ext != '.po': continue

				task = self.create_task('po', self.env, 2)
				task.set_inputs(file)
				task.set_outputs(file.change_ext('.gmo'))
				self.m_tasks.append(task)
			except: pass
	def install(self):
		destfilename = self.m_appname+'.mo'

		current = Params.g_build.m_curdirnode
		for file in self.m_current_path.m_files:
			lang, ext = os.path.splitext(file.m_name)
			if ext != '.po': continue

			node = self.m_current_path.find_node( (lang+'.gmo').split('/') )
			orig = node.relpath_gen(current)

			destfile = os.sep.join([lang, 'LC_MESSAGES', destfilename])
			Common.install_as('GNOME_LOCALE', destfile, orig, self.env)


def setup(env):
	Action.simple_action('po', '${POCOM} -o ${TGT} ${SRC}', color='BLUE')
	Object.register('gnome_translations', gnome_translations)

def detect(conf):

	pocom = conf.checkProgram('msgfmt')
	if not pocom:
		fatal('The program msgfmt (gettext) is mandatory !')
	conf.env['POCOM'] = pocom

	def getstr(varname):
		#if env.has_key('ARGS'): return env['ARGS'].get(varname, '')
		v=''
		try: v = getattr(Params.g_options, varname)
		except: return ''
		return v

	prefix  = conf.env['PREFIX']
	datadir = getstr('datadir')
	libdir  = getstr('libdir')
	if not datadir: datadir = os.path.join(prefix,'share')
	if not libdir:  libdir  = os.path.join(prefix,'lib')

	conf.env['DATADIR'] = datadir
	conf.env['LIBDIR']  = libdir
	conf.env['GNOMELOCALEDIR'] = os.path.join(datadir, 'locale')

	return 1

def set_options(opt):
	try:
		# we do not know yet
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except:
		pass

	for i in "execprefix datadir libdir".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

