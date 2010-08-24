#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

from waflib.extras import fc
from waflib.Configure import conf

@conf
def find_gfortran(conf):
	conf.find_program('gfortran', var='FC')
	conf.env.FC_NAME = 'GFORTRAN'

@conf
def gfortran_flags(conf):
	v = conf.env
	v['FCFLAGS_fcshlib']   = ['-fPIC']
	v['FORTRANMODFLAG']  = ['-M', ''] # template for module path
	v['FCFLAGS_DEBUG'] = ['-Werror'] # why not

	v['FCLIB_ST']        = '-l%s'
	v['FCLIBPATH_ST']    = '-L%s'
	v['FCSTLIB_ST']        = '-l%s'
	v['FCSTLIBPATH_ST']    = '-L%s'

	v['FCSTLIB_MARKER'] = '-Wl,-Bstatic'
	v['FCSHLIB_MARKER'] = '-Wl,-Bdynamic'

def configure(conf):
	conf.find_gfortran()
	conf.find_ar()
	conf.fc_flags()
	conf.gfortran_flags()

