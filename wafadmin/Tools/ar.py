#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Configure, Action, Runner

ar_str = '${AR} ${ARFLAGS} ${TGT} ${SRC} && ${RANLIB} ${RANLIBFLAGS} ${TGT}'

def setup(env):
	Action.simple_action('cpp_link_static', ar_str)
	Action.simple_action('cc_link_static', ar_str)

def detect(conf):

	comp = conf.checkProgram('ar', var='AR')
	if not comp: return 0;

	ranlib = conf.checkProgram('ranlib', var='RANLIB')
	if not ranlib: return 0

	v = conf.env
	v['AR']          = comp
	v['ARFLAGS']     = 'r'
	v['RANLIB']      = ranlib
	v['RANLIBFLAGS'] = ''
	return 1

