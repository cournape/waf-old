#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner

tex_vardeps    = ['TEX', 'TEXFLAGS', 'TEX_ST']
Action.GenAction('tex', tex_vardeps, src_only=1)

latex_vardeps  = ['LATEX', 'LATEXFLAGS', 'LATEX_ST']
act = Action.GenAction('latex', latex_vardeps)
def latex_build(task):
	com = task.m_env['LATEX']
	node = task.m_inputs[0]
	reldir  = node.cd_to()
	uppath = "".join(node.m_parent.invrelpath(Params.g_build.m_tree.m_bldnode))
	srcfile = os.path.join(uppath, node.bldpath())
	#print srcfile
	#sys.exit(0)

	cmd = 'cd %s && %s %s' % (reldir, com, srcfile)
	return Runner.exec_command(cmd)
act.m_function_to_run = latex_build

bibtex_vardeps = ['BIBTEX', 'BIBTEXFLAGS', 'BIBTEX_ST']
Action.GenAction('bibtex', bibtex_vardeps, src_only=1)

dvips_vardeps  = ['DVIPS', 'DVIPSFLAGS', 'DVIPS_ST']
Action.GenAction('dvips', dvips_vardeps)

dvipdf_vardeps = ['DVIPDF', 'DVIPDFFLAGS', 'DVIPDF_ST']
Action.GenAction('dvipdf', dvipdf_vardeps)

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
	conf.env['TEX']         = 'tex'
	conf.env['TEXFLAGS']    = ''
	conf.env['TEX_ST']      = '%s'

	conf.env['LATEX']       = 'latex'
	conf.env['LATEXFLAGS']  = ''
	conf.env['LATEX_ST']    = '%s'

	conf.env['BIBTEX']      = 'bibtex'
	conf.env['BIBTEXFLAGS'] = ''
	conf.env['BIBTEX_ST']   = '%s'

	conf.env['DVIPS']       = 'dvips'
	conf.env['DVIPSFLAGS']  = ''
	conf.env['DVIPS_ST']    = '%s -o %s'

	conf.env['DVIPDF']      = 'dvipdf'
	conf.env['DVIPDFFLAGS'] = ''
	conf.env['DVIPDF_ST']   = '%s -o %s'
	return 1

def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['latex']='\033[94m'
		Params.g_colors['tex']='\033[94m'

        Object.register('tex', texobj)


