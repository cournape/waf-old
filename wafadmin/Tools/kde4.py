#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, re, Object, Action, Utils, Common

class langobj(Object.genobj):
	s_default_ext = ['.java']
	def __init__(self):
		Object.genobj.__init__(self, 'other')
		self.langs = ''
		self.chmod = 0644
		self.inst_dir = 'semantik'
		self.inst_var = 'KDE4_LOCALE_INSTALL_DIR'

	def apply(self):
		for filename in self.to_list(self.langs):
			node = self.path.find_source_lst(Utils.split_path(filename+'.po'))
			task = self.create_task('msgfmt', self.env, 10)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.gmo'))

	def install(self):
		for i in self.m_tasks:
			# only one output file for each task but well
			lst=[a.relpath_gen(self.path) for a in i.m_outputs]
			Common.install_files(self.inst_var, self.inst_dir, lst, chmod=self.chmod)

def detect(conf):
	kdeconfig = conf.find_program('kde4-config')
	if not kdeconfig:
		conf.fatal('we need kde4-config')
	prefix = os.popen('%s --prefix' % kdeconfig).read().strip()
	file = '%s/lib/kde4/cmake/KDE4Config.cmake' % prefix
	try: os.stat(file)
	except: conf.fatal('could not open %s' % file)

	try:
		f = open(file, 'r')
		txt = f.read()
		f.close()
	except:
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

def setup(env):
	Object.register('msgfmt', langobj)
	Action.simple_action('msgfmt', '${MSGFMT} ${SRC} -o ${TGT}', color='BLUE')

