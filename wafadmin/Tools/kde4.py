#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, re, Object, Action, Utils, Common

class langobj(Object.genobj):
	def __init__(self, appname='set_your_app_name'):
		Object.genobj.__init__(self, 'other')
		self.langs = '' # for example "foo/fr foo/br"
		self.chmod = 0644
		self.inst_var = 'KDE4_LOCALE_INSTALL_DIR'
		self.appname = appname

	def apply(self):
		for lang in self.to_list(self.langs):
			node = self.path.find_source_lst(Utils.split_path(lang+'.po'))
			task = self.create_task('msgfmt', self.env)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.mo'))

	def install(self):
		for lang in self.to_list(self.langs):
			langname = lang.split('/')
			langname = langname[-1]
			inst_dir = langname+os.sep+'LC_MESSAGES'
			Common.install_as(self.inst_var, inst_dir+'/semantik.mo', lang+'.mo', chmod=self.chmod)

def detect(conf):
	kdeconfig = conf.find_program('kde4-config')
	if not kdeconfig:
		conf.fatal('we need kde4-config')
	prefix = os.popen('%s --prefix' % kdeconfig).read().strip()
	file = '%s/share/apps/cmake/modules/KDELibsDependencies.cmake' % prefix
	try: os.stat(file)
	except OSError: conf.fatal('could not open %s' % file)

	try:
		f = open(file, 'r')
		txt = f.read()
		f.close()
	except (OSError, IOError):
		conf.fatal('could not read %s' % file)

	txt = txt.replace('\\\n', '\n')
	fu = re.compile('#(.*)\n')
	txt = fu.sub('', txt)

	setregexp = re.compile('([sS][eE][tT]\s*\()\s*([^\s]+)\s+\"([^"]+)\"\)')
	found = setregexp.findall(txt)

	for (_, key, val) in found:
		#print key, val
		conf.env[key] = val

	# well well, i could just write an interpreter for cmake files
	conf.env['LIB_KDECORE']='kdecore'
	conf.env['LIB_KDEUI']  ='kdeui'
	conf.env['LIB_KIO']    ='kio'
	conf.env['LIB_KHTML']  ='khtml'
	conf.env['LIB_KPARTS'] ='kparts'

	conf.env['LIBPATH_KDECORE'] = conf.env['KDE4_LIB_INSTALL_DIR']
	conf.env['CPPPATH_KDECORE'] = conf.env['KDE4_INCLUDE_INSTALL_DIR']
	conf.env.append_value('CPPPATH_KDECORE', conf.env['KDE4_INCLUDE_INSTALL_DIR']+"/KDE")

	conf.env['MSGFMT'] = conf.find_program('msgfmt')

Object.register('msgfmt', langobj)
Action.simple_action('msgfmt', '${MSGFMT} ${SRC} -o ${TGT}', color='BLUE', prio=10)

