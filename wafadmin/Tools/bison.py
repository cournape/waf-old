#! /usr/bin/env python
# encoding: utf-8
# John O'Meara, 2006

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan, cpp
from Params import debug, error, trace, fatal

# -o TGT ? or -b target without extension ? : to investigate
bison_str = '${BISON} -o ${TGT} ${BISONFLAGS} ${SRC}'

def yc_file(obj, node):

	fi = obj.file_in

	yctask = obj.create_task('bison', obj.env, 4)

	base, ext = os.path.splitext(node.m_name)
	yctask.m_inputs  = fi(node.m_name)
	yctask.m_outputs = fi(base+'.tab.cc')

	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = yctask.m_outputs
	cpptask.m_outputs = fi(base+'.tab.o')
	obj.p_compiletasks.append(cpptask)

def setup(env):
	if not sys.platform == 'win32':
		Params.g_colors['bison']='\033[94m'

	# create our action here
	Action.simple_action('bison', bison_str)

	# register the hook for use with cppobj
	if not env['handlers_cppobj_.yc']: env['handlers_cppobj_.yc'] = yc_file
	if not env['handlers_cppobj_.y']: env['handlers_cppobj_.y'] = yc_file

def detect(conf):
	bison = conf.checkProgram('bison', var='BISON')
	if not bison: return 0
	v = conf.env
	v['BISON']      = bison
	v['BISONFLAGS'] = '-d'
	return 1

