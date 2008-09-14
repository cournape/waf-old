#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
c/c++ configuration routines

The code is being written, so do not complain about trunk being broken :-)
"""

import os, types, imp, cPickle, sys, shlex, warnings, shutil
from Utils import md5
import Build, Utils, Configure, Task, Options
from Logs import warn, debug
from Constants import *
from Configure import conf, conftest

stdincpath = ['/usr/include/', '/usr/local/include/']
"""standard include paths"""

stdlibpath = ['/usr/lib/', '/usr/local/lib/', '/lib']
"""standard library search paths"""

# the idea is the following: now that we are certain
# that all the code here is only for c or c++, it is
# easy to put all the logic in one function
#
# this should prevent code duplication (ita)

simple_c_code = 'int main() {return 0;}\n'
code_with_headers = ''

# env: an optional environment (modified -> provide a copy)
# compiler: cc or cxx - it tries to guess what is best
# type: program, shlib, staticlib, objects
# code: a c code to execute
# uselib_store: where to add the variables
# uselib: parameters to use for building
# define: define to set, like FOO in #define FOO, if not set, add /* #undef FOO */
# execute: True or False

# TODO
# fragment
# function_name
# header_name

@conf
def validate_c(*k, **kw):
	"""validate the parameters for the test method"""

	if not 'env' in kw:
		kw['env'] = self.env.copy()

	env = kw['env']
	if not 'compiler' in kw:
		kw['compiler'] = 'cc'
		if env['CXX_NAME'] and Task.TaskBase.classes.get('cxx', None):
			kw['compiler'] = 'cxx'

	if not 'type' in kw:
		kw['type'] = 'program'

	if kw['type'] != 'program' and kw.get('execute', 0):
		raise ValueError, 'can only execute programs'

	if not 'code' in kw:
		code = simple_c_code

	if not 'execute' in kw:
		kw['execute'] = True

@conf
def post_check(self, *k, **kw):
	"set the variables after a test was run successfully"



@conf
def check(self, *k, **kw):
	# so this will be the generic function
	# it will be safer to use cxx_check or cc_check
	self.validate_c(*k, **kw)

	if kw['compiler'] == 'cxx':
		tp = 'cxx'
		test_f_name = 'test.cpp'
	else:
		tp = 'cc'
		test_f_name = 'test.c'

	# create a small folder for testing
	dir = os.path.join(self.blddir, '.wscript-trybuild')

	# if the folder already exists, remove it
	shutil.rmtree(dir)
	if not os.path.exists(dir):
		os.makedirs(dir)

	bdir = os.path.join(dir, 'testbuild')

	if not os.path.exists(bdir):
		os.makedirs(bdir)

	if obj.env: env = obj.env
	else: env = self.env.copy()

	dest = open(os.path.join(dir, test_f_name), 'w')
	dest.write(obj.code)
	dest.close()

	back = os.path.abspath('.')

	bld = Build.BuildContext()
	bld.log = self.log
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default'] = env
	bld._variants = bld.all_envs.keys()
	bld.load_dirs(dir, bdir)

	os.chdir(dir)

	bld.rescan(bld.srcnode)

	o = bld.new_task_gen(tp, obj.build_type)
	o.source   = test_f_name
	o.target   = 'testprog'
	o.uselib   = obj.uselib
	o.includes = obj.includes

	self.log.write("==>\n%s\n<==\n" % obj.code)


	# compile the program
	try:
		ret = bld.compile()
	except Build.BuildError:
		ret = 1

	# keep the name of the program to execute
	if obj.execute:
		lastprog = o.link_task.outputs[0].abspath(o.env)

	#if runopts is not None:
	#	ret = os.popen(obj.link_task.outputs[0].abspath(obj.env)).read().strip()

	os.chdir(back)

	# if we need to run the program, try to get its result
	if obj.execute:
		if ret: return not ret
		data = Utils.cmd_output('"%s"' % lastprog).strip()
		ret = {'result': data}

	if obj.execute:
		return ret

	self.post_check()

	# error code
	return not ret

@conf
def cxx_check(self, *k, **kw):
	kw['compiler'] = 'cxx'
	self.check(*k, **kw)

@conf
def cc_check(self, *k, **kw):
	kw['compiler'] = 'cc'
	self.check(*k, **kw)

@conf
def define(self, define, value, quote=1):
	"""store a single define and its state into an internal list for later
	   writing to a config header file.  Value can only be
	   a string or int; other types not supported.  String
	   values will appear properly quoted in the generated
	   header file."""
	assert define and isinstance(define, str)

	tbl = self.env[DEFINES] or Utils.ordered_dict()

	# the user forgot to tell if the value is quoted or not
	if isinstance(value, str):
		if quote == 1:
			tbl[define] = '"%s"' % str(value)
		else:
			tbl[define] = value
	elif isinstance(value, int):
		tbl[define] = value
	else:
		raise TypeError

	# add later to make reconfiguring faster
	self.env[DEFINES] = tbl
	self.env[define] = value # <- not certain this is necessary

@conf
def undefine(self, define):
	"""store a single define and its state into an internal list
	   for later writing to a config header file"""
	assert define and isinstance(define, str)

	tbl = self.env[DEFINES] or Utils.ordered_dict()

	value = UNDEFINED
	tbl[define] = value

	# add later to make reconfiguring faster
	self.env[DEFINES] = tbl
	self.env[define] = value

@conf
def define_cond(self, name, value):
	"""Conditionally define a name.
	Formally equivalent to: if value: define(name, 1) else: undefine(name)"""
	if value:
		self.define(name, 1)
	else:
		self.undefine(name)

@conf
def is_defined(self, key):
	defines = self.env[DEFINES]
	if not defines:
		return False
	try:
		value = defines[key]
	except KeyError:
		return False
	else:
		return value != UNDEFINED

@conf
def get_define(self, define):
	"get the value of a previously stored define"
	try: return self.env[DEFINES][define]
	except KeyError: return None

@conf
def have_define(self, name):
	"prefix the define with 'HAVE_' and make sure it has valid characters."
	return "HAVE_%s" % Utils.quote_define_name(name)

@conf
def write_config_header(self, configfile='', env=''):
	"save the defines into a file"
	if not configfile: configfile = WAF_CONFIG_H

	lst = Utils.split_path(configfile)
	base = lst[:-1]

	if not env: env = self.env
	base = [self.blddir, env.variant()]+base
	dir = os.path.join(*base)
	if not os.path.exists(dir):
		os.makedirs(dir)

	dir = os.path.join(dir, lst[-1])

	self.env.append_value('waf_config_files', os.path.abspath(dir))

	waf_guard = '_%s_WAF' % Utils.quote_define_name(configfile)

	dest = open(dir, 'w')
	dest.write('/* Configuration header created by Waf - do not edit */\n')
	dest.write('#ifndef %s\n#define %s\n\n' % (waf_guard, waf_guard))

	# config files are not removed on "waf clean"
	if not configfile in self.env['dep_files']:
		self.env['dep_files'] += [configfile]

	tbl = env[DEFINES] or Utils.ordered_dict()
	for key in tbl.allkeys:
		value = tbl[key]
		if value is None:
			dest.write('#define %s\n' % key)
		elif value is UNDEFINED:
			dest.write('/* #undef %s */\n' % key)
		else:
			dest.write('#define %s %s\n' % (key, value))

	dest.write('\n#endif /* %s */\n' % waf_guard)
	dest.close()

@conftest
def cc_check_features(self, kind='cc'):
	v = self.env
	# check for compiler features: programs, shared and static libraries
	test = Configure.check_data()
	test.code = 'int main() {return 0;}\n'
	test.env = v
	test.execute = 1
	test.force_compiler = kind
	ret = self.run_check(test)
	self.check_message('compiler could create', 'programs', not (ret is False))
	if not ret: self.fatal("no programs")

	lib_obj = Configure.check_data()
	lib_obj.code = "int k = 3;\n"
	lib_obj.env = v
	lib_obj.build_type = "shlib"
	lib_obj.force_compiler = kind
	ret = self.run_check(lib_obj)
	self.check_message('compiler could create', 'shared libs', not (ret is False))
	if not ret: self.fatal("no shared libs")

	lib_obj = Configure.check_data()
	lib_obj.code = "int k = 3;\n"
	lib_obj.env = v
	lib_obj.build_type = "staticlib"
	lib_obj.force_compiler = kind
	ret = self.run_check(lib_obj)
	self.check_message('compiler could create', 'static libs', not (ret is False))
	if not ret: self.fatal("no static libs")

@conftest
def cxx_check_features(self):
	return cc_check_features(self, kind='cpp')

@conf
def check_pkg(self, modname, destvar='', vnum='', pkgpath='', pkgbin='',
              pkgvars=[], pkgdefs={}, mandatory=False):
	"wrapper provided for convenience"
	pkgconf = self.create_pkgconfig_configurator()

	if not destvar: destvar = modname.upper()

	pkgconf.uselib_store = destvar
	pkgconf.name = modname
	pkgconf.version = vnum
	if pkgpath: pkgconf.pkgpath = pkgpath
	pkgconf.binary = pkgbin
	pkgconf.variables = pkgvars
	pkgconf.defines = pkgdefs
	pkgconf.mandatory = mandatory
	return pkgconf.run()

@conf
def pkgconfig_fetch_variable(self, pkgname, variable, pkgpath='', pkgbin='', pkgversion=0):

	if not pkgbin: pkgbin='pkg-config'
	if pkgpath: pkgpath='PKG_CONFIG_PATH=$PKG_CONFIG_PATH:'+pkgpath
	pkgcom = '%s %s' % (pkgpath, pkgbin)
	if pkgversion:
		ret = os.popen("%s --atleast-version=%s %s" % (pkgcom, pkgversion, pkgname)).close()
		self.conf.check_message('package %s >= %s' % (pkgname, pkgversion), '', not ret)
		if ret:
			return '' # error
	else:
		ret = os.popen("%s %s" % (pkgcom, pkgname)).close()
		self.check_message('package %s ' % (pkgname), '', not ret)
		if ret:
			return '' # error

	return Utils.cmd_output('%s --variable=%s %s' % (pkgcom, variable, pkgname)).strip()


