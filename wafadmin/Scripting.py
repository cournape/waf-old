#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, shutil, traceback, time, inspect

import Utils, Configure, Build, Logs, Options, Environment, Task
from Logs import error, warn, info
from Constants import *

g_gz = 'bz2'
commands = []

def prepare_impl(t, cwd, ver, wafdir):
	Options.tooldir = [t]
	Options.launch_dir = cwd

	# some command-line options can be processed immediately
	if '--version' in sys.argv:
		opt_obj = Options.Handler()
		opt_obj.curdir = cwd
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

	#def set_def(obj, name=''):
	#	if not obj.__name__ in Utils.g_module.__dict__:
	#		setattr(Utils.g_module, obj.__name__, obj)

	if not 'dist' in Utils.g_module.__dict__:
		Utils.g_module.dist = dist
	if not 'distclean' in Utils.g_module.__dict__:
		Utils.g_module.distclean = distclean
	if not 'distcheck' in Utils.g_module.__dict__:
		Utils.g_module.distcheck = distcheck

	#if not 'build' in Utils.g_module.__dict__:
	#	Utils.g_module.build = build
	if not 'build_context' in Utils.g_module.__dict__:
		Utils.g_module.build_context = Build.BuildContext

	if not 'clean' in Utils.g_module.__dict__:
		Utils.g_module.clean = clean
	if not 'clean_context' in Utils.g_module.__dict__:
		Utils.g_module.clean_context = Build.BuildContext

	if not 'install' in Utils.g_module.__dict__:
		Utils.g_module.install = install
	if not 'install_context' in Utils.g_module.__dict__:
		Utils.g_module.install_context = Build.BuildContext

	if not 'uninstall' in Utils.g_module.__dict__:
		Utils.g_module.uninstall = uninstall
	if not 'uninstall_context' in Utils.g_module.__dict__:
		Utils.g_module.uninstall_context = Build.BuildContext

	#if not 'configure' in Utils.g_module.__dict__:
	#	Utils.g_module.configure = configure
	if not 'configure_context' in Utils.g_module.__dict__:
		Utils.g_module.configure_context = Configure.ConfigurationContext

	# now parse the options from the user wscript file
	opt_obj = Options.Handler(Utils.g_module)
	opt_obj.curdir = candidate
	try:
		f = Utils.g_module.set_options
	except AttributeError:
		pass
	else:
		opt_obj.sub_options([''])
	opt_obj.parse_args()

	if not 'init' in Utils.g_module.__dict__:
		Utils.g_module.init = Utils.nada
	if not 'shutdown' in Utils.g_module.__dict__:
		Utils.g_module.shutdown = Utils.nada

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
	global commands
	commands = Options.arg_line[:]

	while commands:
		x = commands.pop(0)

		ini = time.time()
		#info('Configuration finished successfully%s; project is ready to build.' % ela)
		if x == 'configure':
			fun = configure
		elif x == 'build':
			fun = build
		else:
			fun = getattr(Utils.g_module, x, None)

		if not fun:
			raise Utils.WscriptError('No such command %r' % x)

		ctx = getattr(Utils.g_module, x + '_context', Utils.Context)()

		if x in ['init', 'shutdown', 'dist', 'distclean', 'distcheck']:
			# compatibility TODO remove in waf 1.6
			try:
				fun(ctx)
			except TypeError:
				fun()
		else:
			fun(ctx)

		ela = ''
		if not Options.options.progress_bar:
			ela = time.strftime(' (%H:%M:%S)', time.gmtime(time.time() - ini))

		if x != 'init' and x != 'shutdown':
			info('%r finished successfully%s' % (x, ela))

		if not commands and x != 'shutdown':
			commands.append('shutdown')

def configure(conf):
	err = 'The %s is not given in %s:\n * define a top level attribute named "%s"\n * run waf configure --%s=xxx'

	src = getattr(Options.options, SRCDIR, None)
	if not src: src = getattr(Utils.g_module, SRCDIR, None)
	if not src: raise Utils.WscriptError(err % (SRCDIR, os.path.abspath('.'), SRCDIR, SRCDIR))
	src = os.path.abspath(src)

	bld = getattr(Options.options, BLDDIR, None)
	if not bld:
		bld = getattr(Utils.g_module, BLDDIR, None)
		if bld == '.':
			raise Utils.WafError('Setting blddir="." may cause distclean problems')
	if not bld: raise Utils.WscriptError(err % (BLDDIR, os.path.abspath('.'), BLDDIR, BLDDIR))
	bld = os.path.abspath(bld)

	try: os.makedirs(bld)
	except OSError: pass

	conf.srcdir = src
	conf.blddir = bld
	conf.post_init()

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

def clean(bld):
	'''removes the build files'''
	try:
		proj = Environment.Environment(Options.lockfile)
	except IOError:
		raise Utils.WafError('Nothing to clean (project not configured)')

	bld.load_dirs(proj[SRCDIR], proj[BLDDIR])
	bld.load_envs()

	# read the scripts - and set the path to the wscript path (useful for srcdir='/foo/bar')
	bld.add_subdirs([os.path.split(Utils.g_module.root_path)[0]])

	try:
		bld.clean()
	finally:
		bld.save()

def check_configured(bld):
	if not Configure.autoconfig:
		return

	def reconf(proj):
		back = (Options.commands, Options.options, Logs.zones, Logs.verbose)

		Options.commands = proj['commands']
		Options.options.__dict__ = proj['options']
		conf = Configure.ConfigurationContext()
		configure(conf)

		(Options.commands, Options.options, Logs.zones, Logs.verbose) = back

	for k in xrange(3):
		try:
			proj = Environment.Environment(Options.lockfile)
		except IOError:
			conf = Configure.ConfigurationContext()
			configure(conf)
		else:
			try:
				bld = Build.BuildContext()
				bld.load_dirs(proj[SRCDIR], proj[BLDDIR])
				bld.load_envs()
			except Utils.WafError:
				reconf(proj)
				return
			break
	else:
		raise Utils.WafError('Auto-config: project does not configure (bug)')

	h = 0
	try:
		for file in proj['files']:
			if file.endswith('configure'):
				h = hash((h, readf(file)))
			else:
				mod = Utils.load_module(file)
				h = hash((h, mod.waf_hash_val))
	except (OSError, IOError):
		warn('Reconfiguring the project: a file is unavailable')
		reconf(proj)
	else:
		if (h != proj['hash']):
			warn('Reconfiguring the project: the configuration has changed')
			reconf(proj)

def install(bld):
	'''installs the build files'''
	Options.commands['install'] = True
	Options.commands['uninstall'] = False

	check_configured(bld)
	build_impl(bld)
	bld.install()

def uninstall(bld):
	'''removes the installed files'''
	Options.commands['install'] = False
	Options.commands['uninstall'] = True

	try:
		def runnable_status(self):
			return SKIP_ME
		setattr(Task.Task, 'runnable_status_back', Task.Task.runnable_status)
		setattr(Task.Task, 'runnable_status', runnable_status)

		build_impl(bld)
		bld.install()
	finally:
		setattr(Task.Task, 'runnable_status', Task.Task.runnable_status_back)

def build(bld):
	check_configured(bld)
	return build_impl(bld)

def build_impl(bld):
	# compile the project and/or install the files
	try:
		proj = Environment.Environment(Options.lockfile)
	except IOError:
		raise Utils.WafError("Project not configured (run 'waf configure' first)")

	bld.load_dirs(proj[SRCDIR], proj[BLDDIR])
	bld.load_envs()

	info("Waf: Entering directory `%s'" % bld.bldnode.abspath())
	bld.add_subdirs([os.path.split(Utils.g_module.root_path)[0]])

	# TODO undocumented hook
	# FIXME remove in waf 1.6
	pre_build = getattr(Utils.g_module, 'pre_build', None)
	if pre_build: pre_build()

	ini = time.time()

	try:
		bld.compile()
	finally:
		info("Waf: Leaving directory `%s'" % bld.bldnode.abspath())

	if Options.options.progress_bar: print('')

	bld.install()

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

# TODO in waf 1.6, change this method if "srcdir == blddir" is allowed
def distclean(ctx=None):
	'''removes the build directory'''
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

		# remove the local waf cache
		if f.startswith('.waf-'):
			shutil.rmtree(f, ignore_errors=True)

# FIXME waf 1.6 a unique ctx parameter, and remove the optional appname and version
def dist(appname='', version=''):
	'''makes a tarball for redistributing the sources'''
	# return return (distdirname, tarballname)
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
	info('The archive is ready: %s' % arch_name)

	if os.path.exists(tmp_folder): shutil.rmtree(tmp_folder)
	return arch_name

# FIXME waf 1.6 a unique ctx parameter, and remove the optional appname and version
def distcheck(appname='', version=''):
	'''checks if the sources compile (tarball from 'dist')'''
	import tempfile, tarfile

	if not appname: appname = getattr(Utils.g_module, APPNAME, 'noname')
	if not version: version = getattr(Utils.g_module, VERSION, '1.0')

	waf = os.path.abspath(sys.argv[0])
	tarball = dist(appname, version)
	t = tarfile.open(tarball)
	for x in t: t.extract(x)
	t.close()

	path = appname + '-' + version

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	ret = Utils.pproc.Popen([waf, 'configure', 'install', 'uninstall', '--destdir=' + instdir], cwd=path).wait()
	if ret:
		raise Utils.WafError('distcheck failed with code %i' % ret)

	if os.path.exists(instdir):
		raise Utils.WafError('distcheck succeeded, but files were left in %s' % instdir)

	shutil.rmtree(path)

# FIXME remove in Waf 1.6 (kept for compatibility)
def add_subdir(dir, bld):
	bld.recurse(dir, 'build')

