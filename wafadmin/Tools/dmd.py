#!/usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2008-2010 (ita)

import sys
from wafadmin.Tools import ar
from wafadmin.Configure import conf

@conf
def find_dmd(conf):
	conf.find_program(['dmd', 'ldc'], var='D')

@conf
def common_flags_ldc(conf):
	v = conf.env
	v['DFLAGS']         = ['-d-version=Posix']
	v['DLINKFLAGS']     = []
	v['D_shlib_DFLAGS'] = ['-relocation-model=pic']

@conf
def common_flags_dmd(conf):
	v = conf.env

	# _DFLAGS _DIMPORTFLAGS

	# Compiler is dmd so 'gdc' part will be ignored, just
	# ensure key is there, so wscript can append flags to it
	v['DFLAGS']            = ['-version=Posix']

	v['D_SRC_F']           = ''
	v['D_TGT_F']           = ['-c', '-of']

	# linker
	v['D_LINKER']          = v['D']
	v['DLNK_SRC_F']        = ''
	v['DLNK_TGT_F']        = '-of'

	v['DLIB_ST']           = '-L-l%s' # template for adding libs
	v['DLIBPATH_ST']       = '-L-L%s' # template for adding libpaths

	# linker debug levels
	v['DFLAGS_OPTIMIZED']  = ['-O']
	v['DFLAGS_DEBUG']      = ['-g', '-debug']
	v['DFLAGS_ULTRADEBUG'] = ['-g', '-debug']
	v['DLINKFLAGS']        = ['-quiet']

	v['dshlib_DFLAGS']    = ['-fPIC']
	v['dshlib_LINKFLAGS'] = ['-L-shared']

	v['DHEADER_ext']       = '.di'
	v['D_HDR_F']           = ['-H', '-Hf']

def configure(conf):
	conf.find_dmd()
	conf.check_tool('ar')
	conf.check_tool('d')
	conf.common_flags_dmd()
	conf.d_platform_flags()

	if str(conf.env.D).find('ldc') > -1:
		conf.common_flags_ldc()

