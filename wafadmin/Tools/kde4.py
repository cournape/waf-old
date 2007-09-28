#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys, re

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

	conf.env['LIBPATH_KDECORE'] = conf.env['KDE4_LIB_INSTALL_DIR']
	conf.env['CPPPATH_KDECORE'] = conf.env['KDE4_INCLUDE_INSTALL_DIR']


