#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

from waflib.extras import fc
from waflib.Configure import conf

@conf
def find_ifort(conf):
	conf.find_program('ifort', var='FC')
	conf.env.FC_NAME = 'IFORT'

	v['FCLIB_ST']        = '-l%s'
	v['FCLIBPATH_ST']    = '-L%s'
	v['FCSTLIB_ST']        = '-l%s'
	v['FCSTLIBPATH_ST']    = '-L%s'

	v['FCSTLIB_MARKER'] = '-Wl,-Bstatic'
	v['FCSHLIB_MARKER'] = '-Wl,-Bdynamic'

@conf
def ifort_modifier_win32(conf):
    raise NotImplementedError("Ifort on win32 not yet implemented")

def configure(conf):
	conf.find_ifort()
	conf.find_ar()
	conf.fc_flags()

