#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2010 (ita)
# Ralf Habacker, 2006 (rh)
# Yinon Ehrlich, 2009
# Michael Kuhn, 2009

import os, sys
from waflib.Tools import ccroot, ar
from waflib.Configure import conf

@conf
def find_xlc(conf):
	cc = conf.find_program(['xlc_r', 'xlc'], var='CC')
	cc = conf.cmd_to_list(cc)
	conf.env.CC_NAME = 'xlc'
	conf.env.CC      = cc

@conf
def xlc_common_flags(conf):
	v = conf.env

	# CPPFLAGS DEFINES _CCINCFLAGS _CCDEFFLAGS
	v['CCFLAGS_DEBUG'] = ['-g']
	v['CCFLAGS_RELEASE'] = ['-O2']

	v['CC_SRC_F']            = ''
	v['CC_TGT_F']            = ['-c', '-o', ''] # shell hack for -MD

	# linker
	if not v['LINK_CC']: v['LINK_CC'] = v['CC']
	v['CCLNK_SRC_F']         = ''
	v['CCLNK_TGT_F']         = ['-o', ''] # shell hack for -MD

	v['LIB_ST']              = '-l%s' # template for adding libs
	v['LIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['STATICLIB_ST']        = '-l%s'
	v['STATICLIBPATH_ST']    = '-L%s'
	v['RPATH_ST']            = '-Wl,-rpath,%s'
	v['DEFINES_ST']        = '-D%s'

	v['SONAME_ST']           = ''
	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''
	v['FULLSTATIC_MARKER']   = '-static'

	# program
	v['program_LINKFLAGS']   = ['-Wl,-brtl']
	v['program_PATTERN']     = '%s'

	# shared library
	v['shlib_CCFLAGS']       = ['-fPIC', '-DPIC'] # avoid using -DPIC, -fPIC aleady defines the __PIC__ macro
	v['shlib_LINKFLAGS']     = ['-G', '-Wl,-brtl,-bexpfull']
	v['shlib_PATTERN']       = 'lib%s.so'

	# static lib
	v['stlib_LINKFLAGS'] = ''
	v['stlib_PATTERN']   = 'lib%s.a'

def configure(conf):
	conf.find_xlc()
	conf.find_ar()
	conf.xlc_common_flags()
	conf.cc_load_tools()
	conf.cc_add_flags()
