#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, optparse, sys, re
import Params, Configure
import ccroot, ar
from Configure import conftest

get_version_re = re.compile('\d+\.\d+\.?\d+')
def get_gxx_version(conf, cc):
        v = conf.env
        output = os.popen('%s --version' % cc).read()
        if output:
                lines = output.split('\n')
                match = get_version_re.search(lines[0])
                if match:
                        v['CXX_VERSION_STRING'] = lines[0]
                        v['CXX_VERSION'] = match.group(0)
                        conf.check_message('compiler','version',1,'Version: '
                                           + v['CXX_VERSION'] + ' ('
                                           + v['CXX_VERSION_STRING'] + ')')
                        return v['CXX_VERSION']
        Params.warning('couldn\'t determine compiler version')

@conftest
def find_gxx(conf):
	v = conf.env
	cc = None
	if v['CXX']: cc = v['CXX']
	elif 'CXX' in os.environ: cc = os.environ['CXX']
	if not cc: cc = conf.find_program('g++', var='CXX')
	if not cc: cc = conf.find_program('c++', var='CXX')
	if not cc: conf.fatal('g++ was not found')
	v['CXX']  = cc
        if not v['CXX_NO_VERSION']:
                get_gxx_version(conf, cc)

@conftest
def gxx_common_flags(conf):
	v = conf.env

	# CPPFLAGS CXXDEFINES _CXXINCFLAGS _CXXDEFFLAGS _LIBDIRFLAGS _LIBFLAGS

	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '-c -o '
	v['CPPPATH_ST']          = '-I%s' # template for adding include paths

	# linker
	if not v['LINK_CXX']: v['LINK_CXX'] = v['CXX']
	v['CXXLNK_SRC_F']        = ''
	v['CXXLNK_TGT_F']        = '-o '

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['CXXDEFINES_ST']       = '-D%s'

	v['SHLIB_MARKER']        = '-Wl,-Bdynamic'
	v['STATICLIB_MARKER']    = '-Wl,-Bstatic'

	# program
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CXXFLAGS']      = ['-fPIC', '-DPIC']
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
def gxx_modifier_win32(conf):
	if sys.platform != 'win32': return
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CXXFLAGS']      = ['']

	v['staticlib_LINKFLAGS'] = ['']

@conftest
def gxx_modifier_cygwin(conf):
	if sys.platform != 'cygwin': return
	v = conf.env
	v['program_PATTERN']     = '%s.exe'

	v['shlib_PATTERN']       = 'lib%s.dll'
	v['shlib_CXXFLAGS']      = ['']

	v['staticlib_LINKFLAGS'] = ['']

@conftest
def gxx_modifier_darwin(conf):
	if sys.platform != 'darwin': return
	v = conf.env
	v['shlib_CXXFLAGS']      = ['-fPIC']
	v['shlib_LINKFLAGS']     = ['-dynamiclib']
	v['shlib_PATTERN']       = 'lib%s.dylib'

	v['staticlib_LINKFLAGS'] = ['']

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

@conftest
def gxx_modifier_aix5(conf):
	if sys.platform != 'aix5': return
	v = conf.env
	v['program_LINKFLAGS']   = ['-Wl,-brtl']

	v['shlib_LINKFLAGS']     = ['-shared','-Wl,-brtl,-bexpfull']

	v['SHLIB_MARKER']        = ''

@conftest
def gxx_modifier_debug(conf, kind='cpp'):
	v = conf.env
	# compiler debug levels
	if conf.check_flags('-O2 -DNDEBUG', kind=kind):
		v['CXXFLAGS_OPTIMIZED'] = ['-O2', '-DNDEBUG']
		v['CXXFLAGS_RELEASE'] = ['-O2', '-DNDEBUG']
	if conf.check_flags('-g -DDEBUG', kind=kind):
		v['CXXFLAGS_DEBUG'] = ['-g', '-DDEBUG']
	if conf.check_flags('-g3 -O0 -DDEBUG', kind=kind):
		v['CXXFLAGS_ULTRADEBUG'] = ['-g3', '-O0', '-DDEBUG']
	if conf.check_flags('-Wall', kind=kind):
		for x in 'OPTIMIZED RELEASE DEBUG ULTRADEBUG'.split(): v.append_unique('CXXFLAGS_'+x, '-Wall')
	try:
		debug_level = Params.g_options.debug_level.upper()
	except AttributeError:
		debug_level = ccroot.DEBUG_LEVELS.CUSTOM
	v.append_value('CXXFLAGS', v['CXXFLAGS_'+debug_level])

detect = '''
find_gxx
find_cpp
find_ar
gxx_common_flags
gxx_modifier_win32
gxx_modifier_cygwin
gxx_modifier_darwin
gxx_modifier_aix5
cxx_load_tools
cxx_check_features
gxx_modifier_debug
cxx_add_flags
'''

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = ccroot.DEBUG_LEVELS.RELEASE,
		help = "Specify the debug level, does nothing if CXXFLAGS is set in the environment. [Allowed Values: '%s']" % "', '".join(ccroot.DEBUG_LEVELS.ALL),
		choices = ccroot.DEBUG_LEVELS.ALL,
		dest = 'debug_level')
	except optparse.OptionConflictError:
		pass
