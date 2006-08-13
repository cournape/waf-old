#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner

latex_vardeps  = ['LATEX']
def latex_build(task):
	com = task.m_env['LATEX']
	node = task.m_inputs[0]
	reldir  = node.cd_to(task.m_env)

	srcfile = node.srcpath(task.m_env)

	lst = []
	for c in reldir.split(os.sep):
		if c: lst.append('..')
	sr = os.sep.join(lst + [srcfile])
	sr2 = os.sep.join(lst + [node.m_parent.srcpath(task.m_env)])

	aux_node = node.change_ext('.aux')

	hash     = ''
	old_hash = ''

	i = 0
	while i < 10:
		# prevent against infinite loops
		i += 1

		# watch the contents of file.aux
		old_hash = hash
		try:
			hash = Utils.h_md5_file(aux_node.abspath(task.m_env))
		except:
			pass

		# debug
		#print "hash is, ", hash, " ", old_hash

		# stop if file.aux does not change anymore
		if hash and hash == old_hash: break

		# run the command
		cmd = 'cd %s && TEXINPUTS=%s:$TEXINPUTS %s %s' % (reldir, sr2, com, sr)
		ret = Runner.exec_command(cmd)
		if ret: return ret

	# 0 means no error
	return 0

g_texobjs=['latex','tex','bibtex','dvips','dvipdf']
class texobj(Object.genobj):
	s_default_ext = ['.tex', '.ltx']
	def __init__(self, type='latex'):
		Object.genobj.__init__(self, 'tex')

		global g_texobjs
		if not type in g_texobjs:
			Params.niceprint('type %s not supported for texobj', 'ERROR', 'texobj')
			import sys
			sys.exit(1)
		self.m_type   = type
		self.outs     = '' # example: "ps pdf"
	def apply(self):
		
		outs = self.outs.split()

		for filename in self.source.split():
			base, ext = os.path.splitext(filename)
			if not ext in self.s_default_ext: continue

			node = self.m_current_path.find_node( filename.split(os.sep) )
			if not node: fatal('cannot find %s' % filename)

			task = self.create_task('latex', self.env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.dvi'))


			if 'ps' in outs:
				pstask = self.create_task('dvips', self.env, 40)
				pstask.set_inputs(task.m_outputs)
				pstask.set_outputs(node.change_ext('.ps'))
			if 'pdf' in outs:
				pdftask = self.create_task('dvipdf', self.env, 40)
				pdftask.set_inputs(task.m_outputs)
				pdftask.set_outputs(node.change_ext('.pdf'))

def detect(conf):
	v = conf.env

	v['TEX']         = conf.find_program('tex')
	v['TEXFLAGS']    = ''

	v['LATEX']       = conf.find_program('latex')
	v['LATEXFLAGS']  = ''

	v['BIBTEX']      = conf.find_program('bibtex')
	v['BIBTEXFLAGS'] = ''

	v['DVIPS']       = conf.find_program('dvips')
	v['DVIPSFLAGS']  = ''

	v['DVIPDF']      = conf.find_program('dvipdf')
	v['DVIPDFFLAGS'] = ''
	return 1

def setup(env):
	Action.simple_action('tex', '${TEX} ${TEXFLAGS} ${SRC}', color='BLUE')
	Action.simple_action('bibtex', '${BIBTEX} ${BIBTEXFLAGS} ${SRC}', color='BLUE')
	Action.simple_action('dvips', '${DVIPS} ${DVIPSFLAGS} ${SRC} -o ${TGT}', color='BLUE')
	Action.simple_action('dvipdf', '${DVIPDF} ${DVIPDFFLAGS} ${SRC} ${TGT}', color='BLUE')

	Action.Action('latex', vars=latex_vardeps, func=latex_build)

        Object.register('tex', texobj)


