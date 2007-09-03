#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)

import os, sys
import optparse
import Object, Utils, Action, Params, checks, Configure


class dobj(Object.genobj):

	s_default_ext = ['.d', '.di', '.D']
	def __init__(self, type='program'):
		Object.genobj.__init__(self, type)

		self.dflags = ''
		self.importpaths = ''
		self.libs = ''
		self.libpaths = ''
		self.uselib = ''
		self.uselib_local = ''

	def apply(self):

		#initialization
		if self.m_type == 'objects':
			type = 'program'
		else:
			type = self.m_type

		env = self.env
		dpath_st         = env['DPATH_ST']
		lib_st           = env['DLIB_ST']
		libpath_st       = env['DLIBPATH_ST']

		importpaths = []
		libpaths = []
		libs = []

		if type == 'staticlib':
			linktask = self.create_task('ar_link_static', self.env, 101)
		else:
			linktask = self.create_task('d_link', self.env, 101)

		# go through the local uselibs
		for local_uselib in self.to_list(self.uselib_local):
			y = Object.name_to_obj(local_uselib)
			if not y: continue

			if not y.m_posted: y.post()

			if y.m_type == 'shlib':
				libs = libs + [y.target]
			elif y.m_type == 'staticlib':
				libs = libs + [y.target]
			elif y.m_type == 'objects':
				pass
			else:
				error('%s has unknown object type %s, in apply_lib_vars, uselib_local.'
				      % (y.name, y.m_type))

			if y.m_linktask is not None:
				linktask.set_run_after(y.m_linktask)

			libpaths = libpaths + [y.path.bldpath(self.env)]


		# add compiler flags
		for i in self.to_list(self.uselib):
			if self.env['DFLAGS_' + i]:
				self.env.append_unique('DFLAGS', self.env['DFLAGS_' + i])
		if self.dflags:
			self.env.append_unique('DFLAGS', self.dflags)

		d_shlib_dflags = self.env['D_' + type + '_DFLAGS']
		if d_shlib_dflags:
			for dflag in d_shlib_dflags:
				self.env.append_unique('DFLAGS', dflag)


		# add import paths
		for i in self.to_list(self.uselib):
			if self.env['DPATH_' + i]:
				importpaths += self.to_list(self.env['DPATH_' + i])
		importpaths = self.to_list(self.importpaths) + importpaths

		# now process the import paths
		for path in importpaths:
			if Utils.is_absolute_path(path):
				imppath = path
			else:
				imppath = self.path.find_source_lst(Utils.split_path(path)).srcpath(self.env)
			self.env.append_unique('_DIMPORTFLAGS', dpath_st % imppath)


		# add library paths
		for i in self.to_list(self.uselib):
			if self.env['LIBPATH_' + i]:
				libpaths += self.to_list(self.env['LIBPATH_' + i])
		libpaths = self.to_list(self.libpaths) + libpaths

		# now process the library paths
		for path in libpaths:
			self.env.append_unique('_DLIBDIRFLAGS', libpath_st % path)


		# add libraries
		for i in self.to_list(self.uselib):
			if self.env['LIB_' + i]:
				libs += self.to_list(self.env['LIB_' + i])
		libs = libs + self.to_list(self.libs)

		# now process the libraries
		for lib in libs:
			self.env.append_unique('_DLIBFLAGS', lib_st % lib)


		# add linker flags
		for i in self.to_list(self.uselib):
			dlinkflags = self.env['DLINKFLAGS_' + i]
			if dlinkflags:
				for linkflag in dlinkflags:
					self.env.append_unique('DLINKFLAGS', linkflag)

		d_shlib_linkflags = self.env['D_' + type + '_LINKFLAGS']
		if d_shlib_linkflags:
			for linkflag in d_shlib_linkflags:
				self.env.append_unique('DLINKFLAGS', linkflag)


		# create compile tasks

		compiletasks = []

		obj_ext = self.env['D_' + type + '_obj_ext'][0]

		find_source_lst = self.path.find_source_lst

		for filename in self.to_list(self.source):
			node = find_source_lst(Utils.split_path(filename))
			base, ext = os.path.splitext(filename)
			#mod_names = get_module_names_from_file(find_source_lst(Utils.split_path(filename)).srcpath(self.env))
			#print mod_names

			if not ext in self.s_default_ext:
				fatal("unknown file " + filename)

			task = self.create_task('d', self.env, 10)
			task.set_inputs(node)
			task.set_outputs(node.change_ext(obj_ext))

			compiletasks.append(task)

		# and after the objects, the remaining is the link step
		# link in a lower priority (101) so it runs alone (default is 10)
		global g_prio_link

		outputs = []
		for t in compiletasks: outputs.append(t.m_outputs[0])
		linktask.set_inputs(outputs)
		linktask.set_outputs(self.path.find_build(self.get_target_name()))

		self.m_linktask = linktask

	def get_target_name(self):
		v = self.env

		prefix = v['D_' + self.m_type + '_PREFIX']
		suffix = v['D_' + self.m_type + '_SUFFIX']

		if not prefix: prefix=''
		if not suffix: suffix=''
		return ''.join([prefix, self.target, suffix])

	def install(self):
		pass

def setup(env):
	d_str = '${D_COMPILER} ${DFLAGS} ${_DIMPORTFLAGS} ${D_SRC_F}${SRC} ${D_TGT_F}${TGT}'
	link_str = '${D_LINKER} ${DLNK_SRC_F}${SRC} ${DLNK_TGT_F}${TGT} ${DLINKFLAGS} ${_DLIBDIRFLAGS} ${_DLIBFLAGS}'

	Action.simple_action('d', d_str, 'GREEN')
	Action.simple_action('d_link', link_str, color='YELLOW')

	Object.register('d', dobj)

def detect(conf):
	return 1


# def get_module_names_from_file(fname):
# 	import re
# 	f = open(fname)
# 	impnames = []
# 	try:
# 		code = f.read()


# 		mod_name = re.search("module\s+([^;]+)", code)
# 		if mod_name:
# 			mod_name = mod_name.group(1)
# 		else:
# 			mod_name = ''
# 		


# 		results = re.findall("import\s+[^;]+", code)

# 		for result in results:
# 			impname = result
# 			r = re.match("(import\s+)([^:]+)\s+:\s+(.*)", impname)
# 			if r:
# 				impname = r.group(2)

# 			r = re.match("([^=]+)\s+=\s+(.+)", impname)
# 			if r:
# 				impname = r.group(2)

# 			r = re.match("(import\s+)(.*)", impname)
# 			if r:
# 				impname = r.group(2)

# 			impnames = impnames + [impname]

# 	except:
# 		pass

# 	f.close()

# 	return [mod_name, impnames]
