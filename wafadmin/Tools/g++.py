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

	deb = Params.g_options.debug_level

	cpp_str = '${CXX} ${CXXFLAGS} ${CXXFLAGS%s} ${CPPFLAGS} ${_CXXINCFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}' % deb
	Action.simple_action('cpp', cpp_str)

	# on windows libraries must be defined after the object files 
	link_str = '${LINK} ${CPPLNK_SRC_F}${SRC} ${CPPLNK_TGT_F}${TGT} ${LINKFLAGS} ${LINKFLAGS_%s} ${_LIBDIRFLAGS} ${_LIBFLAGS}' % deb
	Action.simple_action('cpp_link', link_str)

	if not sys.platform == "win32":
		Params.g_colors['cpp']='\033[92m'
		Params.g_colors['cpp_link']='\033[93m'
		Params.g_colors['cpp_link_static']='\033[93m'
		Params.g_colors['fakelibtool']='\033[94m'

# tool detection and initial setup 
# is called when a configure process is started, 
# the values are cached for further build processes
def detect(conf):

	cpp = conf.checkProgram('cpp', var='CPP')
	if not cpp:
		return 0;

	comp = conf.checkProgram('g++', var='CXX')
	if not comp:
		return 0;

	# load the cpp builders
	conf.checkTool('cpp')

	# g++ requires ar for static libs
	if not conf.checkTool('ar'):
		Utils.error('g++ needs ar - not found')
		return 0

	v = conf.env

	# preprocessor
	v['CPP']                 = cpp

	# c++ compiler
	v['CXX']                 = comp
	v['CPPFLAGS']            = []
	v['_CXXINCFLAGS']        = ''

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '-c -o '

	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# compiler debug levels
	v['CXXFLAGS']            = []
	v['CXXFLAGS_OPTIMIZED']  = ['-O2']
	v['CXXFLAGS_RELEASE']    = ['-O2']
	v['CXXFLAGS_DEBUG']      = ['-g', '-DDEBUG']
	v['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	# linker	
	v['LINK']                = comp
	v['LIB']                 = []

	v['CPPLNK_TGT_F']        = '-o '
	v['CPPLNK_SRC_F']        = ''


	v['LIB_ST']              = '-l%s'	# template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpathes
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['_LIBDIRFLAGS']        = ''
	v['_LIBFLAGS']           = ''

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	# linker debug levels
	v['LINKFLAGS']           = []
	v['LINKFLAGS_OPTIMIZED'] = ['-s']
	v['LINKFLAGS_RELEASE']   = ['-s']
	v['LINKFLAGS_DEBUG']     = ['-g']
	v['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	def addflags(var):
		try:
			c = os.environ[var]
			if c: v[var].append(c)
		except:
			pass

	addflags('CXXFLAGS')
	addflags('CPPFLAGS')

	if not v['DESTDIR']: v['DESTDIR']=''
	
	if sys.platform == "win32": 
		if not v['PREFIX']: v['PREFIX']='c:\\'

		# shared library 
		v['shlib_CXXFLAGS']  = ['']
		v['shlib_LINKFLAGS'] = ['-shared']
		v['shlib_obj_ext']   = ['.o']
		v['shlib_PREFIX']    = 'lib'
		v['shlib_SUFFIX']    = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.a']
	
		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext'] = ['.o']
		v['staticlib_PREFIX']= 'lib'
		v['staticlib_SUFFIX']= '.a'

		# program 
		v['program_obj_ext'] = ['.o']
		v['program_SUFFIX']  = '.exe'
	elif sys.platform == 'cygwin':
		if not v['PREFIX']: v['PREFIX']='/cygdrive/c/'

		# shared library 
		v['shlib_CXXFLAGS']  = ['']
		v['shlib_LINKFLAGS'] = ['-shared']
		v['shlib_obj_ext']   = ['.o']
		v['shlib_PREFIX']    = 'lib'
		v['shlib_SUFFIX']    = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.a']
	
		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext'] = ['.o']
		v['staticlib_PREFIX']= 'lib'
		v['staticlib_SUFFIX']= '.a'

		# program 
		v['program_obj_ext'] = ['.o']
		v['program_SUFFIX']  = '.exe'
	else:
		if not v['PREFIX']: v['PREFIX'] = '/usr'

		# shared library 
		v['shlib_CXXFLAGS']  = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS'] = ['-shared']
		v['shlib_obj_ext']   = ['.os']
		v['shlib_PREFIX']    = 'lib'
		v['shlib_SUFFIX']    = '.so'
	
		# static lib
		#v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_obj_ext'] = ['.o']
		v['staticlib_PREFIX']= 'lib'
		v['staticlib_SUFFIX']= '.a'

		# program 
		v['program_obj_ext'] = ['.o']
		v['program_SUFFIX']  = ''

	return 1

