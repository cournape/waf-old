#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Action, Params

# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.c -o file.o' when called

        deb = Params.g_options.debug_level

        cc_str = '${CC} ${CCFLAGS} ${CCFLAGS%s} ${CPPFLAGS} ${_CCINCFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}' % deb
        Action.simple_action('cc', cc_str)

        # on windows libraries must be defined after the object files
        link_str = '${LINK} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT} ${LINKFLAGS} ${LINKFLAGS_%s} ${_LIBDIRFLAGS} ${_LIBFLAGS}' % deb
        Action.simple_action('cc_link', link_str)


	if not sys.platform == "win32":
		Params.g_colors['cc']='\033[92m'
		Params.g_colors['cc_link']='\033[93m'
		Params.g_colors['cc_link_static']='\033[93m'
		Params.g_colors['fakelibtool']='\033[94m'

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
	v['_CINCFLAGS']           = ''
	v['CC_SRC_F']             = ''
	v['CC_TGT_F']             = '-c -o '
	v['CPPPATH_ST']           = '-I%s' # template for adding include pathes

	# compiler debug levels
	v['CCFLAGS'] = []
	v['CCFLAGS_OPTIMIZED']    = ['-O2']
	v['CCFLAGS_RELEASE']      = ['-O2']
	v['CCFLAGS_DEBUG']        = ['-g', '-DDEBUG']
	v['CCFLAGS_ULTRADEBUG']   = ['-g3', '-O0', '-DDEBUG']
		
	# linker	
	v['LINK']                 = comp
	v['LIB']                  = []
	v['CCLNK_SRC_F']          = ''
	v['CCLNK_TGT_F']          = '-o '

	v['LIB_ST']               = '-l%s'	# template for adding libs
	v['LIBPATH_ST']           = '-L%s' # template for adding libpathes
	v['_LIBDIRFLAGS']         = ''
	v['_LIBFLAGS']            = ''

	# linker debug levels
	v['LINKFLAGS']            = []
	v['LINKFLAGS_OPTIMIZED']  = ['-s']
	v['LINKFLAGS_RELEASE']    = ['-s']
	v['LINKFLAGS_DEBUG']      = ['-g']
	v['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	def addflags(var):
		try:
			c = os.environ[var]
			if c: v[var].append(c)
		except:
			pass

	addflags('CCFLAGS')
	addflags('CPPFLAGS')

	if sys.platform == "win32": 
		if not v['PREFIX']: v['PREFIX']='c:\\'
	
		# shared library 
		v['shlib_CCFLAGS']  = ['']
		v['shlib_LINKFLAGS'] = ['-shared']
		v['shlib_obj_ext']   = ['.o']
		v['shlib_PREFIX']    = 'lib'
		v['shlib_SUFFIX']    = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']
	
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
		v['shlib_CCFLAGS']  = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS'] = ['-shared']
		v['shlib_obj_ext']   = ['.os']
		v['shlib_PREFIX']    = 'lib'
		v['shlib_SUFFIX']    = '.so'
	
		# static lib
		v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_obj_ext'] = ['.o']
		v['staticlib_PREFIX']= 'lib'
		v['staticlib_SUFFIX']= '.a'

		# program 
		v['program_obj_ext'] = ['.o']
		v['program_SUFFIX']  = ''

	return 1

