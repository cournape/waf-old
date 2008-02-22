#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)
# Ralf Habacker, 2006 (rh)

"ar and ranlib"

import Action, sys

ar_str = '${AR} ${ARFLAGS} ${TGT} ${SRC} && ${RANLIB} ${RANLIBFLAGS} ${TGT}'

# FIXME
if sys.platform == "win32":
	ar_str = '${AR} s${ARFLAGS} ${TGT} ${SRC}'
Action.simple_action('ar_link_static', ar_str, color='YELLOW', prio=101)

def detect(conf):
	comp = conf.find_program('ar', var='AR')
	if not comp: return

	ranlib = conf.find_program('ranlib', var='RANLIB')
	if not ranlib: return

	v = conf.env
	v['AR']          = comp
	v['ARFLAGS']     = 'r'
	v['RANLIB']      = ranlib
	v['RANLIBFLAGS'] = ''

