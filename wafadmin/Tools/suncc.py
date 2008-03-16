#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, Object
import optparse
import Utils, Action, Params, Configure
import ccroot

def detect(conf):
	cc = None
	if conf.env['CC']:
		cc = conf.env['CC']
	elif 'CC' in os.environ:
		cc = os.environ['CC']
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc:
		return 0
	#TODO: Has anyone a better idea to check if this is a sun cc?
	ret = os.popen("%s -flags" %cc).close()
	if ret:
		conf.check_message('suncc', '', not ret)
		return
	conf.check_tool('checks')

	# load the cc builders
	conf.check_tool('cc')

	# sun cc requires ar for static libs
	conf.check_tool('ar')

	v = conf.env

	cpp = cc

	v['CC']  = cc
	v['CPP'] = cpp

	v['CPPFLAGS']             = []
	v['CCDEFINES']            = []
	v['_CCINCFLAGS']          = []
	v['_CCDEFFLAGS']          = []

	v['CC_SRC_F']             = ''
	v['CC_TGT_F']             = '-c -o '
	v['CPPPATH_ST']           = '-I%s' # template for adding include paths

	# linker
	v['LINK_CC']              = v['CC']
	v['LIB']                  = []

	v['CCLNK_SRC_F']          = ''
	v['CCLNK_TGT_F']          = '-o '

	v['LIB_ST']               = '-l%s' # template for adding libs
	v['LIBPATH_ST']           = '-L%s' # template for adding libpaths
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

	v['SHLIB_MARKER']        = '-Bdynamic'
	v['STATICLIB_MARKER']    = '-Bstatic'

	# shared library
	v['shlib_CCFLAGS']       = ['-Kpic', '-DPIC']
	v['shlib_LINKFLAGS']     = ['-G']
	v['shlib_obj_ext']       = '.o'
	v['shlib_PREFIX']        = 'lib'
	v['shlib_SUFFIX']        = '.so'

	# plugins. We handle them exactly as shlibs
	# everywhere except on osx, where we do bundles
	v['plugin_CCFLAGS']      = v['shlib_CCFLAGS']
	v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
	v['plugin_obj_ext']      = v['shlib_obj_ext']
	v['plugin_PREFIX']       = v['shlib_PREFIX']
	v['plugin_SUFFIX']       = v['shlib_SUFFIX']

	# static lib
	v['staticlib_LINKFLAGS'] = ['-Bstatic']
	v['staticlib_obj_ext']   = '.o'
	v['staticlib_PREFIX']    = 'lib'
	v['staticlib_SUFFIX']    = '.a'

	# program
	v['program_obj_ext']     = '.o'
	v['program_SUFFIX']      = ''

	conf.check_features(kind='cpp')

	# compiler debug levels
	v['CCFLAGS'] = ['-O']
	if conf.check_flags('-O2'):
		v['CCFLAGS_OPTIMIZED'] = ['-O2']
		v['CCFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CCFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CCFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	# see the option below
	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CCFLAGS', v['CCFLAGS_'+debug_level])

	conf.add_os_flags('CFLAGS', 'CCFLAGS')
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
		# the sunc++ tool might have added that option already
		pass

