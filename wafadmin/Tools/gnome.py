#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, re
import Object, Action, Params, Common, Scan
from Params import fatal, error, trace

n1_regexp = re.compile('<refentrytitle>(.*)</refentrytitle>', re.M)
n2_regexp = re.compile('<manvolnum>(.*)</manvolnum>', re.M)

class sgml_man_scanner(Scan.scanner):
	def __init__(self):
		Scan.scanner.__init__(self)
	def scan(self, node, env):
		if node in node.m_parent.m_files: variant = 0
		else: variant = task.m_env.variant()

		fi = open(node.abspath(env), 'r')
		content = fi.read()
		fi.close()

		names = n1_regexp.findall(content)
		nums = n2_regexp.findall(content)

		name = names[0]
		num  = nums[0]

		doc_name = name+'.'+num

		#print "@@@@@@@@@@@@@@@@@@@@@@@@@@ ", doc_name
		return ([], [doc_name])

sgml_scanner = sgml_man_scanner()

# intltool
class gnome_intltool(Object.genobj):
	def __init__(self):
		Object.genobj.__init__(self, 'other')
		self.sources = ''
		self.destvar = ''
		self.subdir  = ''
		self.m_tasks   = []

	def apply(self):
		tree = Params.g_build
		current = tree.m_curdirnode
		for i in self.sources.split():
			node = self.m_current_path.find_node(i.split(os.sep))

			podirnode = self.m_current_path.find_node(self.podir.split(os.sep) )

			self.env['INTLCACHE'] = Params.g_build.m_curdirnode.bldpath(self.env) + os.sep + ".intlcache"
			self.env['INTLPODIR'] = podirnode.bldpath(self.env)

			task = self.create_task('intltool', self.env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext(''))
			self.m_tasks.append(task)

	def install(self):	
		current = Params.g_build.m_curdirnode
		for task in self.m_tasks:
			out = task.m_outputs[0]
			Common.install_files(self.destvar, self.subdir, out.abspath(self.env), self.env)

# sgml2man
class gnome_sgml2man(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other')
		self.m_tasks=[]
		self.m_appname = appname
	def apply(self):
		tree = Params.g_build
		for node in self.m_current_path.m_files:
			try:
				base, ext = os.path.splitext(node.m_name)
				if ext != '.sgml': continue

				if tree.needs_rescan(node, self.env):
					sgml_scanner.do_scan(node, self.env, hashparams={})

				if node in node.m_parent.m_files: variant = 0
				else: variant = env.variant()

				try: tmp_lst = tree.m_raw_deps[variant][node]
				except: tmp_lst = []
				name = tmp_lst[0]

				task = self.create_task('sgml2man', self.env, 2)
				task.set_inputs(node)
				task.set_outputs(self.file_in(name))
				self.m_tasks.append(task)
			except:
				raise
				pass

	def install(self):	
		current = Params.g_build.m_curdirnode

		for task in self.m_tasks:
			out = task.m_outputs[0]
			# get the number 1..9
			name = out.m_name
			ext = name[len(name)-1]
			# and install the file
			Common.install_files('DATADIR', 'man/man%s/' % ext, out.abspath(self.env), self.env)

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
	Action.simple_action('sgml2man', '${SGML2MAN} -o ${TGT[0].bld_dir(env)} ${SRC}', color='BLUE')
	Action.simple_action( \
		'intltool', \
		'${INTLTOOL} -s -u -c ${INTLCACHE} ${INTLPODIR} ${SRC} ${TGT}', \
		color='BLUE')

	Object.register('gnome_translations', gnome_translations)
	Object.register('gnome_sgml2man', gnome_sgml2man)
	Object.register('gnome_intltool', gnome_intltool)

def detect(conf):

	pocom = conf.checkProgram('msgfmt')
	if not pocom:
		fatal('The program msgfmt (gettext) is mandatory!')
	conf.env['POCOM'] = pocom

	sgml2man = conf.checkProgram('docbook2man')
	if not sgml2man:
		fatal('The program docbook2man is mandatory!')
	conf.env['SGML2MAN'] = sgml2man

	intltool = conf.checkProgram('intltool-merge')
	if not intltool:
		fatal('The program intltool-merge (intltool, gettext-devel) is mandatory!')
	conf.env['INTLTOOL'] = intltool

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

