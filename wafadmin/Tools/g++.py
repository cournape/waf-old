#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils,Action

# tool specific setup
# is called when a build process is started 
def setup(env):
	# by default - when loading a compiler tool, it sets CC_SOURCE_TARGET to a string
	# like '%s -o %s' which becomes 'file.cpp -o file.o' when called
	cpp_vardeps    = ['CXX', 'CXXFLAGS', '_CPPDEFFLAGS', '_CXXINCFLAGS', 'CXX_ST']
	Action.GenAction('cpp', cpp_vardeps)

	# TODO: this is the same definitions as for gcc, should be separated to have independent setup
	link_vardeps   = ['LINK', 'LINKFLAGS', 'LINK_ST', '_LIBDIRFLAGS', '_LIBFLAGS']
	Action.GenAction('link', link_vardeps)

# tool detection and initial setup 
# is called when a configure process is started, 
# the values are cached for further build processes
def detect(env):

	comp = Utils.where_is('g++')
	if not comp:
		Utils.error('g++ was not found')
		return 1;

	# g++ requires ar for static libs
	if env.detect('ar'):
		return 1

	# this should be defined here
	env['PREFIX']         = '/usr/bin'
	env['DESTDIR']        = ''
	
	if sys.platform == "win32": 
		# c++ compiler
		env['CXX']             = comp
		env['CXXFLAGS']        = '-O2'
		env['_CPPDEFFLAGS']    = ''
		env['_CXXINCFLAGS']    = ''
		env['CXX_ST']          = '%s -c -o %s'

		# linker	
		env['LINK']            = comp
		env['LINKFLAGS']       = []
		env['LIB']             = []
		env['LINK_ST']         = '%s -o %s'
		env['_LIBDIRFLAGS']    = ''
		env['_LIBFLAGS']       = ''
	
		# TODO: for what kind of library is this used ? 
		env['LIBSUFFIX']       = '.dll'
	
		# shared library 
		env['shlib_CXXFLAGS']  = ['']
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
		# c++ compiler
		env['CXX']             = 'g++'
		env['CXXFLAGS']        = '-O2'
		env['_CPPDEFFLAGS']    = ''
		env['_CXXINCFLAGS']    = ''
		env['CXX_ST']          = '%s -c -o %s'
	
		# linker
		env['LINK']            = 'g++'
		env['LINKFLAGS']       = []
		env['LIB']             = []
		env['LINK_ST']         = '%s -o %s'
		env['_LIBDIRFLAGS']    = ''
		env['_LIBFLAGS']       = ''
	
		# TODO: for what kind of library is this used ? 
		env['LIBSUFFIX']       = '.so'
	
		# shared library 
		env['shlib_CXXFLAGS']  = ['-fPIC', '-DPIC']
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

