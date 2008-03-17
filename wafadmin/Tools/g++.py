#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import optparse
import Params, Configure

import ccroot

def find_cxx(conf):
	v = conf.env
	cc = None
	if v['CXX']: cc = v['CXX']
	elif 'CXX' in os.environ: cc = os.environ['CXX']
	if not cc: cc = conf.find_program('g++', var='CXX')
	if not cc: cc = conf.find_program('c++', var='CXX')
	if not cc: conf.fatal('g++ was not found')
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
	env = conf.env
	conf.check_tool('ar')
	if not env['AR']: conf.fatal('g++ requires ar - not found')

def common_flags(conf):
	v = conf.env

	# CPPFLAGS CXXDEFINES _CXXINCFLAGS _CXXDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CXX_SRC_F']             = ''
	v['CXX_TGT_F']             = '-c -o '
	v['CPPPATH_ST']           = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CXX']: v['LINK_CXX'] = v['CXX']
	v['CXXLNK_SRC_F']          = ''
	v['CXXLNK_TGT_F']          = '-o '

	v['LIB_ST']               = '-l%s' # template for adding libs
	v['LIBPATH_ST']           = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']         = '-l%s'
	v['STATICLIBPATH_ST']     = '-L%s'
	v['CXXDEFINES_ST']         = '-D%s'

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CXXFLAGS']       = ['-fPIC', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-shared']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
	v['staticlib_PATTERN']   = 'lib%s.a'

def modifier_win32(conf):
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_IMPLIB_SUFFIX'] = ['.dll.a'] # FIXME what the fuck is IMPLIB?
	v['shlib_CXXFLAGS']       = ['']

	v['staticlib_LINKFLAGS'] = ['']

def modifier_cygwin(conf):
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CXXFLAGS']       = ['']
	v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']

	v['staticlib_LINKFLAGS'] = ['']

def modifier_darwin(conf):
	v = conf.env
	v['shlib_CXXFLAGS']       = ['-fPIC']
	v['shlib_LINKFLAGS']     = ['-dynamiclib']
	v['shlib_PATTERN']       = 'lib%s.dylib'

	v['staticlib_LINKFLAGS'] = ['']

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

def modifier_aix5(conf):
	v = conf.env
	v['program_LINKFLAGS']   = ['-Wl,-brtl']

	v['shlib_LINKFLAGS']     = ['-shared','-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

def modifier_plugin(conf):
	v = conf.env
	# TODO this will disappear somehow
	# plugins. We handle them exactly as shlibs
	# everywhere except on osx, where we do bundles
	if sys.platform == 'darwin':
		v['plugin_LINKFLAGS']    = ['-bundle', '-undefined dynamic_lookup']
		v['plugin_CXXFLAGS']      = ['-fPIC']
		v['plugin_PATTERN']      = '%s.bundle'
	else:
		v['plugin_CXXFLAGS']      = v['shlib_CXXFLAGS']
		v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
		v['plugin_PATTERN']      = v['shlib_PATTERN']

def modifier_debug(conf):
	v = conf.env
	# compiler debug levels
	if conf.check_flags('-O2'):
		v['CXXFLAGS_OPTIMIZED'] = ['-O2']
		v['CXXFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CXXFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']
	if conf.check_flags('-Wall'):
		for x in 'OPTIMIZED RELEASE DEBUG ULTRADEBUG'.split(): v.append_unique('CXXFLAGS_'+x, '-Wall')
	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CXXFLAGS', v['CXXFLAGS_'+debug_level])

def detect(conf):

	find_cxx(conf)
	find_cpp(conf)
	find_ar(conf)

	conf.check_tool('cpp')

	common_flags(conf)
	if sys.platform == 'win32': modifier_win32(conf)
	elif sys.platform == 'cygwin': modifier_cygwin(conf)
	elif sys.platform == 'darwin': modifier_darwin(conf)
	elif sys.platform == 'aix5': modifier_aix5(conf)
	modifier_plugin(conf)

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
		help = "Specify the debug level, does nothing if CXXFLAGS is set in the environment. [Allowed Values: '%s']" % "', '".join(ccroot.DEBUG_LEVELS.ALL),
		choices = ccroot.DEBUG_LEVELS.ALL,
		dest = 'debug_level')
	except optparse.OptionConflictError:
		# the gcc tool might have added that option already
		pass
