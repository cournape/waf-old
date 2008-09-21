#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
c/c++ configuration routines

The code is being written, so do not complain about trunk being broken :-)
"""

import os, types, imp, cPickle, sys, shlex, shutil
from Utils import md5
import Build, Utils, Configure, Task, Options, Logs
from Constants import *
from Configure import conf, conftest

stdincpath = ['/usr/include/', '/usr/local/include/']
"""standard include paths"""

stdlibpath = ['/usr/lib/', '/usr/local/lib/', '/lib']
"""standard library search paths"""

ver = {
	'atleast-version': '>=',
	'exact-version': '==',
	'max-version': '<=',
}


def parse_flags(line, uselib, env):
	"""stupidest thing ever"""

	lst = shlex.split(line)
	while lst:
		x = lst.pop(0)
		st = x[:2]
		ot = x[2:]

		if st == '-I' or st == '/I':
			if not ot: ot = lst.pop(0)
			env.append_unique('CPPPATH_' + uselib, ot)
		elif st == '-D':
			if not ot: ot = lst.pop(0)
			env.append_unique('CXXDEFINES_' + uselib, ot)
			env.append_unique('CCDEFINES_' + uselib, ot)
		elif st == '-l':
			if not ot: ot = lst.pop(0)
			env.append_unique('LIB_' + uselib, ot)
		elif st == '-L':
			if not ot: ot = lst.pop(0)
			env.append_unique('LIBPATH_' + uselib, ot)
		elif x == '-pthread' or x.startswith('+'):
			env.append_unique('CCFLAGS_' + uselib, x)
			env.append_unique('CXXFLAGS_' + uselib, x)
			env.append_unique('LINKFLAGS_' + uselib, x)
		elif x.startswith('-std'):
			env.append_unique('CCFLAGS_' + uselib, x)
			env.append_unique('LINKFLAGS_' + uselib, x)

@conf
def validate_cfg(self, kw):
	if not 'path' in kw:
		kw['path'] = 'pkg-config --silence-errors'

	# pkg-config version
	if 'atleast_pkgconfig_version' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for pkg-config version >= %s' % kw['atleast_pkgconfig_version']
		return

	# checking for the version of a module, for the moment, one thing at a time
	for x in ver.keys():
		y = x.replace('-', '_')
		if y in kw:
			if not 'package' in kw:
				raise ValueError, '%s requires a package' % x

			if not 'msg' in kw:
				kw['msg'] = 'Checking for %s %s %s' % (kw['package'], ver[x], kw[y])
			return

	if not 'msg' in kw:
		kw['msg'] = 'Checking for %s flags' % kw['package']
	if not 'okmsg' in kw:
		kw['okmsg'] = 'ok'
	if not 'errmsg' in kw:
		kw['errmsg'] = 'not found'

@conf
def exec_cfg(self, kw):

	# pkg-config version
	if 'atleast_pkgconfig_version' in kw:
		try:
			Utils.cmd_output('%s --atleast-pkgconfig-version=%s' % (kw['path'], kw['atleast_pkgconfig_version']))
		except:
			if not 'errmsg' in kw:
				kw['errmsg'] = 'TODO'
			raise Configure.ConfigurationError, kw['errmsg']
		if not 'okmsg' in kw:
			kw['okmsg'] = 'ok'
		return

	# checking for the version of a module
	for x in ver:
		y = x.replace('-', '_')
		if y in kw:
			try:
				Utils.cmd_output('%s --%s=%s %s' % (kw['path'], x, kw[y], kw['package']))
			except:
				if not 'errmsg' in kw:
					kw['errmsg'] = 'TODO 2'
				raise Configure.ConfigurationError, kw['errmsg']
			if not 'okmsg' in kw:
				kw['okmsg'] = 'ok'
			return

	lst = [kw['path']]
	for key, val in Utils.to_list(kw.get('define_variable', [])):
		lst.append('--define-variable=%s=%s' % (key, val))

	lst.append(kw.get('args', ''))
	lst.append(kw['package'])

	# so we assume the command-line will output flags to be parsed afterwards
	cmd = ' '.join(lst)
	try:
		ret = Utils.cmd_output(cmd)
	except:
		if not 'errmsg' in kw:
			kw['errmsg'] = 'TODO3'
		raise
	if not 'okmsg' in kw:
		kw['okmsg'] = 'ok'

	parse_flags(ret, kw.get('uselib_store', kw['package'].upper()), kw.get('env', self.env))

@conf
def check_cfg(self, *k, **kw):
	self.validate_cfg(kw)
	self.check_message_1(kw['msg'])
	ret = None
	try:
		ret = self.exec_cfg(kw)
	except Configure.ConfigurationError, e:
		self.check_message_2(kw['errmsg'], 'YELLOW')
		if 'mandatory' in kw:
			if Logs.verbose > 1:
				raise
			else:
				self.fatal('the configuration failed (see config.log)')
		else:
			pass
	else:
		self.check_message_2(kw['okmsg'])

	return ret

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
# execute: True or False - will return the result of the execution

@conf
def validate_c(self, kw):
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

	assert not(kw['type'] != 'program' and kw.get('execute', 0)), 'can only execute programs'


	#if kw['type'] != 'program' and kw.get('execute', 0):
	#	raise ValueError, 'can only execute programs'

	def to_header(dct):
		if 'header_name' in dct:
			dct = Utils.to_list(dct['header_name'])
			return ''.join(['#include <%s>\n' % x for x in dct])
		return ''


	#OSX
	if 'framework_name' in kw:
		if not kw.get('header_name'):
			kw['header_name'] = []


	if 'function_name' in kw:
		fu = kw['function_name']
		if not 'msg' in kw:
			kw['msg'] = 'Checking for function %s' % fu
		kw['code'] = to_header(kw) + 'int main(){\nvoid *p;\np=(void*)(%s);\nreturn 0;\n}\n' % fu
		if not 'uselib_store' in kw:
			kw['uselib_store'] = fu.upper()
		if not 'define_name' in kw:
			kw['define_name'] = self.have_define(fu)

	elif 'header_name' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for header %s' % kw['header_name']

		# OSX
		if 'framework_name' in kw:
			fwkname = kw['framework_name']
			fwk = '%s/%s.h' % (fwkname, fwkname)
			if kw.get('remove_dot_h', None):
				fwk = fwk[:-2]
			kw['header_name'] = Utils.to_list(kw['header_name']) + [fwk]
			kw['msg'] = 'Checking for framework %s' % fwkname

		l = Utils.to_list(kw['header_name'])
		assert len(l)>0, 'list of headers in header_name is empty'

		kw['code'] = to_header(kw) + 'int main(){return 0;}\n'

		if not 'uselib_store' in kw:
			kw['uselib_store'] = l[0].upper()

		if not 'define_name' in kw:
			kw['define_name'] = self.have_define(l[0])

	if 'lib' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for library %s' % kw['lib']
		if not 'uselib_store' in kw:
			kw['uselib_store'] = kw['lib'].upper()

	if 'staticlib' in kw:
		if not 'msg' in kw:
			kw['msg'] = 'Checking for static library %s' % kw['staticlib']
		if not 'uselib_store' in kw:
			kw['uselib_store'] = kw['staticlib'].upper()

	if 'fragment' in kw:
		# an additional code fragment may be provided to replace the predefined code
		# in custom headers
		kw['code'] = kw['fragment']
		if not 'msg' in kw:
			kw['msg'] = 'Checking for custom code'
		if not 'errmsg' in kw:
			kw['errmsg'] = 'fail'

	if not 'execute' in kw:
		kw['execute'] = False

	if not 'errmsg' in kw:
		kw['errmsg'] = 'not found'

	if not 'okmsg' in kw:
		kw['okmsg'] = 'ok'

	if not 'code' in kw:
		kw['code'] = simple_c_code

	assert('msg' in kw)

@conf
def post_check(self, *k, **kw):
	"set the variables after a test was run successfully"

	def define_or_stuff():
		nm = kw['define_name']
		if not kw['execute'] and not kw.get('define_ret', None):
			self.define_cond(kw['define_name'], kw['success'] is not None)
		else:
			self.define(kw['define_name'], kw['success'])

	is_define = kw['success'] is not None

	if 'header_name' in kw:
		if kw['success']:
			self.env['CPPPATH_' + kw['uselib_store']] = kw.get('include', '')
		define_or_stuff()

	elif 'function_name' in kw:
		define_or_stuff()

	elif 'fragment' in kw:
		if 'define_name' in kw:
			define_or_stuff()

	if kw['success'] and 'uselib_store' in kw:
		import cc, cxx
		for k in set(cc.g_cc_flag_vars).union(cxx.g_cxx_flag_vars):
			lk = k.lower()
			# inconsistency: includes -> CPPPATH
			if k == 'CPPPATH': lk = 'includes'
			if k == 'CXXDEFINES': lk = 'defines'
			if k == 'CCDEFINES': lk = 'defines'
			if lk in kw:
				self.env.append_value(k + '_' + kw['uselib_store'], kw[lk])

@conf
def check(self, *k, **kw):
	# so this will be the generic function
	# it will be safer to use cxx_check or cc_check
	self.validate_c(kw)
	self.check_message_1(kw['msg'])
	ret = None
	try:
		ret = self.run_c_code(*k, **kw)
	except Configure.ConfigurationError, e:
		self.check_message_2(kw['errmsg'], 'YELLOW')
		if 'mandatory' in kw:
			if Logs.verbose > 1:
				raise
			else:
				self.fatal('the configuration failed (see config.log)')
		else:
			pass
	else:
		self.check_message_2(kw['okmsg'])

	kw['success'] = ret
	self.post_check(*k, **kw)
	return ret

@conf
def run_c_code(self, *k, **kw):
	if kw['compiler'] == 'cxx':
		tp = 'cxx'
		test_f_name = 'test.cpp'
	else:
		tp = 'cc'
		test_f_name = 'test.c'

	# create a small folder for testing
	dir = os.path.join(self.blddir, '.wscript-trybuild')

	# if the folder already exists, remove it
	try:
		shutil.rmtree(dir)
	except OSError:
		pass
	os.makedirs(dir)

	bdir = os.path.join(dir, 'testbuild')

	if not os.path.exists(bdir):
		os.makedirs(bdir)

	env = kw['env']

	dest = open(os.path.join(dir, test_f_name), 'w')
	dest.write(kw['code'])
	dest.close()

	back = os.path.abspath('.')

	bld = Build.BuildContext()
	bld.log = self.log
	bld.all_envs.update(self.all_envs)
	bld.all_envs['default'] = env
	bld.lst_variants = bld.all_envs.keys()
	bld.load_dirs(dir, bdir)

	os.chdir(dir)

	bld.rescan(bld.srcnode)

	o = bld.new_task_gen(tp, kw['type'])
	o.source = test_f_name
	o.target = 'testprog'

	for k, v in kw.iteritems():
		setattr(o, k, v)

	self.log.write("==>\n%s\n<==\n" % kw['code'])

	# compile the program
	try:
		bld.compile()
	except:
		ret = Utils.ex_stack()
	else:
		ret = 0

	os.chdir(back)

	# keep the name of the program to execute
	if kw['execute']:
		lastprog = o.link_task.outputs[0].abspath(env)

	if ret:
		raise Configure.ConfigurationError, str(ret)

	# if we need to run the program, try to get its result
	if kw['execute']:
		data = Utils.cmd_output('"%s"' % lastprog).strip()
		ret = data

	return ret

@conf
def check_cxx(self, *k, **kw):
	kw['compiler'] = 'cxx'
	return self.check(*k, **kw)

@conf
def check_cc(self, *k, **kw):
	kw['compiler'] = 'cc'
	return self.check(*k, **kw)

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


