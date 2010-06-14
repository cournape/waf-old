#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)

import os
from waflib import Utils
from waflib.Tools import ccroot, ar
from waflib.Configure import conf

@conf
def find_scc(conf):
	v = conf.env
	cc = None
	if v['CC']: cc = v['CC']
	elif 'CC' in conf.environ: cc = conf.environ['CC']
	#if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc: conf.fatal('suncc was not found')

	try:
		if not Utils.cmd_output('%s -flags' % cc):
			conf.fatal('suncc %r was not found' % cc)
	except ValueError:
		conf.fatal('suncc -flags could not be executed')

	v['CC']  = cc
	v['CC_NAME'] = 'sun'

@conf
def scc_common_flags(conf):
	v = conf.env

	# CPPFLAGS CCDEFINES _CCINCFLAGS _CCDEFFLAGS

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = ['-c', '-o', '']

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = ['-o', ''] # solaris hack, separate the -o from the target

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CCDEFINES_ST']        = '-D%s'

	v['SONAME_ST']           = '-Wl,-h -Wl,%s'
	v['SHLIB_MARKER']        = '-Bdynamic'
	v['STATICLIB_MARKER']    = '-Bstatic'

	# program
	v['cprogram_PATTERN']     = '%s'

	# shared library
	v['shlib_CCFLAGS']       = ['-Kpic', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-G']
	v['cshlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['stlib_LINKFLAGS'] = ['-Bstatic']
	v['cstlib_PATTERN']   = 'lib%s.a'

detect = '''
find_scc
find_ar
scc_common_flags
cc_load_tools
cc_add_flags
link_add_flags
'''

