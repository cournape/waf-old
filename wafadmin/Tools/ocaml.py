#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"ocaml support"

import os, re
import Params, Action, Object, Scan, Utils, Task
from Params import error, fatal
from Object import taskgen, feature, before, after, extension

EXT_MLL = ['.mll']
EXT_MLY = ['.mly']
EXT_MLI = ['.mli']
EXT_MLC = ['.c']
EXT_ML  = ['.ml']

open_re = re.compile('open ([a-zA-Z]+);;', re.M)

def filter_comments(filename):
	f = open(filename, 'r')
	txt = f.read()
	f.close()
	buf = []

	i = 0
	max = len(txt)
	while i < max:
		c = txt[i]
		# skip a string
		if c == '"':
			i += 1
			c = ''
			while i < max:
				p = c
				c = txt[i]
				i += 1
				if i == max: return buf
				if c == '"':
					cnt = 0
					while i < cnt and i < max:
						#print "cntcnt = ", str(cnt), self.txt[self.i-2-cnt]
						if txt[i-2-cnt] == '\\': cnt+=1
						else: break
					#print "cnt is ", str(cnt)
					if (cnt%2)==0: break
		# skip a char - unfortunately caml is a bit special t'
		elif c == "'":
			i += 1
			if i == max: return buf
			c = txt[i]
			if c == '\\':
				i += 1
				if i == max: return buf
				c = txt[i]
				if c == 'x':
					i += 2 # skip two chars
			i += 1
			if i == max: return buf
			c = txt[i]
			#if c != '\'': print "uh-oh, invalid character"

		# skip a comment
		elif c == '(':
			if i == max: break
			c = txt[i+1]
			# eat (* *) comments
			if c == '*':
				i += 1
				nesting = 1
				prev = 0
				while i < max:
					c = txt[i]
					if c == '*':
						prev = 1
					elif c == ')' and prev:
						if prev:
							nesting -= 1
							if nesting == 0: break
					elif c == '(':
						prev = 0
						if i == max: return buf
						i += 1
						c = txt[i]
						if c == '*': nesting += 1
					else:
						prev = 0
					i += 1
		# a valid char, add it to the buffer
		else:
			buf.append(c)
		i += 1
	return buf

class ocaml_link(Task.Task):
	"""link tasks in ocaml are special, the command line calculation must be postponed
	until having the dependencies on the compilation tasks, this means that we must
	produce the .ml files (lex, ..) to decide the order on which to link the files"""
	def __init__(self, action_name, env, normal=1):
		Task.Task.__init__(self, action_name, env, normal)
	def may_start(self):
		if not getattr(self, 'order', ''):

			# now reorder the m_inputs given the task dependencies
			if getattr(self, 'bytecode', 0): alltasks = self.obj.bytecode_tasks
			else: alltasks = self.obj.native_tasks

			# this part is difficult, we do not have a total order on the tasks
			# if the dependencies are wrong, this may not stop
			seen = []
			pendant = []+alltasks
			while pendant:
				task = pendant.pop(0)
				if task in seen: continue
				for x in task.get_run_after():
					if not x in seen:
						pendant.append(task)
						break
				else:
					seen.append(task)
			self.m_inputs = [x.m_outputs[0] for x in seen]
			self.order=1
		return Task.Task.may_start(self)

class ocaml_scanner(Scan.scanner):
	def __init__(self):
		Scan.scanner.__init__(self)
	def may_start(self, task):
		if getattr(task, 'flag_deps', ''): return 1

		# the evil part is that we can only compute the dependencies after the
		# source files can be read (this means actually producing the source files)
		if getattr(task, 'bytecode', ''): alltasks = task.obj.bytecode_tasks
		else: alltasks = task.obj.native_tasks

		task.signature() # ensure that files are scanned - unfortunately
		tree = Params.g_build
		env = task.env()
		for node in task.m_inputs:
			lst = tree.m_depends_on[node.variant(env)][node]
			for depnode in lst:
				for t in alltasks:
					if t == task: continue
					if depnode in t.m_inputs:
						task.set_run_after(t)
		task.obj.flag_deps = 'ok'

		# TODO necessary to get the signature right - for now
		delattr(task, 'sign_all')
		task.signature()

		return 1

	def scan(self, task, node):
		#print "scan is called"
		code = "".join(filter_comments(node.abspath(task.env())))

		global open_re
		names=[]
		import_iterator = open_re.finditer(code)
		if import_iterator:
			for import_match in import_iterator:
				names.append(import_match.group(1))
		found_lst = []
		raw_lst = []
		for name in names:
			nd = None
			for x in task.incpaths:
				nd = x.find_source(name.lower()+'.ml')
				if nd:
					found_lst.append(nd)
					break
			else:
				raw_lst.append(name)

		return (found_lst, raw_lst)

g_caml_scanner = ocaml_scanner()

def get_target_name(self, bytecode):
	if bytecode:
		if self.islibrary:
			return self.target+'.cma'
		else:
			return self.target+'.run'
	else:
		if self.m_type == 'c_object': return self.target+'.o'

		if self.islibrary:
			return self.target+'.cmxa'
		else:
			return self.target

native_lst=['native', 'all', 'c_object']
bytecode_lst=['bytecode', 'all']
class ocamlobj(Object.task_gen):
	s_default_ext = ['.mli', '.mll', '.mly', '.ml']
	def __init__(self, type='all', library=0):
		Object.task_gen.__init__(self)

		self.m_type       = type
		self.m_source     = ''
		self.m_target     = ''
		self.islibrary    = library
		self._incpaths_lst = []
		self._bld_incpaths_lst = []
		self._mlltasks    = []
		self._mlytasks    = []

		self.mlitasks    = []
		self.native_tasks   = []
		self.bytecode_tasks = []
		self.linktasks      = []

		self.bytecode_env = None
		self.native_env   = None


		self.compiled_tasks = []
		self.includes     = ''
		self.uselib       = ''

		self.out_nodes    = []

		self.are_deps_set = 0

		if not self.env: self.env = Params.g_build.env()

		if not type in ['bytecode','native','all','c_object']:
			print 'type for camlobj is undefined '+type
			type='all'

		if type in native_lst:
			self.native_env                = self.env.copy()
			self.native_env['OCAMLCOMP']   = self.native_env['OCAMLOPT']
			self.native_env['OCALINK']     = self.native_env['OCAMLOPT']
		if type in bytecode_lst:
			self.bytecode_env              = self.env.copy()
			self.bytecode_env['OCAMLCOMP'] = self.bytecode_env['OCAMLC']
			self.bytecode_env['OCALINK']   = self.bytecode_env['OCAMLC']

		if self.islibrary:
			self.bytecode_env['OCALINKFLAGS'] = '-a'
			self.native_env['OCALINKFLAGS']   = '-a'

		if self.m_type == 'c_object':
			self.native_env['OCALINK'] = self.native_env['OCALINK']+' -output-obj'

		self.features.append('ocaml')

Object.add_feature('ocaml', ['apply_core'])

@taskgen
@feature('ocaml')
@before('apply_vars_ml')
def apply_incpaths_ml(self):
	inc_lst = self.includes.split()
	lst = self._incpaths_lst
	tree = Params.g_build
	for dir in inc_lst:
		node = self.path.find_source(dir)
		if not node:
			error("node not found dammit")
			continue
		Params.g_build.rescan(node)
		if not node in lst: lst.append( node )
		self._bld_incpaths_lst.append(node)
	# now the nodes are added to self._incpaths_lst

@taskgen
@feature('ocaml')
@before('apply_core')
def apply_vars_ml(self):
	for i in self._incpaths_lst:
		if self.bytecode_env:
			self.bytecode_env.append_value('OCAMLPATH', '-I %s' % i.srcpath(self.env))
			self.bytecode_env.append_value('OCAMLPATH', '-I %s' % i.bldpath(self.env))

		if self.native_env:
			self.native_env.append_value('OCAMLPATH', '-I %s' % i.bldpath(self.env))
			self.native_env.append_value('OCAMLPATH', '-I %s' % i.srcpath(self.env))

	varnames = ['INCLUDES', 'OCAMLFLAGS', 'OCALINKFLAGS', 'OCALINKFLAGS_OPT']
	for name in self.uselib.split():
		for vname in varnames:
			cnt = self.env[vname+'_'+name]
			if cnt:
				if self.bytecode_env: self.bytecode_env.append_value(vname, cnt)
				if self.native_env: self.native_env.append_value(vname, cnt)

@taskgen
@feature('ocaml')
@after('apply_core')
def apply_link_ml(self):

	if self.bytecode_env:
		linktask = ocaml_link('ocalink', self.bytecode_env)
		linktask.bytecode = 1
		linktask.set_outputs(self.path.find_build(get_target_name(self, bytecode=1)))
		linktask.obj = self
		self.linktasks.append(linktask)
	if self.native_env:
		linktask = ocaml_link('ocalinkopt', self.native_env)
		linktask.set_outputs(self.path.find_build(get_target_name(self, bytecode=0)))
		linktask.obj = self
		self.linktasks.append(linktask)

		self.out_nodes += linktask.m_outputs

		# we produce a .o file to be used by gcc
		if self.m_type == 'c_object': self.compiled_tasks.append(linktask)

@extension(EXT_MLL)
def mll_hook(self, node):
	mll_task = self.create_task('ocamllex', self.native_env)
	mll_task.set_inputs(node)
	mll_task.set_outputs(node.change_ext('.ml'))
	self.mlltasks.append(mll_task)

	self.allnodes.append(mll_task.m_outputs[0])

@extension(EXT_MLY)
def mly_hook(self, node):
	mly_task = self.create_task('ocamlyacc', self.native_env)
	mly_task.set_inputs(node)
	mly_task.set_outputs([node.change_ext('.ml'), node.change_ext('.mli')])
	self._mlytasks.append(mly_task)
	self.allnodes.append(mly_task.m_outputs[0])

	task = self.create_task('ocamlcmi', self.native_env)
	task.set_inputs(mly_task.m_outputs[1])
	task.set_outputs(mly_task.m_outputs[1].change_ext('.cmi'))

@extension(EXT_MLI)
def mli_hook(self, node):
	task = self.create_task('ocamlcmi', self.native_env)
	task.set_inputs(node)
	task.set_outputs(node.change_ext('.cmi'))
	self.mlitasks.append(task)

@extension(EXT_MLC)
def mlc_hook(self, node):
	task = self.create_task('ocamlcc', self.native_env)
	task.set_inputs(node)
	task.set_outputs(node.change_ext('.o'))

	self.out_nodes += task.m_outputs

@extension(EXT_ML)
def ml_hook(self, node):
	if self.native_env:
		task = self.create_task('ocaml', self.native_env)
		task.set_inputs(node)
		task.set_outputs(node.change_ext('.cmx'))
		task.m_scanner = g_caml_scanner
		task.obj = self
		task.incpaths = self._bld_incpaths_lst
		self.native_tasks.append(task)
	if self.bytecode_env:
		task = self.create_task('ocaml', self.bytecode_env)
		task.set_inputs(node)
		task.m_scanner = g_caml_scanner
		task.obj = self
		task.bytecode = 1
		task.incpaths = self._bld_incpaths_lst
		task.set_outputs(node.change_ext('.cmo'))
		self.bytecode_tasks.append(task)

Object.register('ocaml', ocamlobj)
Action.simple_action('ocaml', '${OCAMLCOMP} ${OCAMLPATH} ${OCAMLFLAGS} ${INCLUDES} -c -o ${TGT} ${SRC}', color='GREEN', prio=60)
Action.simple_action('ocalink', '${OCALINK} -o ${TGT} ${INCLUDES} ${OCALINKFLAGS} ${SRC}', color='YELLOW', prio=99)
Action.simple_action('ocalinkopt', '${OCALINK} -o ${TGT} ${INCLUDES} ${OCALINKFLAGS_OPT} ${SRC}', color='YELLOW', prio=99)
Action.simple_action('ocamlcmi', '${OCAMLC} ${OCAMLPATH} ${INCLUDES} -o ${TGT} -c ${SRC}', color='BLUE', prio=40)
Action.simple_action('ocamlcc', 'cd ${TGT[0].bld_dir(env)} && ${OCAMLOPT} ${OCAMLFLAGS} ${OCAMLPATH} ${INCLUDES} -c ${SRC[0].abspath(env)}', color='GREEN', prio=60)
Action.simple_action('ocamllex', '${OCAMLLEX} ${SRC} -o ${TGT}', color='BLUE', prio=20)
Action.simple_action('ocamlyacc', '${OCAMLYACC} -b ${TGT[0].bldbase(env)} ${SRC}', color='BLUE', prio=20)

def detect(conf):
	opt = conf.find_program('ocamlopt', var='OCAMLOPT')
	occ = conf.find_program('ocamlc', var='OCAMLC')
	if (not opt) or (not occ):
		fatal('The objective caml compiler was not found:\ninstall it or make it available in your PATH')

	conf.env['OCAMLC']       = occ
	conf.env['OCAMLOPT']     = opt
	conf.env['OCAMLLEX']     = conf.find_program('ocamllex', var='OCAMLLEX')
	conf.env['OCAMLYACC']    = conf.find_program('ocamlyacc', var='OCAMLYACC')
	conf.env['OCAMLFLAGS']   = ''
	conf.env['OCALINK']      = ''
	conf.env['OCAMLLIB']     = os.popen(conf.env['OCAMLC']+' -where').read().strip()+os.sep
	conf.env['LIBPATH_OCAML'] = os.popen(conf.env['OCAMLC']+' -where').read().strip()+os.sep
	conf.env['CPPPATH_OCAML'] = os.popen(conf.env['OCAMLC']+' -where').read().strip()+os.sep
	conf.env['LIB_OCAML'] = 'camlrun'
	conf.env['OCALINKFLAGS'] = ''

