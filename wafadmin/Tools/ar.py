#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)
# Ralf Habacker, 2006 (rh)

"ar and ranlib"

import os, sys
import Task
import Utils
from Configure import conftest

def detect(conf):
	comp = conf.find_program('ar', var='AR')
	if not comp: return

	ranlib = conf.find_program('ranlib', var='RANLIB')
	if not ranlib: return

	v = conf.env
	v['AR']          = comp
	v['ARFLAGS']     = 'rc'
	v['RANLIB']      = ranlib
	v['RANLIBFLAGS'] = ''

@conftest
def find_ar(conf):
	v = conf.env
	conf.check_tool('ar')
	if not v['AR']: conf.fatal('ar is required for static libraries - not found')

def ar_link_static(task):
	env = task.env

	# always remove the archive - prevents remnants of old object files
	# (renamed, deleted, etc.)
	tgt = task.outputs[0].bldpath(env)
	try: os.remove(tgt)
	except: pass

#	Windows:
#		ar_str = '${AR} s${ARFLAGS} ${TGT} ${SRC}'
#	Others:
#		ar_str = '${AR} ${ARFLAGS} ${TGT} ${SRC} && ${RANLIB} ${RANLIBFLAGS} ${TGT}'

	ar_flags = env['ARFLAGS']
	ranlib = ''
	if Utils.is_win32:
		ar_flags[0] = 's' + ar_flags[0]
	else:
		ranlib = ' && %s %s %s' % (env['RANLIB'], env['RANLIBFLAGS'], tgt)

	srcs = [a.srcpath(env) for a in task.inputs]
	command = '%s %s %s %s%s' % (env['AR'], ar_flags, tgt, ' '.join(srcs), ranlib)
	return task.exec_command(command)

cls = Task.task_type_from_func('ar_link_static', color='YELLOW', func=ar_link_static, ext_in='.o')
cls.maxjobs = 1

