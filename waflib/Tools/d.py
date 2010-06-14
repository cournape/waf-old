#!/usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2007-2010 (ita)

import os, sys, re
from collections import deque
import waflib.Tools.ccroot # <- leave this
from waflib import TaskGen, Utils, Task, Logs, Errors
from waflib.Logs import debug, error
from waflib.TaskGen import taskgen_method, feature, after, before, extension
from waflib.Configure import conf

import waflib.Tools.d_scan

DLIB = """
version(D_Version2) {
	import std.stdio;
	int main() {
		writefln("phobos2");
		return 0;
	}
} else {
	version(Tango) {
		import tango.stdc.stdio;
		int main() {
			printf("tango");
			return 0;
		}
	} else {
		import std.stdio;
		int main() {
			writefln("phobos1");
			return 0;
		}
	}
}
"""

def get_target_name(self):
	"for d programs and libs"
	v = self.env
	tp = 'program'
	for x in self.features:
		if x in ['dshlib', 'dstlib']:
			tp = x.lstrip('d')
	return v['D_%s_PATTERN' % tp] % self.target

d_params = {
'dflags': '',
'libs':'',
'libpaths':'',
'generate_headers':False,
}

@feature('d')
@before('apply_lib_vars')
def init_d(self):
	for x in d_params:
		setattr(self, x, getattr(self, x, d_params[x]))

@feature('d')
@before('apply_d_libs')
def init_d(self):
	Utils.def_attrs(self,
		dflags='',
		libs='',
		libpaths='',
		uselib='',
		uselib_local='',
		generate_headers=False, # set to true if you want .di files as well as .o
		compiled_tasks=[],
		add_objects=[],
		link_task=None)

@feature('d')
@after('apply_d_link', 'init_d')
@before('apply_vnum', 'apply_incpaths')
def apply_d_libs(self):
	"""after apply_link because of 'link_task'"""
	env = self.env

	# 1. the case of the libs defined in the project (visit ancestors first)
	# the ancestors external libraries (uselib) will be prepended
	self.uselib = self.to_list(self.uselib)
	names = self.to_list(self.uselib_local)
	get = self.bld.get_tgen_by_name

	seen = set([])
	tmp = deque(names) # consume a copy of the list of names
	while tmp:
		lib_name = tmp.popleft()
		# visit dependencies only once
		if lib_name in seen:
			continue

		y = get(lib_name)
		y.post()
		seen.add(lib_name)

		# object has ancestors to process (shared libraries): add them to the end of the list
		if getattr(y, 'uselib_local', None):
			lst = y.to_list(y.uselib_local)
			if 'dshlib' in y.features or 'cprogram' in y.features:
				lst = [x for x in lst if not 'cstlib' in get(x).features]
			tmp.extend(lst)

		# link task and flags
		if getattr(y, 'link_task', None):

			link_name = y.target[y.target.rfind(os.sep) + 1:]
			if 'dstlib' in y.features or 'dshlib' in y.features:
				env.append_unique('DLINKFLAGS', [env.DLIB_ST % link_name])
				env.append_unique('DLINKFLAGS', [env.DLIBPATH_ST % y.link_task.outputs[0].parent.bldpath()])

			# the order
			self.link_task.set_run_after(y.link_task)

			# for the recompilation
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.outputs

		# add ancestors uselib too - but only propagate those that have no staticlib
		for v in self.to_list(y.uselib):
			if not v in self.uselib:
				self.uselib.insert(0, v)

		# if the library task generator provides 'export_incdirs', add to the include path
		# the export_incdirs must be a list of paths relative to the other library
		if getattr(y, 'export_incdirs', None):
			for x in self.to_list(y.export_incdirs):
				node = y.path.find_dir(x)
				if not node:
					raise Errors.WafError('object %r: invalid folder %r in export_incdirs' % (y.target, x))
				self.env.append_unique('INC_PATHS', [node])

@feature('dprogram', 'dshlib', 'dstlib')
@after('process_source')
def apply_d_link(self):
	link = getattr(self, 'link', None)
	if not link:
		if 'dstlib' in self.features: link = 'static_link'
		else: link = 'd_link'

	outputs = [t.outputs[0] for t in self.compiled_tasks]
	self.link_task = self.create_task(link, outputs, self.path.find_or_declare(get_target_name(self)))

@feature('d')
@after('process_source')
def apply_d_vars(self):
	env = self.env
	lib_st     = env['DLIB_ST']
	libpath_st = env['DLIBPATH_ST']

	libpaths = []
	libs = []
	uselib = self.to_list(self.uselib)

	for i in uselib:
		if env['DFLAGS_' + i]:
			env.append_unique('DFLAGS', env['DFLAGS_' + i])

	for x in self.features:
		env.append_unique('DFLAGS', env[x + '_DFLAGS'])

	# add library paths
	for i in uselib:
		for entry in self.to_list(env['LIBPATH_' + i]):
			if not entry in libpaths:
				libpaths.append(entry)
	libpaths = self.to_list(self.libpaths) + libpaths

	# now process the library paths
	# apply same path manipulation as used with import paths
	for path in libpaths:
		env.append_unique('DLINKFLAGS', [libpath_st % path])

	# add libraries
	for i in uselib:
		for entry in self.to_list(env['LIB_' + i]):
			if not entry in libs:
				libs.append(entry)
	libs.extend(self.to_list(self.libs))

	# process user flags
	env.append_unique('DFLAGS', self.to_list(self.dflags))

	# now process the libraries
	env.append_unique('DLINKFLAGS', [lib_st % lib for lib in libs])

	# add linker flags
	for i in uselib:
		env.append_unique('DLINKFLAGS', env['DLINKFLAGS_' + i])

@feature('dshlib')
@after('apply_d_vars')
def add_shlib_d_flags(self):
	self.env.append_unique('DLINKFLAGS', self.env['D_shlib_LINKFLAGS'])

@extension('.d', '.di', '.D')
def d_hook(self, node):
	if self.generate_headers:
		task = self.create_compiled_task('d_with_header', node)
		header_node = node.change_ext(self.env['DHEADER_ext'])
		task.outputs.append(header_node)
	else:
		task = self.create_compiled_task('d', node)
	return task

class d(Task.Task):
	color   = 'GREEN'
	run_str = '${D} ${DFLAGS} ${_INCFLAGS} ${D_SRC_F}${SRC} ${D_TGT_F}${TGT}'
	scan    = waflib.Tools.d_scan.scan

	def exec_command(self, *k, **kw):
		"""dmd wants -of stuck to the file name"""
		if isinstance(k[0], list):
			lst = k[0]
			for i in range(len(lst)):
				if lst[i] == '-of':
					del lst[i]
					lst[i] = '-of' + lst[i]
					break
		return super(d, self).exec_command(*k, **kw)

class d_with_header(d):
	run_str = '${D} ${DFLAGS} ${_INCFLAGS} ${D_HDR_F}${TGT[1].bldpath()} ${D_SRC_F}${SRC} ${D_TGT_F}${TGT[0].bldpath()}'

class d_link(d):
	color   = 'YELLOW'
	run_str = '${D_LINKER} ${DLNK_SRC_F}${SRC} ${DLNK_TGT_F}${TGT} ${DLINKFLAGS}'

class d_header(Task.Task):
	color   = 'BLUE'
	run_str = '${D} ${D_HEADER} ${SRC}'

@taskgen_method
def generate_header(self, filename, install_path=None):
	"""see feature request #104 - TODO the install_path is not used"""
	try:
		self.header_lst.append([filename, install_path])
	except AttributeError:
		self.header_lst = [[filename, install_path]]

@feature('d')
def process_header(self):
	for i in getattr(self, 'header_lst', []):
		node = self.path.find_resource(i[0])
		if not node:
			raise Errors.WafError('file %r not found on d obj' % i[0])
		self.create_task('d_header', node, node.change_ext('.di'))

@conf
def d_platform_flags(self):
	v = self.env
	if Utils.unversioned_sys_platform_to_binary_format(self.env.DEST_OS or Utils.unversioned_sys_platform()) == 'pe':
		v['D_program_PATTERN']   = '%s.exe'
		v['D_shlib_PATTERN']     = 'lib%s.dll'
		v['D_stlib_PATTERN'] = 'lib%s.a'
	else:
		v['D_program_PATTERN']   = '%s'
		v['D_shlib_PATTERN']     = 'lib%s.so'
		v['D_stlib_PATTERN'] = 'lib%s.a'

@conf
def check_dlibrary(self):
	ret = self.check_cc(features='d dprogram', fragment=DLIB, compile_filename='test.d', execute=True)
	self.env.DLIBRARY = ret.strip()

