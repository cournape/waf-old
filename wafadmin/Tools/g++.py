#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils,Action,Params,Configure

# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.cpp -o file.o' when called
	cpp_vardeps    = ['CXX', 'CXXFLAGS', 'CXXFLAGS_' + Params.g_options.debug_level, '_CPPDEFFLAGS', '_CXXINCFLAGS', 'CXX_ST']
	Action.GenAction('cpp', cpp_vardeps)

	# TODO: this is the same definitions as for gcc, should be separated to have independent setup
	# on windows libraries must be defined after the object files 
	link_vardeps   = ['LINK', 'LINK_ST', 'LINKFLAGS', 'LINKFLAGS_' + Params.g_options.debug_level, '_LIBDIRFLAGS', '_LIBFLAGS']
	action = Action.GenAction('link', link_vardeps)

# tool detection and initial setup 
# is called when a configure process is started, 
# the values are cached for further build processes
def detect(conf):

	cpp = conf.checkProgram('cpp')
	if not cpp:
		return 0;

	comp = conf.checkProgram('g++')
	if not comp:
		return 0;

	# g++ requires ar for static libs
	if not conf.checkTool('ar'):
		Utils.error('g++ needs ar - not found')
		return 0

	# preprocessor
	conf.env['CPP']             = cpp

	# c++ compiler
	conf.env['CXX']             = comp
	conf.env['_CPPDEFFLAGS']    = ''
	conf.env['_CXXINCFLAGS']    = ''
	conf.env['CXX_ST']          = '%s -c -o %s'
	conf.env['CPPPATH_ST']      = '-I%s' # template for adding include pathes

	# compiler debug levels
	conf.env['CXXFLAGS'] = []
	conf.env['CXXFLAGS_OPTIMIZED'] = ['-O2']
	conf.env['CXXFLAGS_RELEASE'] = ['-O2']
	conf.env['CXXFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	conf.env['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']
		
	# linker	
	conf.env['LINK']             = comp
	conf.env['LIB']              = []
	conf.env['LINK_ST']          = '%s -o %s'
	conf.env['LIB_ST']           = '-l%s'	# template for adding libs
	conf.env['LIBPATH_ST']       = '-L%s' # template for adding libpathes
	conf.env['STATICLIB_ST']     = '-l%s'
	conf.env['STATICLIBPATH_ST'] = '-L%s'
	conf.env['_LIBDIRFLAGS']     = ''
	conf.env['_LIBFLAGS']        = ''

	conf.env['SHLIB_MARKER']     = '-Wl,-Bdynamic'
	conf.env['STATICLIB_MARKER'] = '-Wl,-Bstatic'

	# linker debug levels
	conf.env['LINKFLAGS'] = []
	conf.env['LINKFLAGS_OPTIMIZED'] = ['-s']
	conf.env['LINKFLAGS_RELEASE'] = ['-s']
	conf.env['LINKFLAGS_DEBUG'] = ['-g']
	conf.env['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	if not conf.env['DESTDIR']: conf.env['DESTDIR']=''
	
	if sys.platform == "win32": 
		if not conf.env['PREFIX']: conf.env['PREFIX']='c:\\'

		# shared library 
		conf.env['shlib_CXXFLAGS']  = ['']
		conf.env['shlib_LINKFLAGS'] = ['-shared']
		conf.env['shlib_obj_ext']   = ['.o']
		conf.env['shlib_PREFIX']    = 'lib'
		conf.env['shlib_SUFFIX']    = '.dll'
		conf.env['shlib_IMPLIB_SUFFIX'] = ['.dll.a']
	
		# static library
		conf.env['staticlib_LINKFLAGS'] = ['']
		conf.env['staticlib_obj_ext'] = ['.o']
		conf.env['staticlib_PREFIX']= 'lib'
		conf.env['staticlib_SUFFIX']= '.a'

		# program 
		conf.env['program_obj_ext'] = ['.o']
		conf.env['program_SUFFIX']  = '.exe'

	else:
		if not conf.env['PREFIX']: conf.env['PREFIX'] = '/usr'

		# shared library 
		conf.env['shlib_CXXFLAGS']  = ['-fPIC', '-DPIC']
		conf.env['shlib_LINKFLAGS'] = ['-shared']
		conf.env['shlib_obj_ext']   = ['.os']
		conf.env['shlib_PREFIX']    = 'lib'
		conf.env['shlib_SUFFIX']    = '.so'
	
		# static lib
		conf.env['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		conf.env['staticlib_obj_ext'] = ['.o']
		conf.env['staticlib_PREFIX']= 'lib'
		conf.env['staticlib_SUFFIX']= '.a'

		# program 
		conf.env['program_obj_ext'] = ['.o']
		conf.env['program_SUFFIX']  = ''

	return 1

