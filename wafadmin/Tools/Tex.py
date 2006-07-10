#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner

# TODO: make this more simple
latex_vardeps  = ['LATEX', 'LATEXFLAGS', 'LATEX_ST']
def latex_build(task):
	com = task.m_env['LATEX']
	node = task.m_inputs[0]
	reldir  = node.cd_to()
	uppath = "".join(node.m_parent.invrelpath(Params.g_build.m_bldnode))
	srcfile = os.path.join(uppath, node.bldpath())
	#print srcfile
	#sys.exit(0)

	cmd = 'cd %s && %s %s' % (reldir, com, srcfile)
	return Runner.exec_command(cmd)


g_texobjs=['latex','tex','bibtex','dvips','dvipdf']
class texobj(Object.genobj):
	def __init__(self, type='latex'):
		Object.genobj.__init__(self, 'tex')

		global g_texobjs
		if not type in g_texobjs:
			Params.niceprint('type %s not supported for texobj', 'ERROR', 'texobj')
			import sys
			sys.exit(1)
		self.m_type   = type
		self.m_source = ''
		self.m_target = ''
	def apply(self):
		for filename in (' '+self.source).split():
			base, ext = os.path.splitext(filename)
			if not ext=='.tex': continue

			task = self.create_task('latex', self.env, 2)
			task.m_inputs = [ self.get_mirror_node( self.m_current_path, base+'.tex') ]
			task.m_outputs = [ self.get_mirror_node( self.m_current_path, base+'.dvi') ]

def detect(conf):
	v = conf.env

	v['TEX']         = 'tex'
	v['TEXFLAGS']    = ''

	v['LATEX']       = 'latex'
	v['LATEXFLAGS']  = ''

	v['BIBTEX']      = 'bibtex'
	v['BIBTEXFLAGS'] = ''

	v['DVIPS']       = 'dvips'
	v['DVIPSFLAGS']  = ''

	v['DVIPDF']      = 'dvipdf'
	v['DVIPDFFLAGS'] = ''
	return 1

def setup(env):
	Action.simple_action('tex', '${TEX} ${TEXFLAGS} ${SRC}', color='BLUE')
	Action.simple_action('bibtex', '${BIBTEX} ${BIBTEXFLAGS} ${SRC}', color='BLUE')
	Action.simple_action('dvips', '${DVIPS} ${DVIPSFLAGS} ${SRC} -o ${TGT}', color='BLUE')
	Action.simple_action('dvipdf', '${DVIPDF} ${DVIPDFFLAGS} ${SRC} -o ${TGT}', color='BLUE')

	Action.Action('latex', vars=latex_vardeps, func=latex_build)

        Object.register('tex', texobj)


