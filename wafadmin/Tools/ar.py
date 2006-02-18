#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)
# Ralf Habacker, 2006 (rh)

import os, sys
import Utils, Configure, Action, Runner

ar_vardeps = ['AR', 'RANLIB', 'ARFLAGS', 'RANLIBFLAGS']
def ar_build(task):
	#reldir = task.m_inputs[0].cd_to()

	infiles = " ".join(  map(lambda a:a.bldpath(), task.m_inputs)  )
	outfile = " ".join(  map(lambda a:a.bldpath(), task.m_outputs)  )

	#infiles = task.m_inputs[0].bldpath()
	#outfile = task.m_outputs[0].m_name

	e=task.m_env
	s = '%s %s %s %s && %s %s %s'
	cmd = s % (e['AR'], e['ARFLAGS'], outfile, infiles, e['RANLIB'], e['RANLIBFLAGS'], outfile)
	return Runner.exec_command(cmd)

def setup(env):
	aract = Action.GenAction('arlink', ar_vardeps)
	aract.m_function_to_run = ar_build

def detect(env):
	comp = Utils.where_is('ar')
	if not comp:
		Utils.error('ar was not found')
		return 1

	ranlib = Utils.where_is('ranlib')
	if not ranlib:
		Utils.error('ranlib was not found')
		return 1

	env['AR']                = comp
	env['ARFLAGS']           = 'r'
	env['RANLIB']            = ranlib
	env['RANLIBFLAGS']       = ''

	return 0

