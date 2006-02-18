#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys
import Utils

def detect(env):

	env.setValue('GCC_IS_FOUND', 0)

	comp = os.popen('which g++').read().strip()
	if not comp:
		Utils.error('g++ was not found')
		sys.exit(1)

	env.setValue('PREFIX', '/usr')
	env.setValue('DESTDIR', '/tmp/blah/')

	env.setValue('CXX', comp)
	env.setValue('CXXFLAGS', '-O2')
	env.setValue('_CPPDEFFLAGS', '')
	env.setValue('_CXXINCFLAGS', '')
	env.setValue('CXX_ST','%s -c -o %s')

	env.setValue('LINK', comp)
	env.setValue('LINKFLAGS',[])
	env.setValue('LIB',[])
	env.setValue('LINK_ST','%s -o %s')
	env.setValue('_LIBDIRFLAGS','')
	env.setValue('_LIBFLAGS','')

	env.setValue('GCC_IS_FOUND', 1)

	return 0
