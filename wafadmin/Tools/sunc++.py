#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, optparse
import Utils, Action, Params, Configure
import ccroot


def find_cxx(conf):
	v = conf.env
	cc = None
	if v['CXX']: cc = v['CXX']
	elif 'CXX' in os.environ: cc = os.environ['CXX']
	#if not cc: cc = conf.find_program('g++', var='CXX')
	if not cc: cc = conf.find_program('c++', var='CXX')
	if not cc: conf.fatal('sunc++ was not found')
	v['CXX']  = cc

def find_cpp(conf):
	v = conf.env
	cpp = None
	if v['CPP']: cpp = v['CPP']
	elif 'CPP' in os.environ: cpp = os.environ['CPP']
	if not cpp: cpp = conf.find_program('cpp', var='CPP')
	if not cpp: cpp = v['CXX']
	v['CPP'] = cpp

def find_ar(conf):
	v = conf.env
	conf.check_tool('ar')
	if not v['AR']: conf.fatal('sunc++ requires ar - not found')

def common_flags(conf):
	v = conf.env

	# CPPFLAGS CXXDEFINES _CXXINCFLAGS _CXXDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '-c -o '
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CXX']: v['LINK_CXX'] = v['CXX']
	v['CXXLNK_SRC_F']        = ''
	v['CXXLNK_TGT_F']        = '-o '

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CXXDEFINES_ST']       = '-D%s'

	v['SHLIB_MARKER']        = '-Bdynamic'
	v['STATICLIB_MARKER']    = '-Bstatic'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CXXFLAGS']      = ['-Kpic', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-G']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['staticlib_LINKFLAGS'] = ['-Bstatic']
	v['staticlib_PATTERN']   = 'lib%s.a'

def modifier_debug(conf):
	v = conf.env
	v['CXXFLAGS'] = ['']
	if conf.check_flags('-O2'):
		v['CXXFLAGS_OPTIMIZED'] = ['-O2']
		v['CXXFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CXXFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CXXFLAGS', v['CXXFLAGS_'+debug_level])

def detect(conf):

	find_cxx(conf)
	find_cpp(conf)
	find_ar(conf)

	conf.check_tool('cxx')

	common_flags(conf)

	conf.check_tool('checks')
	conf.check_features(kind='cpp')

	modifier_debug(conf)

	conf.add_os_flags('CXXFLAGS')
	conf.add_os_flags('CPPFLAGS')
	conf.add_os_flags('LINKFLAGS')

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = ccroot.DEBUG_LEVELS.RELEASE,
		help = "Specify the debug level, does nothing if CFLAGS is set in the environment. [Allowed Values: '%s']" % "', '".join(ccroot.DEBUG_LEVELS.ALL),
		choices = ccroot.DEBUG_LEVELS.ALL,
		dest = 'debug_level')

	except optparse.OptionConflictError:
		# the suncc tool might have added that option already
		pass

