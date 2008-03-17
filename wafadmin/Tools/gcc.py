#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import optparse
import Params, Configure

import ccroot

STOP = "stop"
CONTINUE = "continue"


"""
Configuration issues:

The first problem is that some exceptions are critical
(compiler not found, ..) while others are not (the ar
program is only needed for static libraries)

The second problem is about the branching: how to extend
the configuration functions without hard-coding the names
and calling the functions

A third problem is to reuse the code and not copy-paste
everything each time a new compiler is added

The refactoring will be performed in three steps:
1 the code will be split into small functions
2 the irrelevant variables will be eliminated
3 a stack-based system will be used for calling the configuration functions
4 the user logic will go into the error recovery (for example, making some errors non-fatal)

Another solution to avoid an excessive amount of configuration variables is
to create platform-specific methods, in this case the following problems must be solved first:
attach functions dynamically to the c/c++ classes (without importing cpp.py or cc.py)
"""

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

def find_cc(conf):
	v = conf.env
	cc = None
	if v['CC']: cc = v['CC']
	elif 'CC' in os.environ: cc = os.environ['CC']
	if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc: conf.fatal('gcc was not found')
	v['CC']  = cc

def find_cpp(conf):
	v = conf.env
	cpp = None
	if v['CPP']: cpp = v['CPP']
	elif 'CPP' in os.environ: cpp = os.environ['CPP']
	if not cpp: cpp = conf.find_program('cpp', var='CPP')
	if not cpp: cpp = v['CC']
	v['CPP'] = cpp

def find_ar(conf):
	env = conf.env
	conf.check_tool('ar')
	if not env['AR']: conf.fatal('gcc requires ar - not found')

def common_flags(conf):
	v = conf.env

	# CPPFLAGS CCDEFINES _CCINCFLAGS _CCDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CC_SRC_F']             = ''
	v['CC_TGT_F']             = '-c -o '
	v['CPPPATH_ST']           = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']          = ''
	v['CCLNK_TGT_F']          = '-o '

	v['LIB_ST']               = '-l%s' # template for adding libs
	v['LIBPATH_ST']           = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']         = '-l%s'
	v['STATICLIBPATH_ST']     = '-L%s'
	v['CCDEFINES_ST']         = '-D%s'

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CCFLAGS']       = ['-fPIC', '-DPIC']
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
	v['shlib_CCFLAGS']       = ['']

	v['staticlib_LINKFLAGS'] = ['']

def modifier_cygwin(conf):
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CCFLAGS']       = ['']
	v['shlib_IMPLIB_SUFFIX'] = ['.dll.a']

	v['staticlib_LINKFLAGS'] = ['']

def modifier_darwin(conf):
	v = conf.env
	v['shlib_CCFLAGS']       = ['-fPIC']
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
		v['plugin_CCFLAGS']      = ['-fPIC']
		v['plugin_PATTERN']      = '%s.bundle'
	else:
		v['plugin_CCFLAGS']      = v['shlib_CCFLAGS']
		v['plugin_LINKFLAGS']    = v['shlib_LINKFLAGS']
		v['plugin_PATTERN']      = v['shlib_PATTERN']

def modifier_debug(conf):
	v = conf.env
	# compiler debug levels
	if conf.check_flags('-O2'):
		v['CCFLAGS_OPTIMIZED'] = ['-O2']
		v['CCFLAGS_RELEASE'] = ['-O2']
	if conf.check_flags('-g -DDEBUG'):
		v['CCFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG'):
		v['CCFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']
	if conf.check_flags('-Wall'):
		for x in 'OPTIMIZED RELEASE DEBUG ULTRADEBUG'.split(): v.append_unique('CCFLAGS_'+x, '-Wall')
	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CCFLAGS', v['CCFLAGS_'+debug_level])

def detect(conf):

	# TODO FIXME later it will start from eval_rules
	# funcs = [find_cc, find_cpp, find_ar, common_flags, modifier_win32]
	#eval_rules(conf, funcs, on_error)

	find_cc(conf)
	find_cpp(conf)
	find_ar(conf)

	conf.check_tool('cc')

	common_flags(conf)
	if sys.platform == 'win32': modifier_win32(conf)
	elif sys.platform == 'cygwin': modifier_cygwin(conf)
	elif sys.platform == 'darwin': modifier_darwin(conf)
	elif sys.platform == 'aix5': modifier_aix5(conf)
	modifier_plugin(conf)

	conf.check_tool('checks')
	conf.check_features()

	modifier_debug(conf)

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
		# the g++ tool might have added that option already
		pass
