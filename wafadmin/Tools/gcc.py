#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Action

# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.cpp -o file.o' when called
	cc_vardeps     = ['CC', 'CCFLAGS', '_CPPDEFFLAGS', '_CINCFLAGS', 'CC_ST']
	Action.GenAction('cc', cc_vardeps)

	# TODO: this is the same definitions as for gcc, should be separated to have independent setup
	link_vardeps   = ['LINK', 'LINKFLAGS', 'LINK_ST', '_LIBDIRFLAGS', '_LIBFLAGS']
	Action.GenAction('link', link_vardeps)

def detect(env):

	comp = Utils.where_is('gcc')
	if not comp:
		Utils.error('gcc was not found')
		sys.exit(1)

	if sys.platform == "win32": 
		if not env['PREFIX']: env['PREFIX']='c:\\'

		# c compiler
		env['CC']             = comp
		env['CCFLAGS']        = '-O2'
		env['_CPPDEFFLAGS']   = ''
		env['_CINCFLAGS']     = ''
		env['CC_ST']          = '%s -c -o %s'

		# linker	
		env['LINK']            = comp
		env['LINKFLAGS']       = []
		env['LIB']             = []
		env['LINK_ST']         = '%s -o %s'
		env['_LIBDIRFLAGS']    = ''
		env['_LIBFLAGS']       = ''
	
		# shared library 
		env['shlib_CFLAGS']  = ['']
		env['shlib_LINKFLAGS'] = ['-shared']
		env['shlib_obj_ext']   = ['.o']
		env['shlib_PREFIX']    = 'lib'
		env['shlib_SUFFIX']    = '.dll'
	
		# static library
		env['staticlib_LINKFLAGS'] = ['']
		env['staticlib_obj_ext'] = ['.o']
		env['staticlib_PREFIX']= 'lib'
		env['staticlib_SUFFIX']= '.a'
	
		# program 
		env['program_obj_ext'] = ['.o']
		env['program_SUFFIX']  = '.exe'

	else:
		if not env['PREFIX']: env['PREFIX']='/usr'

		env['CC']             = comp
		env['CCFLAGS']        = '-O2'
		env['_CPPDEFFLAGS']   = ''
		env['_CINCFLAGS']     = ''
		env['CC_ST']          = '%s -c -o %s'
	
		# linker
		env['LINK']            = comp
		env['LINKFLAGS']       = []
		env['LIB']             = []
		env['LINK_ST']         = '%s -o %s'
		env['_LIBDIRFLAGS']    = ''
		env['_LIBFLAGS']       = ''
	
		# shared library 
		env['shlib_CFLAGS']    = ['-fPIC', '-DPIC']
		env['shlib_LINKFLAGS'] = ['-shared']
		env['shlib_obj_ext']   = ['.os']
		env['shlib_PREFIX']    = 'lib'
		env['shlib_SUFFIX']    = '.so'
	
		# static lib
		env['staticlib_LINKFLAGS'] = ['-Wl,-Bstatic']
		env['staticlib_obj_ext'] = ['.o']
		env['staticlib_PREFIX']= 'lib'
		env['staticlib_SUFFIX']= '.a'
	
		# program 
		env['program_obj_ext'] = ['.o']
		env['program_SUFFIX']  = ''
		
	return 0

