#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)
# Ralf Habacker, 2006 (rh)
# Yinon Ehrlich, 2009

import os, sys
import Configure, Options, Utils, TaskGen
import ccroot, ar
from Configure import conftest

@conftest
def find_gcc(conf):
	v = conf.env
	cc = None
	if v['CC']:
		cc = v['CC']
	elif 'CC' in conf.environ:
		cc = conf.environ['CC']
	if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc: conf.fatal('gcc was not found')
	cc = conf.cmd_to_list(cc)

	ccroot.get_cc_version(conf, cc, gcc=True)
	v['CC_NAME'] = 'gcc'
	v['CC'] = cc

@conftest
def gcc_common_flags(conf):
	v = conf.env

	# CPPFLAGS CCDEFINES _CCINCFLAGS _CCDEFFLAGS

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = ['-c', '-o', ''] # shell hack for -MD
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = ['-o', ''] # shell hack for -MD

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['RPATH_ST']            = '-Wl,-rpath,%s'
	v['CCDEFINES_ST']        = '-D%s'

	v['SONAME_ST']           = '-Wl,-h,%s'
	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'
	v['FULLSTATIC_MARKER']   = '-static'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CCFLAGS']       = ['-fPIC', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-shared']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
	v['staticlib_PATTERN']   = 'lib%s.a'

	# osx stuff
	v['LINKFLAGS_MACBUNDLE'] = ['-bundle', '-undefined', 'dynamic_lookup']
	v['CCFLAGS_MACBUNDLE']   = ['-fPIC']
	v['macbundle_PATTERN']   = '%s.bundle'

@conftest
def gcc_modifier_win32(conf):
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = '%s.dll'
	v['staticlib_PATTERN']   = '%s.lib'
	v['shlib_CCFLAGS']       = []

	v['staticlib_LINKFLAGS'] = []

@conftest
def gcc_modifier_cygwin(conf):
	return conf.gcc_modifier_win32()

@conftest
def gcc_modifier_darwin(conf):
	v = conf.env
	v['shlib_CCFLAGS']       = ['-fPIC', '-compatibility_version', '1', '-current_version', '1']
	v['shlib_LINKFLAGS']     = ['-dynamiclib']
	v['shlib_PATTERN']       = 'lib%s.dylib'

	v['staticlib_LINKFLAGS'] = []

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

@conftest
def gcc_modifier_aix5(conf):
	v = conf.env
	v['program_LINKFLAGS']   = ['-Wl,-brtl']

	v['shlib_LINKFLAGS']     = ['-shared','-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

def detect(conf):
		conf.find_gcc()
		conf.find_cpp()
		conf.find_ar()
		conf.gcc_common_flags()

		# * set configurations specific for a platform.
		# * By default sys.plaform will be used as the target platform.
		#	but you may write conf.env['TARGET_PLATFORM'] = 'my_platform' to allow
		#	cross compilaion..
		target_platform = conf.env['TARGET_PLATFORM'] or sys.platform

		gcc_modifier_func = globals().get('gcc_modifier_'+target_platform)
		if gcc_modifier_func:
				gcc_modifier_func(conf)

		conf.cc_load_tools()
		conf.cc_add_flags()
