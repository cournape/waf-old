#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params, Action, Object, Runner, Common

ocaml_vardeps = ['OCAMLCOMP', 'OCAMLFLAGS']
act=Action.GenAction('ocaml', ocaml_vardeps)
def ocaml_build(task):
	com = task.m_env['OCAMLCOMP']
	#reldir  = task.m_inputs[0].cd_to()
	srcfile = task.m_inputs[0].bldpath()
	bldfile = task.m_outputs[0].bldpath()
	cmd = '%s -c %s -o %s' % (com, srcfile, bldfile)
	#print cmd
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

	def apply(self):
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

