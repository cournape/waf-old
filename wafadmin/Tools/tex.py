#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"TeX/LaTeX/PDFLaTeX support"

import os, re
import Utils, Params, TaskGen, Task, Runner, Scan
from Params import error, warning, debug, fatal

re_tex = re.compile(r'\\(?P<type>include|import|bringin){(?P<file>[^{}]*)}', re.M)
class tex_scanner(Scan.scanner):
	def __init__(self):
		Scan.scanner.__init__(self)

	def scan(self, task, node):
		env = task.env()

		nodes = []
		names = []
		if not node: return (nodes, names)

		fi = open(node.abspath(env), 'r')
		code = fi.read()
		fi.close()

		curdirnode = task.curdirnode
		abs = curdirnode.abspath()
		for match in re_tex.finditer(code):
			path = match.group('file')
			if path:
				for k in ['', '.tex', '.ltx']:
					# add another loop for the tex include paths?
					debug("trying %s%s" % (path, k), 'tex')
					try:
						os.stat(abs+os.sep+path+k)
					except OSError:
						continue
					found = path+k
					node = curdirnode.find_resource(found)
					if node:
						nodes.append(node)
				else:
					debug('could not find %s' % path, 'tex')
					names.append(path)

		debug("found the following : %s and names %s" % (nodes, names), 'tex')
		return (nodes, names)

g_tex_scanner = tex_scanner()

g_bibtex_re = re.compile('bibdata', re.M)
def tex_build(task, command='LATEX'):
	env = task.env()

	if env['PROMPT_LATEX']:
		Runner.set_exec('noredir')
		com = '%s %s' % (env[command], env.get_flat(command+'FLAGS'))
	else:
		com = '%s %s %s' % (env[command], env.get_flat(command+'FLAGS'), '-interaction=batchmode')

	node = task.m_inputs[0]
	reldir  = node.bld_dir(env)
	srcfile = node.srcpath(env)

	lst = []
	for c in Utils.split_path(reldir):
		if c: lst.append('..')
	sr = os.path.join(*(lst + [srcfile]))
	sr2 = os.path.join(*(lst + [node.m_parent.srcpath(env)]))

	aux_node = node.change_ext('.aux')
	idx_node = node.change_ext('.idx')

	hash     = ''
	old_hash = ''

	nm = aux_node.m_name
	docuname = nm[ : len(nm) - 4 ] # 4 is the size of ".aux"

	latex_compile_cmd = 'cd %s && TEXINPUTS=%s:$TEXINPUTS %s %s' % (reldir, sr2, com, sr)
	warning('first pass on %s' % command)
	ret = Runner.exec_command(latex_compile_cmd)
	if ret: return ret

	# look in the .aux file if there is a bibfile to process
	try:
		file = open(aux_node.abspath(env), 'r')
		ct = file.read()
		file.close()
	except (OSError, IOError):
		error('erreur bibtex scan')
	else:
		fo = g_bibtex_re.findall(ct)

		# yes, there is a .aux file to process
		if fo:
			bibtex_compile_cmd = 'cd %s && BIBINPUTS=%s:$BIBINPUTS %s %s' % (reldir, sr2, env['BIBTEX'], docuname)

			warning('calling bibtex')
			ret = Runner.exec_command(bibtex_compile_cmd)
			if ret:
				error('error when calling bibtex %s' % bibtex_compile_cmd)
				return ret

	# look on the filesystem if there is a .idx file to process
	try:
		idx_path = idx_node.abspath(env)
		os.stat(idx_path)
	except OSError:
		error('erreur file.idx scan')
	else:
		makeindex_compile_cmd = 'cd %s && %s %s' % (reldir, env['MAKEINDEX'], idx_path)
		warning('calling makeindex')
		ret = Runner.exec_command(makeindex_compile_cmd)
		if ret:
			error('error when calling makeindex %s' % makeindex_compile_cmd)
			return ret

	i = 0
	while i < 10:
		# prevent against infinite loops - one never knows
		i += 1

		# watch the contents of file.aux
		old_hash = hash
		try:
			hash = Params.h_file(aux_node.abspath(env))
		except KeyError:
			error('could not read aux.h -> %s' % aux_node.abspath(env))
			pass

		# debug
		#print "hash is, ", hash, " ", old_hash

		# stop if file.aux does not change anymore
		if hash and hash == old_hash: break

		# run the command
		warning('calling %s' % command)
		ret = Runner.exec_command(latex_compile_cmd)
		if ret:
			error('error when calling %s %s' % (command, latex_compile_cmd))
			return ret

	# 0 means no error
	return 0

latex_vardeps  = ['LATEX', 'LATEXFLAGS']
def latex_build(task):
	return tex_build(task, 'LATEX')

pdflatex_vardeps  = ['PDFLATEX', 'PDFLATEXFLAGS']
def pdflatex_build(task):
	return tex_build(task, 'PDFLATEX')

g_texobjs = ['latex','pdflatex']
class tex_taskgen(TaskGen.task_gen):
	s_default_ext = ['.tex', '.ltx']
	def __init__(self, *k, **kw):
		TaskGen.task_gen.__init__(self, *k)

		global g_texobjs
		self.m_type = kw['type']
		if not self.m_type in g_texobjs:
			fatal('type %s not supported for texobj' % type)
		self.outs = '' # example: "ps pdf"
		self.prompt = 1  # prompt for incomplete files (else the batchmode is used)
		self.deps = ''
	def apply(self):

		tree = Params.g_build
		outs = self.outs.split()
		self.env['PROMPT_LATEX'] = self.prompt

		deps_lst = []

		if self.deps:
			deps = self.to_list(self.deps)
			for filename in deps:
				n = self.path.find_resource(filename)
				if not n in deps_lst: deps_lst.append(n)

		for filename in self.source.split():
			base, ext = os.path.splitext(filename)
			if not ext in self.s_default_ext: continue

			node = self.path.find_resource(filename)
			if not node: fatal('cannot find %s' % filename)

			if self.m_type == 'latex':
				task = self.create_task('latex', self.env)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.dvi'))
			elif self.m_type == 'pdflatex':
				task = self.create_task('pdflatex', self.env)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.pdf'))
			else:
				fatal('no type or invalid type given in tex object (should be latex or pdflatex)')

			task.m_scanner = g_tex_scanner
			task.m_env = self.env
			task.curdirnode = self.path

			# add the manual dependencies
			if deps_lst:
				variant = node.variant(self.env)
				try:
					lst = tree.node_deps[variant][node.id]
					for n in deps_lst:
						if not n in lst:
							lst.append(n)
				except KeyError:
					tree.node_deps[variant][node.id] = deps_lst

			if self.m_type == 'latex':
				if 'ps' in outs:
					pstask = self.create_task('dvips', self.env)
					pstask.set_inputs(task.m_outputs)
					pstask.set_outputs(node.change_ext('.ps'))
				if 'pdf' in outs:
					pdftask = self.create_task('dvipdf', self.env)
					pdftask.set_inputs(task.m_outputs)
					pdftask.set_outputs(node.change_ext('.pdf'))
			elif self.m_type == 'pdflatex':
				if 'ps' in outs:
					pstask = self.create_task('pdf2ps', self.env)
					pstask.set_inputs(task.m_outputs)
					pstask.set_outputs(node.change_ext('.ps'))

def detect(conf):
	v = conf.env
	for p in 'tex latex pdflatex bibtex dvips dvipdf ps2pdf makeindex'.split():
		conf.find_program(p, var=p.upper())
		v[p.upper()+'FLAGS'] = ''
	v['DVIPSFLAGS'] = '-Ppdf'

b = Task.simple_task_type
b('tex', '${TEX} ${TEXFLAGS} ${SRC}', color='BLUE')
b('bibtex', '${BIBTEX} ${BIBTEXFLAGS} ${SRC}', color='BLUE')
b('dvips', '${DVIPS} ${DVIPSFLAGS} ${SRC} -o ${TGT}', color='BLUE', after="latex pdflatex tex bibtex")
b('dvipdf', '${DVIPDF} ${DVIPDFFLAGS} ${SRC} ${TGT}', color='BLUE', after="latex pdflatex tex bibtex")
b('pdf2ps', '${PDF2PS} ${PDF2PSFLAGS} ${SRC} ${TGT}', color='BLUE', after="dvipdf pdflatex")
b = Task.task_type_from_func
b('latex', latex_build, vars=latex_vardeps)
b('tex', pdflatex_build, vars=pdflatex_vardeps)

