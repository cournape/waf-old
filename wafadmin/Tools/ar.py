#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Configure, Action, Runner

ar_vardeps = ['AR', 'RANLIB', 'ARFLAGS', 'RANLIBFLAGS']
def ar_build(task):
	#reldir = task.m_inputs[0].cd_to()

	infiles = " ".join(  map(lambda a:a.bldpath(task.m_env), task.m_inputs)  )
	outfile = " ".join(  map(lambda a:a.bldpath(task.m_env), task.m_outputs)  )

	#infiles = task.m_inputs[0].bldpath()
	#outfile = task.m_outputs[0].m_name

	e=task.m_env
	s = '%s %s %s %s && %s %s %s'
	cmd = s % (e['AR'], e['ARFLAGS'], outfile, infiles, e['RANLIB'], e['RANLIBFLAGS'], outfile)
	return Runner.exec_command(cmd)

def setup(env):
	aract = Action.GenAction('cpp_link_static', ar_vardeps)
	aract.m_function_to_run = ar_build

	aract = Action.GenAction('cc_link_static', ar_vardeps)
	aract.m_function_to_run = ar_build

def detect(conf):

	comp = conf.checkProgram('ar', var='AR')
	if not comp:
		return 0;

	ranlib = conf.checkProgram('ranlib', var='RANLIB')
	if not ranlib:
		return 0

	conf.env['AR']                = comp
	conf.env['ARFLAGS']           = 'r'
	conf.env['RANLIB']            = ranlib
	conf.env['RANLIBFLAGS']       = ''
	return 1

