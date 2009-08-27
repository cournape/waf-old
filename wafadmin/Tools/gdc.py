#!/usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)

import sys
import Utils, ar
from Configure import conftest

@conftest
def find_gdc(conf):
	conf.find_program('gdc', var='D_COMPILER', mandatory=True)

@conftest
def common_flags_gdc(conf):
	v = conf.env

	# _DFLAGS _DIMPORTFLAGS

	# for mory info about the meaning of this dict see dmd.py
	v['DFLAGS']            = []

	v['D_SRC_F']           = ''
	v['D_TGT_F']           = ['-c', '-o', '']
	v['DPATH_ST']          = '-I%s' # template for adding import paths

	# linker
	v['D_LINKER']          = v['D_COMPILER']
	v['DLNK_SRC_F']        = ''
	v['DLNK_TGT_F']        = ['-o', '']

	v['DLIB_ST']           = '-l%s' # template for adding libs
	v['DLIBPATH_ST']       = '-L%s' # template for adding libpaths

	# debug levels
	v['DLINKFLAGS']        = []
	v['DFLAGS_OPTIMIZED']  = ['-O3']
	v['DFLAGS_DEBUG']      = ['-O0']
	v['DFLAGS_ULTRADEBUG'] = ['-O0']

	v['D_shlib_DFLAGS']    = []
	v['D_shlib_LINKFLAGS'] = ['-shared']

	v['DHEADER_ext']       = '.di'
	v['D_HDR_F']           = '-fintfc -fintfc-file='

	binfmt = conf.env.DEST_BINFMT or Utils.unversioned_sys_platform_to_binary_format(
		conf.env.DEST_OS or Utils.unversioned_sys_platform())
	if binfmt == 'pe':
		v['D_program_PATTERN']   = '%s.exe'
		v['D_shlib_PATTERN']     = 'lib%s.dll'
		v['D_staticlib_PATTERN'] = 'lib%s.a'
	else:
		v['D_program_PATTERN']   = '%s'
		v['D_shlib_PATTERN']     = 'lib%s.so'
		v['D_staticlib_PATTERN'] = 'lib%s.a'

def detect(conf):
	conf.find_gdc()
	conf.check_tool('ar')
	conf.check_tool('d')
	conf.common_flags_gdc()

