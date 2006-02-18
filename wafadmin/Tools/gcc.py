#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys
import Utils

def detect(env):

	comp = Utils.where_is('gcc')
	if not comp:
		Utils.error('gcc was not found')
		sys.exit(1)

	env['PREFIX']          = '/usr'
	env['DESTDIR']         = '/tmp/blah/'

	env['CXX']             = comp
	env['CXXFLAGS']        = '-O2'
	env['_CPPDEFFLAGS']    = ''
	env['_CXXINCFLAGS']    = ''
	env['CXX_ST']          = '%s -c -o %s'

	env['LINK']            = comp
	env['LINKFLAGS']       = []
	env['LIB']             = []
	env['LINK_ST']         = '%s -o %s'
	env['_LIBDIRFLAGS']    = ''
	env['_LIBFLAGS']       = ''

	env['LIBSUFFIX']       = '.so'

	env['shlib_CXXFLAGS']  = ['-fPIC', '-DPIC']
	env['shlib_LINKFLAGS'] = ['-shared']
	env['program_obj_ext'] = ['.o']
	env['shlib_obj_ext']   = ['.os']
	env['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
	env['staticlib_obj_ext'] = ['.o']

	if sys.platform=='win32': env['program_SUFFIX']  = '.exe'

	env['shlib_PREFIX']    = 'lib'
	env['shlib_SUFFIX']    = '.so'
	env['staticlib_PREFIX']= 'lib'
	env['staticlib_SUFFIX']= '.a'

	return 0

