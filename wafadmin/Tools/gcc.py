#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)
# Ralf Habacker, 2006 (rh)

import os, optparse, sys
import Params, Configure
import ccroot, ar
from Configure import conftest

@conftest
def find_gcc(conf):
	v = conf.env
	cc = None
	if v['CC']: cc = v['CC']
	elif 'CC' in os.environ: cc = os.environ['CC']
	if not cc: cc = conf.find_program('gcc', var='CC')
	if not cc: cc = conf.find_program('cc', var='CC')
	if not cc: conf.fatal('gcc was not found')
	v['CC']  = cc

@conftest
def gcc_common_flags(conf):
	v = conf.env

	# CPPFLAGS CCDEFINES _CCINCFLAGS _CCDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = '-c -o '
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = '-o '

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CCDEFINES_ST']        = '-D%s'

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

	# osx stuff
	v['MACBUNDLE_LINKFLAGS'] = ['-bundle', '-undefined dynamic_lookup']
	v['MACBUNDLE_CCFLAGS']   = ['-fPIC']
	v['MACBUNDLE_PATTERN']   = '%s.bundle'

@conftest
def gcc_modifier_win32(conf):
	v = conf.env
	if sys.platform != 'win32': return
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CCFLAGS']       = []

	v['staticlib_LINKFLAGS'] = []

@conftest
def gcc_modifier_cygwin(conf):
	v = conf.env
	if sys.platform != 'cygwin': return
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CCFLAGS']       = []

	v['staticlib_LINKFLAGS'] = []

@conftest
def gcc_modifier_darwin(conf):
	v = conf.env
	if sys.platform != 'darwin': return
	v['shlib_CCFLAGS']       = ['-fPIC']
	v['shlib_LINKFLAGS']     = ['-dynamiclib']
	v['shlib_PATTERN']       = 'lib%s.dylib'

	v['staticlib_LINKFLAGS'] = []

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

@conftest
def gcc_modifier_aix5(conf):
	v = conf.env
	if sys.platform != 'aix5': return
	v['program_LINKFLAGS']   = ['-Wl,-brtl']

	v['shlib_LINKFLAGS']     = ['-shared','-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

@conftest
def gcc_modifier_debug(conf):
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

detect = '''
find_gcc
find_cpp
find_ar
gcc_common_flags
gcc_modifier_win32
gcc_modifier_cygwin
gcc_modifier_darwin
gcc_modifier_aix5
cc_load_tools
cc_check_features
gcc_modifier_debug
cc_add_flags
'''

"""
If you want to remove the tests you do not want, use something like this:

conf.check_tool('gcc', funs='''
find_gcc
find_cpp
find_ar
gcc_common_flags
gcc_modifier_win32
gcc_modifier_cygwin
gcc_modifier_darwin
gcc_modifier_aix5
cc_add_flags
cc_load_tools
'''
)"""

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = ccroot.DEBUG_LEVELS.RELEASE,
		help = "Specify the debug level, does nothing if CFLAGS is set in the environment. [Allowed Values: '%s']" % "', '".join(ccroot.DEBUG_LEVELS.ALL),
		choices = ccroot.DEBUG_LEVELS.ALL,
		dest = 'debug_level')
	except optparse.OptionConflictError:
		pass

