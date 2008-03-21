#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)

import sys

def find_gdc(conf):
	v = conf.env
	d_compiler = None
	if v['D_COMPILER']:
		d_compiler = v['D_COMPILER']
	if not d_compiler: d_compiler = conf.find_program('gdc', var='D_COMPILER')
	if not d_compiler: return 0
	v['D_COMPILER'] = d_compiler

def find_ar(conf):
	v = conf.env
	conf.check_tool('ar')
	if not v['AR']: conf.fatal('ar is required for shared libraries - not found')

def common_flags(conf):
	v = conf.env

	#compiler
	v['D_COMPILER']           = d_compiler

	# for mory info about the meaning of this dict see dmd.py
	v['DFLAGS']               = {'gdc':[], 'dmd':[]}
	v['_DFLAGS']              = []

	v['_DIMPORTFLAGS']        = []

	v['D_SRC_F']              = ''
	v['D_TGT_F']              = '-c -o '
	v['DPATH_ST']             = '-I%s' # template for adding import paths

	# linker
	v['D_LINKER']             = v['D_COMPILER']
	v['DLNK_SRC_F']           = ''
	v['DLNK_TGT_F']           = '-o '

	v['DLIB_ST']              = '-l%s' # template for adding libs
	v['DLIBPATH_ST']          = '-L%s' # template for adding libpaths
	v['_DLIBDIRFLAGS']        = ''
	v['_DLIBFLAGS']           = ''

	# debug levels
	v['DLINKFLAGS']            = []
	v['DFLAGS_OPTIMIZED']      = ['-O3']
	v['DFLAGS_DEBUG']          = ['-O0']
	v['DFLAGS_ULTRADEBUG']     = ['-O0']

	if sys.platform == "win32":
		# shared library
		v['D_shlib_DFLAGS']        = ['']
		v['D_shlib_LINKFLAGS']     = ['-shared']
		v['D_shlib_PREFIX']        = 'lib'
		v['D_shlib_SUFFIX']        = '.dll'

		# static library
		v['D_staticlib_PREFIX']    = 'lib'
		v['D_staticlib_SUFFIX']    = '.a'

		# program
		v['D_program_PREFIX']      = ''
		v['D_program_SUFFIX']      = '.exe'

	else:
		# shared library
		v['D_shlib_DFLAGS']        = ['']
		v['D_shlib_LINKFLAGS']     = ['-shared']
		v['D_shlib_PREFIX']        = 'lib'
		v['D_shlib_SUFFIX']        = '.so'

		# static lib
		v['D_staticlib_PREFIX']    = 'lib'
		v['D_staticlib_SUFFIX']    = '.a'

		# program
		v['D_program_PREFIX']      = ''
		v['D_program_SUFFIX']      = ''

def detect(conf):
	v = conf.env
	find_gdc(conf)
	find_ar(conf)
	conf.check_tool('d')
	common_flags(conf)

def set_options(opt):
	pass
