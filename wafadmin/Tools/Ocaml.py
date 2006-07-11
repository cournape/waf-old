#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner, Common
from Params import debug, error, trace, fatal


native_lst=['native', 'all']
bytecode_lst=['bytecode', 'all']
class ocamlobj(Object.genobj):
	def __init__(self, type='all', library=0):
		Object.genobj.__init__(self, 'ocaml')

		self.m_type   = type
		self.m_source = ''
		self.m_target = ''
		self.islibrary = library
		self._incpaths_lst = []
		self._bld_incpaths_lst = []

		if not type in ['bytecode','native','all']:
			print 'type for camlobj is undefined '+type
			type='all'

		if type in native_lst:
			self.is_native                 = 1
			self.native_env                = Params.g_build.m_allenvs['default'].copy()
			self.native_env['OCAMLCOMP']   = self.native_env['OCAMLOPT']
			self.native_env['OCALINK']     = self.native_env['OCAMLOPT']
		if type in bytecode_lst:
			self.is_bytecode               = 1
			self.bytecode_env              = Params.g_build.m_allenvs['default'].copy()
			self.bytecode_env['OCAMLCOMP'] = self.bytecode_env['OCAMLC']
			self.bytecode_env['OCALINK']   = self.bytecode_env['OCAMLC']

		if self.islibrary:
			self.bytecode_env['OCALINKFLAGS'] = '-a'
			self.native_env['OCALINKFLAGS']   = '-a'

	def apply_incpaths(self):
		inc_lst = self.includes.split()
		lst = self._incpaths_lst
		tree = Params.g_build
		for dir in inc_lst:
			node = self.m_current_path.find_node( dir.split(os.sep) )
			if not node:
				error("node not found dammit")
				continue

			lst.append( node )
			self._bld_incpaths_lst.append(node)
			#self._bld_incpaths_lst.append(node2)
		# now the nodes are added to self._incpaths_lst

	def apply(self):
		self.apply_incpaths()

		for i in self._incpaths_lst:
     			self.bytecode_env.appendValue('OCAMLPATH', '-I %s' % i.srcpath(self.env))
			self.native_env.appendValue('OCAMLPATH', '-I %s' % i.srcpath(self.env))

			self.bytecode_env.appendValue('OCAMLPATH', '-I %s' % i.bldpath(self.env))
			self.native_env.appendValue('OCAMLPATH', '-I %s' % i.bldpath(self.env))

		native_tasks   = []
		bytecode_tasks = []
		for filename in (' '+self.source).split():
			base, ext = os.path.splitext(filename)

			# TODO ocamllex and ocamlyacc
			if ext == '.mll':
				continue
			elif ext == '.mly':
				continue

			node = self.file_in(base+'.ml')[0]

			if self.is_native:
				task = self.create_task('ocaml', self.native_env, 2)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.cmx'))
				native_tasks.append(task)
			if self.is_bytecode:
				task = self.create_task('ocaml', self.bytecode_env, 2)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.cmo'))
				bytecode_tasks.append(task)

		if self.is_bytecode:
			linktask = self.create_task('ocalink', self.bytecode_env, 101)
			objfiles = []
			for t in bytecode_tasks: objfiles.append(t.m_outputs[0])
			linktask.m_inputs  = objfiles
			linktask.m_outputs = self.file_in(self.get_target_name(bytecode=1))

		if self.is_native:
			linktask = self.create_task('ocalink', self.native_env, 101)
			objfiles = []
			for t in native_tasks: objfiles.append(t.m_outputs[0])
			linktask.m_inputs  = objfiles
			linktask.m_outputs = self.file_in(self.get_target_name(bytecode=0))

	def get_target_name(self, bytecode):
		if bytecode:
			if self.islibrary:
				return self.target+'.cma'
			else:
				return self.target+'.run'
		else:
			if self.islibrary:
				return self.target+'.cmxa'
			else:
				return self.target

def setup(env):
	Object.register('ocaml', ocamlobj)
	Action.simple_action('ocaml', '${OCAMLCOMP} ${OCAMLPATH} -c -o ${TGT} ${SRC}', color='GREEN')
	Action.simple_action('ocalink', '${OCALINK} ${OCALINKFLAGS} ${SRC} -o ${TGT}', color='YELLOW')

def detect(conf):

	opt = conf.checkProgram('ocamlopt', var='OCAMLOPT')
	occ = conf.checkProgram('ocamlc', var='OCAMLC')
	if (not opt) or (not occ):
		fatal('The objective caml compiler was not found:\n' \
			'install it or make it availaible in your PATH')

	conf.env['OCAMLC']       = occ
	conf.env['OCAMLOPT']     = opt
	conf.env['OCAMLLEX']     = 'ocamllex'
	conf.env['OCAMLYACC']    = 'ocamlyacc'
	conf.env['OCAMLFLAGS']   = ''
	conf.env['OCALINK']      = ''
	conf.env['OCALINKFLAGS'] = ''
	return 1

