#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Action, Params

# tool specific setup
# is called when a build process is started 
def setup(env):
	cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

        Action.simple_action('cc', cc_str, 'GREEN')

        # on windows libraries must be defined after the object files
        Action.simple_action('cc_link', link_str, color='YELLOW')

def detect(conf):
	cc = conf.checkProgram('cc', var='CC')
	if not cc:
		return 0;

	comp = conf.checkProgram('gcc', var='GCC')
	if not comp:
		return 0;

	# load the cc builders
	conf.checkTool('cc')

	# gcc requires ar for static libs
	if not conf.checkTool('ar'):
		Utils.error('gcc needs ar - not found')
		return 0

	v = conf.env

	# preprocessor (what is that ? ita)
	#v['CPP']             = cpp

	# cc compiler
	v['CC']                   = comp
	v['CPPFLAGS']             = []
	v['CCDEFINES']            = []
	v['_CCINCFLAGS']          = []
	v['_CCDEFFLAGS']          = []

	v['CC_SRC_F']             = ''
	v['CC_TGT_F']             = '-c -o '
	v['CPPPATH_ST']           = '-I%s' # template for adding include pathes

	# compiler debug levels
	v['CCFLAGS'] = ['-Wall']
	v['CCFLAGS_OPTIMIZED']    = ['-O2']
	v['CCFLAGS_RELEASE']      = ['-O2']
	v['CCFLAGS_DEBUG']        = ['-g', '-DDEBUG']
	v['CCFLAGS_ULTRADEBUG']   = ['-g3', '-O0', '-DDEBUG']

	# linker
	v['LINK_CC']              = comp
	v['LIB']                  = []
	v['CCLNK_SRC_F']          = ''
	v['CCLNK_TGT_F']          = '-o '

	v['LIB_ST']               = '-l%s'	# template for adding libs
	v['LIBPATH_ST']           = '-L%s' # template for adding libpathes
	v['STATICLIB_ST']         = '-l%s'
	v['STATICLIBPATH_ST']     = '-L%s'
	v['_LIBDIRFLAGS']         = ''
	v['_LIBFLAGS']            = ''
	v['CCDEFINES_ST']         = '-D%s'

	# linker debug levels
	v['LINKFLAGS']            = []
	v['LINKFLAGS_OPTIMIZED']  = ['-s']
	v['LINKFLAGS_RELEASE']    = ['-s']
	v['LINKFLAGS_DEBUG']      = ['-g']
	v['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

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

	addflags('CCFLAGS')
	addflags('CPPFLAGS')

	if sys.platform == "win32": 
		# shared library 
		v['shlib_CCFLAGS']       = ['']
		v['shlib_LINKFLAGS']     = ['-shared']
		v['shlib_obj_ext']       = ['.o']
		v['shlib_PREFIX']        = 'lib'
		v['shlib_SUFFIX']        = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']
	
		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext']   = ['.o']
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program 
		v['program_obj_ext']     = ['.o']
		v['program_SUFFIX']      = '.exe'

	elif sys.platform == "darwin":
		v['shlib_CCFLAGS']       = ['-fPIC']
		v['shlib_LINKFLAGS']     = ['-dynamiclib']
		v['shlib_obj_ext']       = ['.os']
		v['shlib_PREFIX']        = 'lib'
		v['shlib_SUFFIX']        = '.dynlib'

		# static lib
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext']   = ['.o']
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program
		v['program_obj_ext']     = ['.o']
		v['program_SUFFIX']      = ''

	else:
		# shared library 
		v['shlib_CCFLAGS']       = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS']     = ['-shared']
		v['shlib_obj_ext']       = ['.os']
		v['shlib_PREFIX']        = 'lib'
		v['shlib_SUFFIX']        = '.so'
	
		# static lib
		v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_obj_ext']   = ['.o']
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program 
		v['program_obj_ext']     = ['.o']
		v['program_SUFFIX']      = ''

	return 1

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = 'release',
		help = 'Specify the debug level. [Allowed Values: ultradebug, debug, release, optimized]',
		dest = 'debug_level')
	except:
		# the g++ tool might have added that option already
		pass

