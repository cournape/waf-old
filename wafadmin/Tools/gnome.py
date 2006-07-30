#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os
import Object, Action, Params, Common
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
			Common.install_as('GNOMELOCALEDIR', destfile, orig, self.env)

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

	# addefine also sets the variable to the env
	conf.addDefine('GNOMELOCALEDIR', os.path.join(datadir, 'locale'))
	conf.addDefine('DATADIR', datadir)
	conf.addDefine('LIBDIR', libdir)

	# TODO: maybe the following checks should be in a more generic module.

	#always defined to indicate that i18n is enabled */
	conf.addDefine('ENABLE_NLS', '1')

	# TODO
	#Define to 1 if you have the `bind_textdomain_codeset' function.
	conf.addDefine('HAVE_BIND_TEXTDOMAIN_CODESET', '1')

	# TODO
	#Define to 1 if you have the `dcgettext' function.
	conf.addDefine('HAVE_DCGETTEXT', '1')

	#Define to 1 if you have the <dlfcn.h> header file.
	conf.checkHeader('dlfcn.h', 'HAVE_DLFCN_H')
 
	# TODO
	#Define if the GNU gettext() function is already present or preinstalled.
	conf.addDefine('HAVE_GETTEXT', '1')
 
	#Define to 1 if you have the <inttypes.h> header file.
	conf.checkHeader('inttypes.h', 'HAVE_INTTYPES_H')
 
	# TODO FIXME
	#Define if your <locale.h> file defines LC_MESSAGES.
	#conf.addDefine('HAVE_LC_MESSAGES', '1')
 
	#Define to 1 if you have the <locale.h> header file.
	conf.checkHeader('locale.h', 'HAVE_LOCALE_H')

	#Define to 1 if you have the <memory.h> header file.
	conf.checkHeader('memory.h', 'HAVE_MEMORY_H')

	#Define to 1 if you have the <stdint.h> header file.
	conf.checkHeader('stdint.h', 'HAVE_STDINT_H')

	#Define to 1 if you have the <stdlib.h> header file.
	conf.checkHeader('stdlib.h', 'HAVE_STDLIB_H')
 
	#Define to 1 if you have the <strings.h> header file.
	conf.checkHeader('strings.h', 'HAVE_STRINGS_H')
 
	#Define to 1 if you have the <string.h> header file.
	conf.checkHeader('string.h', 'HAVE_STRING_H')
 
        #Define to 1 if you have the <sys/stat.h> header file.
	conf.checkHeader('sys/stat.h', 'HAVE_SYS_STAT_H')
 
	#Define to 1 if you have the <sys/types.h> header file.
	conf.checkHeader('sys/types.h', 'HAVE_SYS_TYPES_H')
 
	#Define to 1 if you have the <unistd.h> header file.
	conf.checkHeader('unistd.h', 'HAVE_UNISTD_H')

	return 1

def set_options(opt):
	try:
		# we do not know yet
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except:
		pass

	for i in "execprefix datadir libdir".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

