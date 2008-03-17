#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import optparse
import Params, Configure

import ccroot

# tool detection and initial setup
# is called when a configure process is started,
# the values are cached for further build processes
def detect(conf):
	v = conf.env
	cxx = None
	if v['CXX']:
		cxx = v['CXX']
	elif 'CXX' in os.environ:
		cxx = os.environ['CXX']
	if not cxx: cxx = conf.find_program('g++', var='CXX')
	if not cxx: cxx = conf.find_program('c++', var='CXX')
	if not cxx: conf.fatal("g++ was not found")

	if not v['CPP']:
		cpp = conf.find_program('cpp', var='CPP')
		if not cpp: cpp = cxx
		v['CPP'] = cpp

	# load the cpp builders
	conf.check_tool('cpp')

	# g++ requires ar for static libs
	conf.check_tool('ar')
	if not v['AR']:
		conf.fatal('g++ needs ar - not found')

	v['CXX'] = cxx

	#v['CPPFLAGS']            = []
	#v['CXXDEFINES']          = [] # command-line defines

	v['_CXXINCFLAGS']        = []
	v['_CXXDEFFLAGS']        = []

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '-c -o '

	v['CPPPATH_ST']          = '-I%s' # template for adding include paths


	# linker
	v['LINK_CXX']            = v['LINK_CXX'] or v['CXX']
	#v['LIB']                 = []

	v['CPPLNK_TGT_F']        = '-o '
	v['CPPLNK_SRC_F']        = ''

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CXXDEFINES_ST']       = '-D%s'
	v['_LIBDIRFLAGS']        = ''
	v['_LIBFLAGS']           = ''

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	# linker debug levels
	#v['LINKFLAGS']           = v['LINKFLAGS'] or []
	v['LINKFLAGS_OPTIMIZED'] = ['-s']
	v['LINKFLAGS_RELEASE']   = ['-s']
	v['LINKFLAGS_DEBUG']     = ['-g']
	v['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	if sys.platform == "win32":
		# shared library
		v['shlib_CXXFLAGS']    = ['']
		v['shlib_LINKFLAGS']   = ['-shared']
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.a']

		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_SUFFIX']    = '.exe'

		# plugins, loadable modules.
		v['plugin_CXXFLAGS']     = v['shlib_CXXFLAGS']
		v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
		v['plugin_PREFIX']       = v['shlib_PREFIX']
		v['plugin_SUFFIX']       = v['shlib_SUFFIX']
	elif sys.platform == 'cygwin':
		# shared library
		v['shlib_CXXFLAGS']    = ['']
		v['shlib_LINKFLAGS']   = ['-shared']
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.a']

		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_SUFFIX']    = '.exe'
	elif sys.platform == 'darwin':
		v['SHLIB_MARKER']      = ' '
		v['STATICLIB_MARKER']  = ' '

		# shared library
		v['shlib_MARKER']      = ''
		v['shlib_CXXFLAGS']    = ['-fPIC']
		v['shlib_LINKFLAGS']   = ['-dynamiclib']
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.dylib'

		# static lib
		v['staticlib_MARKER']  = ''
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# bundles
		v['plugin_LINKFLAGS']    = ['-bundle', '-undefined dynamic_lookup']
		v['plugin_CXXFLAGS']     = ['-fPIC']
		v['plugin_PREFIX']       = ''
		v['plugin_SUFFIX']       = '.bundle'

		# program
		v['program_SUFFIX']    = ''

		v['SHLIB_MARKER']        = ''
		v['STATICLIB_MARKER']    = ''

	elif sys.platform == 'aix5':
		# shared library
		v['shlib_CXXFLAGS']    = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS']   = ['-shared','-Wl,-brtl,-bexpfull']
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.so'

		# plugins, loadable modules.
		v['plugin_CXXFLAGS']   = v['shlib_CXXFLAGS']
		v['plugin_LINKFLAGS']  = v['shlib_LINKFLAGS']
		v['plugin_PREFIX']     = v['shlib_PREFIX']
		v['plugin_SUFFIX']     = v['shlib_SUFFIX']

		# static lib
		#v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_LINKFLAGS'] = ['-Wl,-brtl']
		v['program_SUFFIX']    = ''

		v['SHLIB_MARKER']      = ''
	else:
		# shared library
		v['shlib_CXXFLAGS']    = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS']   = ['-shared']
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.so'

		# plugins, loadable modules.
		v['plugin_CXXFLAGS']     = v['shlib_CXXFLAGS']
		v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
		v['plugin_PREFIX']       = v['shlib_PREFIX']
		v['plugin_SUFFIX']       = v['shlib_SUFFIX']

		# static lib
		#v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_SUFFIX']    = ''

	conf.check_tool('checks')

	conf.check_features(kind='cpp')

	# compiler debug levels
	if conf.check_flags('-Wall'):
		v['CXXFLAGS'] = ['-Wall']
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
