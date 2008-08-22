#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, optparse
import Utils, Options, Configure
import ccroot, ar
from Configure import conftest

@conftest
def find_scc(conf):
	v = conf.env
	cc = None
	if v['CC']: cc = v['CC']
	elif 'CC' in os.environ: cc = os.environ['CC']
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

@conftest
def scc_common_flags(conf):
	v = conf.env

	# CPPFLAGS CCDEFINES _CCINCFLAGS _CCDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = '-c -o '
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = '-o '

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CCDEFINES_ST']        = '-D%s'


	v['SHLIB_MARKER']        = '-Bdynamic'
	v['STATICLIB_MARKER']    = '-Bstatic'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CCFLAGS']       = ['-Kpic', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-G']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['staticlib_LINKFLAGS'] = ['-Bstatic']
	v['staticlib_PATTERN']   = 'lib%s.a'

@conftest
def scc_modifier_debug(conf):
	v = conf.env

	# compiler debug levels
	v['CCFLAGS'] = ['-O']
	if conf.check_flags('-O2'):
		v['CCFLAGS_OPTIMIZED'] = ['-O2']
		v['CCFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CCFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CCFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	# see the option below
	try:
		debug_level = Options.options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CCFLAGS', v['CCFLAGS_'+debug_level])

detect = '''
find_scc
find_cpp
find_ar
scc_common_flags
cc_load_tools
cc_check_features
gcc_modifier_debug
cc_add_flags
'''

