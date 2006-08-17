#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Action, Params, Configure

# tool specific setup
# is called when a build process is started 
def setup(env):
	cpp_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_CXXDEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
	link_str = '${LINK_CXX} ${CPPLNK_SRC_F}${SRC} ${CPPLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

	Action.simple_action('cpp', cpp_str, color='GREEN')

	# on windows libraries must be defined after the object files 
	Action.simple_action('cpp_link', link_str, color='YELLOW')

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
	v['CXXDEFINES']          = [] # command-line defines

	v['_CXXINCFLAGS']        = []
	v['_CXXDEFFLAGS']        = []

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '-c -o '

	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# compiler debug levels
	v['CXXFLAGS']            = ['-Wall']
	v['CXXFLAGS_OPTIMIZED']  = ['-O2']
	v['CXXFLAGS_RELEASE']    = ['-O2']
	v['CXXFLAGS_DEBUG']      = ['-g', '-DDEBUG']
	v['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	# linker	
	v['LINK_CXX']            = comp
	v['LIB']                 = []

	v['CPPLNK_TGT_F']        = '-o '
	v['CPPLNK_SRC_F']        = ''


	v['LIB_ST']              = '-l%s'	# template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpathes
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CXXDEFINES_ST']       = '-D%s'
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

	try:
		deb = Params.g_options.debug_level
		v['CCFLAGS']   += v['CCFLAGS_'+deb]
		v['LINKFLAGS'] += v['LINKFLAGS_'+deb]
	except:
		pass

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

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = 'release',
		help = 'Specify the debug level. [Allowed Values: ultradebug, debug, release, optimized]',
		dest = 'debug_level')
	except:
		# the gcc tool might have added that option already
		pass

