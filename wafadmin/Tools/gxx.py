#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)
# Yinon Ehrlich, 2009

import os, optparse, sys, re
import Configure, Options, Utils
import ccroot, ar
from Configure import conftest

@conftest
def find_gxx(conf):
	v = conf.env
	cxx = None
	if v['CXX']: cxx = v['CXX']
	elif 'CXX' in conf.environ: cxx = conf.environ['CXX']
	if not cxx: cxx = conf.find_program('g++', var='CXX')
	if not cxx: cxx = conf.find_program('c++', var='CXX')
	if not cxx: conf.fatal('g++ was not found')
	cxx = conf.cmd_to_list(cxx)

	ccroot.get_cc_version(conf, cxx, gcc=True)
	v['CXX_NAME'] = 'gcc'
	v['CXX'] = cxx

@conftest
def gxx_common_flags(conf):
	v = conf.env

	# CPPFLAGS CXXDEFINES _CXXINCFLAGS _CXXDEFFLAGS

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = ['-c', '-o', ''] # shell hack for -MD
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CXX']: v['LINK_CXX'] = v['CXX']
	v['CXXLNK_SRC_F']        = ''
	v['CXXLNK_TGT_F']        = ['-o', ''] # shell hack for -MD

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['RPATH_ST']            = '-Wl,-rpath,%s'
	v['CXXDEFINES_ST']       = '-D%s'

	v['SONAME_ST']           = '-Wl,-h,%s'
	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'
	v['FULLSTATIC_MARKER']   = '-static'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CXXFLAGS']      = ['-fPIC', '-DPIC']
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
def gxx_modifier_win32(conf):
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = '%s.dll'
	v['staticlib_PATTERN']   = '%s.lib'
	v['shlib_CXXFLAGS']      = []

	v['staticlib_LINKFLAGS'] = []

@conftest
def gxx_modifier_cygwin(conf):
	return gxx_modifier_win32(conf)

@conftest
def gxx_modifier_darwin(conf):
	v = conf.env
	v['shlib_CXXFLAGS']      = ['-fPIC', '-compatibility_version', '1', '-current_version', '1']
	v['shlib_LINKFLAGS']     = ['-dynamiclib']
	v['shlib_PATTERN']       = 'lib%s.dylib'

	v['staticlib_LINKFLAGS'] = []

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

@conftest
def gxx_modifier_aix5(conf):
	v = conf.env
	v['program_LINKFLAGS']   = ['-Wl,-brtl']

	v['shlib_LINKFLAGS']     = ['-shared', '-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

def detect(conf):
		conf.find_gxx()
		conf.find_cpp()
		conf.find_ar()
		conf.gxx_common_flags()

		# * set configurations specific for a platform.
		# * By default sys.plaform will be used as the target platform.
		#	but you may write conf.env['TARGET_PLATFORM'] = 'my_platform' to allow
		#	cross compilaion..
		target_platform = conf.env['TARGET_PLATFORM'] or sys.platform

		gxx_modifier_func = globals().get('gxx_modifier_'+target_platform)
		if gxx_modifier_func:
				gxx_modifier_func(conf)

		conf.cxx_load_tools()
		conf.cxx_add_flags()
