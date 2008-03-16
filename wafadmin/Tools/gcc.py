#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import optparse
import Params, Configure

import ccroot

STOP = "stop"
CONTINUE = "continue"

def on_error(func_name, exc):
	if func_name == 'not_critical':
		env['foo'] = 'blah'
		return CONTINUE
	return STOP

def eval_rules(conf, rules, err_handler):
	for x in rules:
		try:
			# TODO check pre/post conditions
			x(conf)
		except Exception, e:
			raise
			if err_handler(x.__name__, e) == STOP:
				break
			else:
				raise

def find_program_c(conf):
	env = conf.env
	cc = None
	if env['CC']: cc = env['CC']
	elif 'CC' in os.environ: cc = os.environ['CC']
	if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc: conf.fatal('gcc was not found')
	env['CC']  = cc
	conf.check_tool('cc')

def find_ar(conf):
	env = conf.env
	conf.check_tool('ar')
	if not env['AR']: conf.fatal('gcc needs ar - not found')

def find_cpp(conf):
	env = conf.env
	if not env['CPP']:
		cpp = conf.find_program('cpp', var='CPP')
		if not cpp: cpp = cc
		env['CPP'] = cpp

def common_flags(conf):
	v = conf.env
	v['CC_TGT_F'] = '-c -o '
	v['CPPPATH_ST'] = '-I%s'

	v['LINK_CC'] = v['CC']
	v['LIB'] = []
	v['CCLNK_SRC_F'] = ''
	v['CCLNK_TGT_F'] = '-o '

	v['LIB_ST'] = '-l%s' # template for adding libs
	v['LIBPATH_ST'] = '-L%s' # template for adding libpaths

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

def modifier_win32(conf):
	# shared library
	v = conf.env
	v.append_unique('shlib_LINKFLAGS', '-shared')
	v['shlib_obj_ext'] = '.os'
	v['shlib_PREFIX'] = 'lib'
	v['shlib_SUFFIX'] = '.dll'
	v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']

	# static library
	v['staticlib_LINKFLAGS'] = ['']
	v['staticlib_obj_ext'] = '.o'
	v['staticlib_PREFIX'] = 'lib'
	v['staticlib_SUFFIX'] = '.a'

	# program
	v['program_obj_ext'] = '.o'
	v['program_SUFFIX'] = '.exe'

	# plugins, loadable modules.
	v['plugin_CCFLAGS'] = v['shlib_CCFLAGS']
	v['plugin_obj_ext'] = v['shlib_obj_ext']
	v['plugin_PREFIX'] = v['shlib_PREFIX']
	v['plugin_SUFFIX'] = v['shlib_SUFFIX']

funcs = [find_program_c, find_ar, find_cpp, common_flags, modifier_win32]

def detect(conf):

	# TODO FIXME later it will all start from eval_rules
	#eval_rules(conf, funcs, on_error)

	v = conf.env

	cc = None
	if v['CC']:
		cc = v['CC']
	elif 'CC' in os.environ:
		cc = os.environ['CC']
	if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc:
		conf.fatal('gcc was not found')

	conf.check_tool('checks')
	# load the cc builders
	conf.check_tool('cc')

	# gcc requires ar for static libs
	conf.check_tool('ar')
	if not v['AR']:
		conf.fatal('gcc needs ar - not found')

	if not v['CPP']:
		cpp = conf.find_program('cpp', var='CPP')
		if not cpp: cpp = cc
		v['CPP'] = cpp

	v['CC']  = cc

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
	v['LINKFLAGS']            = v['LINKFLAGS'] or []
	v['LINKFLAGS_OPTIMIZED']  = ['-s']
	v['LINKFLAGS_RELEASE']    = ['-s']
	v['LINKFLAGS_DEBUG']      = ['-g']
	v['LINKFLAGS_ULTRADEBUG'] = ['-g3']

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	if sys.platform == "win32":
		# shared library
		v['shlib_CCFLAGS']       = ['']
		v['shlib_LINKFLAGS']     = ['-shared']
		v['shlib_obj_ext']       = '.os'
		v['shlib_PREFIX']        = 'lib'
		v['shlib_SUFFIX']        = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']

		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext']   = '.o'
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program
		v['program_obj_ext']     = '.o'
		v['program_SUFFIX']      = '.exe'

		# plugins, loadable modules.
		v['plugin_CCFLAGS']      = v['shlib_CCFLAGS']
		v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
		v['plugin_obj_ext']      = v['shlib_obj_ext']
		v['plugin_PREFIX']       = v['shlib_PREFIX']
		v['plugin_SUFFIX']       = v['shlib_SUFFIX']
	elif sys.platform == 'cygwin':
		# shared library
		v['shlib_CCFLAGS']    = ['']
		v['shlib_LINKFLAGS']   = ['-shared']
		v['shlib_obj_ext']     = '.os'
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.dll'
		v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']

		# static library
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext'] = '.o'
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_obj_ext']   = '.o'
		v['program_SUFFIX']    = '.exe'

	elif sys.platform == "darwin":
		v['shlib_CCFLAGS']       = ['-fPIC']
		v['shlib_LINKFLAGS']     = ['-dynamiclib']
		v['shlib_obj_ext']       = '.os'
		v['shlib_PREFIX']        = 'lib'
		v['shlib_SUFFIX']        = '.dylib'

		# static lib
		v['staticlib_LINKFLAGS'] = ['']
		v['staticlib_obj_ext']   = '.o'
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program
		v['program_obj_ext']     = '.o'
		v['program_SUFFIX']      = ''

		# bundles
		v['plugin_LINKFLAGS']    = ['-bundle', '-undefined dynamic_lookup']
		v['plugin_obj_ext']      = '.os'
		v['plugin_CCFLAGS']      = ['-fPIC']
		v['plugin_PREFIX']       = ''
		v['plugin_SUFFIX']       = '.bundle'

		v['SHLIB_MARKER']        = ''
		v['STATICLIB_MARKER']    = ''

	elif sys.platform == 'aix5':
		# shared library
		v['shlib_CCFLAGS']     = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS']   = ['-shared','-Wl,-brtl,-bexpfull']
		v['shlib_obj_ext']     = '_sh.o'
		v['shlib_PREFIX']      = 'lib'
		v['shlib_SUFFIX']      = '.so'

		# plugins, loadable modules.
		v['plugin_CCFLAGS']    = v['shlib_CCFLAGS']
		v['plugin_LINKFLAGS']  = v['shlib_LINKFLAGS']
		v['plugin_obj_ext']    = v['shlib_obj_ext']
		v['plugin_PREFIX']     = v['shlib_PREFIX']
		v['plugin_SUFFIX']     = v['shlib_SUFFIX']

		# static lib
		v['staticlib_obj_ext'] = '.o'
		v['staticlib_PREFIX']  = 'lib'
		v['staticlib_SUFFIX']  = '.a'

		# program
		v['program_LINKFLAGS'] = ['-Wl,-brtl']
		v['program_obj_ext']   = '.o'
		v['program_SUFFIX']    = ''

		v['SHLIB_MARKER']      = ''
	else:
		# shared library
		v['shlib_CCFLAGS']       = ['-fPIC', '-DPIC']
		v['shlib_LINKFLAGS']     = ['-shared']
		v['shlib_obj_ext']       = '.os'
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
		v['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		v['staticlib_obj_ext']   = '.o'
		v['staticlib_PREFIX']    = 'lib'
		v['staticlib_SUFFIX']    = '.a'

		# program
		v['program_obj_ext']     = '.o'
		v['program_SUFFIX']      = ''

	conf.check_features()

	# FIXME make these checks totally optional
	# compiler debug levels
	if conf.check_flags('-Wall'):
		v['CCFLAGS'] = ['-Wall']
	if conf.check_flags('-O2'):
		v['CCFLAGS_OPTIMIZED'] = ['-O2']
		v['CCFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CCFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CCFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']

	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CCFLAGS', v['CCFLAGS_'+debug_level])

	conf.add_os_flags('CFLAGS', 'CCFLAGS')
	conf.add_os_flags('CPPFLAGS')
	conf.add_os_flags('LINKFLAGS')

	if not v['DESTDIR']: v['DESTDIR']=''

	v['program_INST_VAR'] = 'PREFIX'
	v['program_INST_DIR'] = 'bin'
	v['shlib_INST_VAR'] = 'PREFIX'
	v['shlib_INST_DIR'] = 'lib'
	v['staticlib_INST_VAR'] = 'PREFIX'
	v['staticlib_INST_DIR'] = 'lib'

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = ccroot.DEBUG_LEVELS.RELEASE,
		help = "Specify the debug level, does nothing if CFLAGS is set in the environment. [Allowed Values: '%s']" % "', '".join(ccroot.DEBUG_LEVELS.ALL),
		choices = ccroot.DEBUG_LEVELS.ALL,
		dest = 'debug_level')
	except optparse.OptionConflictError:
		# the g++ tool might have added that option already
		pass
