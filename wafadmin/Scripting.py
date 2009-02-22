#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, shutil, traceback, time, inspect

import Utils, Configure, Build, Logs, Options, Environment
from Logs import error, warn, info
from Constants import *

g_gz = 'bz2'


class Context(object):
	pass


def recurse(self, dirs, name=''):
	if not name:
		name = inspect.stack()[1][3]

	if isinstance(dirs, str):
		dirs = Utils.to_list(dirs)

	if not getattr(self, 'curdir', None):
		self.curdir = os.getcwd()

	for x in dirs:
		if os.path.isabs(x):
			nexdir = x
		else:
			nexdir = os.path.join(self.curdir, x)

		base = os.path.join(nexdir, WSCRIPT_FILE)

		try:
			txt = Utils.readf(base + '_' + name)
		except (OSError, IOError):
			try:
				module = Utils.load_module(base)
			except OSError:
				raise Utils.WscriptError('No such script %s' % base)

			try:
				f = module.__dict__[name]
			except KeyError:
				raise Utils.WscriptError('No function %s defined in %s' % (name, base))

			if getattr(self.__class__, 'pre_recurse', None):
				self.pre_recurse(f, base, nexdir)
			old = self.curdir
			self.curdir = nexdir
			try:
				f(self)
			finally:
				self.curdir = old
			if getattr(self.__class__, 'post_recurse', None):
				self.post_recurse(f, base, nexdir)
		else:
			if getattr(self.__class__, 'pre_recurse', None):
				self.pre_recurse(txt, base + '_' + name, nexdir)
			old = self.curdir
			self.curdir = nexdir
			try:
				exec txt
			finally:
				self.curdir = old
			if getattr(self.__class__, 'post_recurse', None):
				self.post_recurse(txt, base + '_' + name, nexdir)

def add_subdir(dir, bld):
	"each wscript calls bld.add_subdir - TODO obsolete, remove in Waf 1.6"
	bld.recurse(dir, 'build')

def configure():
	err = 'The %s is not given in %s:\n * define a top level attribute named "%s"\n * run waf configure --%s=xxx'

	src = getattr(Options.options, SRCDIR, None)
	if not src: src = getattr(Utils.g_module, SRCDIR, None)
	if not src: raise Utils.WscriptError(err % (SRCDIR, os.path.abspath('.'), SRCDIR, SRCDIR))
	src = os.path.abspath(src)

	bld = getattr(Options.options, BLDDIR, None)
	if not bld: bld = getattr(Utils.g_module, BLDDIR, None)
	if not bld: raise Utils.WscriptError(err % (BLDDIR, os.path.abspath('.'), BLDDIR, BLDDIR))
	bld = os.path.abspath(bld)

	try: os.makedirs(bld)
	except OSError: pass
	conf = Configure.ConfigurationContext(srcdir=src, blddir=bld)
	# TODO cleanup this mess
	conf.curdir = os.getcwd()
	setattr(conf.__class__, 'recurse', recurse)

	# calling to main wscript's configure()
	conf.sub_config([''])

	conf.store()

	# this will write a configure lock so that subsequent builds will
	# consider the current path as the root directory (see prepare_impl).
	# to remove: use 'waf distclean'
	env = Environment.Environment()
	env[BLDDIR] = bld
	env[SRCDIR] = src
	env['argv'] = sys.argv
	env['commands'] = Options.commands
	env['options'] = Options.options.__dict__

	# conf.hash & conf.files hold wscript files paths and hash
	# (used only by Configure.autoconfig)
	env['hash'] = conf.hash
	env['files'] = conf.files
	env.store(Options.lockfile)

def prepare_impl(t, cwd, ver, wafdir):
	Options.tooldir = [t]
	Options.launch_dir = cwd

	# some command-line options can be processed immediately
	if '--version' in sys.argv:
		opt_obj = Options.Handler()
		opt_obj.curdir = cwd
		setattr(opt_obj.__class__, 'recurse', recurse)
		opt_obj.parse_args()
		sys.exit(0)

	# now find the wscript file
	msg1 = 'Waf: *** Nothing to do! Please run waf from a directory containing a file named "%s"' % WSCRIPT_FILE

	# Some people want to configure their projects gcc-style:
	# mkdir build && cd build && ../waf configure && ../waf
	# check that this is really what is wanted
	build_dir_override = None
	candidate = None

	# TODO something weird - cwd is the input
	cwd = Options.launch_dir
	lst = os.listdir(cwd)

	search_for_candidate = True
	if WSCRIPT_FILE in lst:
		candidate = cwd
	elif 'configure' in sys.argv and not WSCRIPT_BUILD_FILE in lst:
		# gcc-style configuration
		# look in the calling directory for a wscript file "/foo/bar/configure"
		calldir = os.path.abspath(os.path.dirname(sys.argv[0]))
		if WSCRIPT_FILE in os.listdir(calldir):
			candidate = calldir
			search_for_candidate = False
		else:
			error('arg[0] directory does not contain a wscript file')
			sys.exit(1)
		build_dir_override = cwd


	# climb up to find a script if it is not found
	while search_for_candidate:
		if len(cwd) <= 3:
			break # stop at / or c:
		dirlst = os.listdir(cwd)
		if WSCRIPT_FILE in dirlst:
			candidate = cwd
		if 'configure' in sys.argv and candidate:
			break
		if Options.lockfile in dirlst:
			break
		cwd = os.path.dirname(cwd) # climb up

	if not candidate:
		# check if the user only wanted to display the help
		if '-h' in sys.argv or '--help' in sys.argv:
			warn('No wscript file found: the help message may be incomplete')
			opt_obj = Options.Handler()
			setattr(opt_obj.__class__, 'recurse', recurse)
			opt_obj.curdir = cwd
			opt_obj.parse_args()
		else:
			error(msg1)
		sys.exit(0)

	# We have found wscript, but there is no guarantee that it is valid
	os.chdir(candidate)

	# define the main module containing the functions init, shutdown, ..
	Utils.set_main_module(os.path.join(candidate, WSCRIPT_FILE))

	if build_dir_override:
		d = getattr(Utils.g_module, BLDDIR, None)
		if d:
			# test if user has set the blddir in wscript.
			msg = ' Overriding build directory %s with %s' % (d, build_dir_override)
			warn(msg)
		Utils.g_module.blddir = build_dir_override

	# now parse the options from the user wscript file
	opt_obj = Options.Handler(Utils.g_module)
	opt_obj.curdir = cwd
	setattr(opt_obj.__class__, 'recurse', recurse)
	opt_obj.sub_options([''])
	opt_obj.parse_args()

	fun = getattr(Utils.g_module, 'init', None)
	if fun: fun()

	# for dist, distclean and distcheck
	for x in ['dist', 'distclean', 'distcheck']:
		if Options.commands[x]:
			fun = getattr(Utils.g_module, x, None)
			if fun:
				fun()
			else:
				# bad
				eval(x+'()')
			sys.exit(0)
	main()

def prepare(t, cwd, ver, wafdir):
	if WAFVERSION != ver:
		msg = 'Version mismatch: waf %s <> wafadmin %s (wafdir %s)' % (ver, WAFVERSION, wafdir)
		print('\033[91mError: %s\033[0m' % msg)
		sys.exit(1)

	#"""
	try:
		prepare_impl(t, cwd, ver, wafdir)
	except Utils.WafError, e:
		error(e)
		sys.exit(1)
	except KeyboardInterrupt:
		Utils.pprint('RED', 'Interrupted')
		sys.exit(68)
	"""
	import cProfile, pstats
	cProfile.runctx("import Scripting; Scripting.prepare_impl(t, cwd, ver, wafdir)", {},
		{'t': t, 'cwd':cwd, 'ver':ver, 'wafdir':wafdir},
		 'profi.txt')
	p = pstats.Stats('profi.txt')
	p.sort_stats('time').print_stats(45)
	#"""

def main():
	if Options.commands['configure']:
		ini = time.time()
		configure()
		ela = ''
		if not Options.options.progress_bar: ela = time.strftime(' (%H:%M:%S)', time.gmtime(time.time() - ini))
		info('Configuration finished successfully%s; project is now ready to build.' % ela)
		sys.exit(0)

	# compile the project and/or install the files
	bld = Build.BuildContext()
	try:
		proj = Environment.Environment(Options.lockfile)
	except IOError:
		if Options.commands['clean']:
			raise Utils.WafError("Nothing to clean (project not configured)")
		else:
			raise Utils.WafError("Project not configured (run 'waf configure' first)")

	if Configure.autoconfig:
		if not Options.commands['clean'] and not Options.commands['uninstall']:
			reconf = 0
			h = 0
			try:
				for file in proj['files']:
					mod = Utils.load_module(file)
					h = Utils.hash_function_with_globals(h, mod.configure)
			except Exception, e:
				warn("Reconfiguring the project (an exception occurred: %s)" % (str(e),))
				reconf = 1
			if (h != proj['hash']):
				reconf = 1
			if reconf:
				warn("Reconfiguring the project (the configuration has changed)")

				back = (Options.commands, Options.options, Logs.zones, Logs.verbose)

				Options.commands = proj['commands']
				Options.options.__dict__ = proj['options']
				configure()

				(Options.commands, Options.options, Logs.zones, Logs.verbose) = back

				bld = Build.BuildContext()
				proj = Environment.Environment(Options.lockfile)

	bld.load_dirs(proj[SRCDIR], proj[BLDDIR])
	bld.load_envs()

	# read the scripts - and set the path to the wscript path (useful for srcdir='/foo/bar')
	setattr(bld.__class__, 'recurse', recurse)
	bld.add_subdirs([os.path.split(Utils.g_module.root_path)[0]])

	# TODO undocumented hook
	pre_build = getattr(Utils.g_module, 'pre_build', None)
	if pre_build: pre_build()

	# compile
	if Options.commands['build'] or Options.is_install:
		# TODO quite ugly, no?
		if Options.commands['uninstall']:
			import Task
			def runnable_status(self):
				return SKIP_ME
			setattr(Task.Task, 'runnable_status', runnable_status)

		ini = time.time()
		bld.compile()

		if Options.options.progress_bar: print('')

		if Options.is_install:
			bld.install()

		ela = ''
		if not Options.options.progress_bar:
			ela = time.strftime(' (%H:%M:%S)', time.gmtime(time.time() - ini))
		if Options.commands['install']: msg = 'Build and installation finished successfully%s' % ela
		elif Options.commands['uninstall']: msg = 'Uninstallation finished successfully%s' % ela
		else: msg = 'Build finished successfully%s' % ela
		info(msg)

	# clean
	if Options.commands['clean']:
		try:
			bld.clean()
			info('Cleaning finished successfully')
		finally:
			bld.save()

	# shutdown
	fun = getattr(Utils.g_module, 'shutdown', None)
	if fun: fun()

excludes = '.bzr .bzrignore .git .gitignore .svn CVS .cvsignore .arch-ids {arch} SCCS BitKeeper .hg Makefile Makefile.in config.log'.split()
dist_exts = '~ .rej .orig .pyc .pyo .bak .tar.bz2 tar.gz .zip .swp'.split()
def dont_dist(name, src, build_dir):
	global excludes, dist_exts

	if (name.startswith(',,')
		or name.startswith('++')
		or name.startswith('.waf-1.')
		or (src == '.' and name == Options.lockfile)
		or name in excludes
		or name == build_dir
		):
		return True

	for ext in dist_exts:
		if name.endswith(ext):
			return True

	return False

# like shutil.copytree
# exclude files and to raise exceptions immediately
def copytree(src, dst, build_dir):
	names = os.listdir(src)
	os.makedirs(dst)
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)

		if dont_dist(name, src, build_dir):
			continue

		if os.path.isdir(srcname):
			copytree(srcname, dstname, build_dir)
		else:
			shutil.copy2(srcname, dstname)

def distclean():
	"""clean the project"""
	lst = os.listdir('.')
	for f in lst:
		if f == Options.lockfile:
			try:
				proj = Environment.Environment(f)
				shutil.rmtree(proj[BLDDIR])
			except (OSError, IOError):
				pass

			try:
				os.remove(f)
			except (OSError, IOError):
				pass

		# remove the local waf
		if f.startswith('.waf-'):
			shutil.rmtree(f, ignore_errors=True)
	info('distclean finished successfully')

def dist(appname='', version=''):
	"""make a tarball with all the sources in it; return (distdirname, tarballname)"""
	import tarfile

	if not appname: appname = getattr(Utils.g_module, APPNAME, 'noname')
	if not version: version = getattr(Utils.g_module, VERSION, '1.0')

	tmp_folder = appname + '-' + version
	arch_name = tmp_folder+'.tar.'+g_gz

	# remove the previous dir
	try:
		shutil.rmtree(tmp_folder)
	except (OSError, IOError):
		pass

	# remove the previous archive
	try:
		os.remove(arch_name)
	except (OSError, IOError):
		pass

	# copy the files into the temporary folder
	copytree('.', tmp_folder, getattr(Utils.g_module, BLDDIR, None))

	# undocumented hook for additional cleanup
	dist_hook = getattr(Utils.g_module, 'dist_hook', None)
	if dist_hook:
		os.chdir(tmp_folder)
		try:
			dist_hook()
		finally:
			# go back to the root directory
			os.chdir('..')

	tar = tarfile.open(arch_name, 'w:' + g_gz)
	tar.add(tmp_folder)
	tar.close()
	info('Your archive is ready -> %s' % arch_name)

	if os.path.exists(tmp_folder): shutil.rmtree(tmp_folder)
	return arch_name

def distcheck(appname='', version=''):
	"""Makes some sanity checks on the waf dist generated tarball"""
	import tempfile, tarfile
	import pproc

	if not appname: appname = getattr(Utils.g_module, APPNAME, 'noname')
	if not version: version = getattr(Utils.g_module, VERSION, '1.0')

	waf = os.path.abspath(sys.argv[0])
	tarball = dist(appname, version)
	t = tarfile.open(tarball)
	for x in t: t.extract(x)
	t.close()

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	retval = pproc.Popen(
		'%(waf)s configure && %(waf)s'
		' && %(waf)s check && %(waf)s install --destdir=%(instdir)s'
		' && %(waf)s uninstall --destdir=%(instdir)s' % vars(),
		shell=True).wait()
	if retval:
		raise Utils.WafError('distcheck failed with code %i' % (retval))
	if os.path.exists(instdir):
		raise Utils.WafError('distcheck succeeded, but files were left in %s' % (instdir))
	else:
		info('distcheck finished successfully')

