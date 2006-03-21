#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner, Common

ocaml_vardeps = ['OCAMLCOMP', 'OCAMLFLAGS', 'OCAMLPATH']
act=Action.GenAction('ocaml', ocaml_vardeps)
def ocaml_build(task):
	com = task.m_env['OCAMLCOMP']
	paths = " ".join(task.m_env['OCAMLPATH'])
	#reldir  = task.m_inputs[0].cd_to()
	srcfile = task.m_inputs[0].bldpath()
	bldfile = task.m_outputs[0].bldpath()
	cmd = '%s %s -c -o %s %s' % (com, paths, bldfile, srcfile)
	print cmd
	return Runner.exec_command(cmd)
act.m_function_to_run = ocaml_build

native_lst=['native', 'all']
bytecode_lst=['bytecode', 'all']
class ocamlobj(Object.genobj):
	def __init__(self, type='all', library=0):
		Object.genobj.__init__(self, 'other', 'ocaml')

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
			self.native_env                = Params.g_default_env.copy()
			self.native_env['OCAMLCOMP']   = Params.g_default_env['OCAMLOPT']
			self.native_env['LINK']        = Params.g_default_env['OCAMLOPT']
		if type in bytecode_lst:
			self.is_bytecode               = 1
			self.bytecode_env              = Params.g_default_env.copy()
			self.bytecode_env['OCAMLCOMP'] = Params.g_default_env['OCAMLC']
			self.bytecode_env['LINK']      = Params.g_default_env['OCAMLC']

		if self.islibrary:
			self.bytecode_env['LINKFLAGS'] = '-a'
			self.native_env['LINKFLAGS']   = '-a'

	def apply_incpaths(self):
		inc_lst = self.includes.split()
		lst = self._incpaths_lst
		tree = Params.g_build.m_tree
		for dir in inc_lst:
			node = self.m_current_path.find_node( dir.split(os.sep) )
			if not node:
				error("node not found dammit")
				continue
			lst.append( node )

			node2 = tree.get_mirror_node(node)
			lst.append( node2 )
			if Params.g_mode == 'nocopy':
				lst.append( node )
				self._bld_incpaths_lst.append(node)
			self._bld_incpaths_lst.append(node2)
		# now the nodes are added to self._incpaths_lst

	def apply(self):
		self.apply_incpaths()

		for i in self._incpaths_lst:
                        self.bytecode_env.appendValue('OCAMLPATH', '-I %s' % i.bldpath())
			self.native_env.appendValue('OCAMLPATH', '-I %s' % i.bldpath())

		native_tasks   = []
		bytecode_tasks = []
		for filename in (' '+self.source).split():
			base, ext = os.path.splitext(filename)

			# TODO ocamllex and ocamlyacc
			if ext == '.mll':
				continue
			elif ext == '.mly':
				continue

			if self.is_native:
				task = self.create_task('ocaml', self.native_env, 2)
				task.m_inputs  = self.file_in(base+'.ml')
				task.m_outputs = self.file_in(base+'.cmx')
				native_tasks.append(task)
			if self.is_bytecode:
				task = self.create_task('ocaml', self.bytecode_env, 2)
				task.m_inputs  = self.file_in(base+'.ml')
				task.m_outputs = self.file_in(base+'.cmo')
				bytecode_tasks.append(task)

		if self.is_bytecode:
			linktask = self.create_task('link', self.bytecode_env, 6)
			objfiles = []
			for t in bytecode_tasks: objfiles.append(t.m_outputs[0])
			linktask.m_inputs  = objfiles
			linktask.m_outputs = self.file_in(self.get_target_name(bytecode=1))

		if self.is_native:
			linktask = self.create_task('link', self.native_env, 7)
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
	link_vardeps   = ['LINK', 'LINKFLAGS', 'LINK_ST']
	Action.GenAction('link', link_vardeps)

	Object.register('ocaml', ocamlobj)

def detect(conf):
	conf.env['OCAMLC']         = 'ocamlc'
	conf.env['OCAMLOPT']       = 'ocamlopt'
	conf.env['OCAMLLEX']       = 'ocamllex'
	conf.env['OCAMLYACC']      = 'ocamlyacc'
	conf.env['OCAMLFLAGS']     = ''
	conf.env['LINK']           = ''
	conf.env['LINKFLAGS']      = ''
	conf.env['LINK_ST']        = '%s -o %s'
	return 1

