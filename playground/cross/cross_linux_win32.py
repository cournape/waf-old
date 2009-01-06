#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2008 (ita)

import Utils
import ccroot
from Configure import conftest

@conftest
def find_mingw_cc(conf):
	v = conf.env
	v['CC'] = None
	cc = conf.find_program('mingw32-gcc', var='CC')
	if not cc: cc = conf.find_program('mingw32-cc', var='CC')
	if not cc: conf.fatal('mingw32-gcc was not found')
	try:
		if Utils.cmd_output('%s --version' % cc).find('mingw') < 0:
			conf.fatal('mingw32-gcc was not found, see the result of gcc --version')
	except ValueError:
		conf.fatal('gcc --version could not be executed')
	v['CC'] = v['LINK_CC'] = cc
	v['CC_NAME'] = 'gcc'
	ccroot.get_cc_version(conf, cc, 'CC_VERSION')

@conftest
def find_mingw_cxx(conf):
	v = conf.env
	v['CXX'] = None
	cxx = conf.find_program('mingw32-g++', var='CXX')
	if not cxx: cxx = conf.find_program('mingw32-c++', var='CXX')
	if not cxx: conf.fatal('mingw32-g++ was not found')
	try:
		if Utils.cmd_output('%s --version' % cxx).find('mingw') < 0:
			conf.fatal('mingw32-g++ was not found, see the result of g++ --version')
	except ValueError:
		conf.fatal('g++ --version could not be executed')
	v['CXX'] = v['LINK_CXX'] = cxx
	v['CXX_NAME'] = 'gcc'
	ccroot.get_cc_version(conf, cxx, 'CXX_VERSION')


detect = 'find_mingw_cc find_mingw_cxx'

