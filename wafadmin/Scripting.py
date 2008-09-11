#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, shutil, traceback, time

import Utils, Configure, Build, Logs, Options, Environment
from Logs import error, warn, info
from Constants import *

g_gz = 'bz2'
g_dirwatch = None
g_excludes = '.svn CVS .arch-ids {arch} SCCS BitKeeper .hg'.split()
"exclude folders from dist"
g_dist_exts = '~ .rej .orig .pyc .pyo .bak config.log .tar.bz2 .zip Makefile Makefile.in'.split()
"exclude files from dist"

g_distclean_exts = '~ .pyc .wafpickle'.split()

def add_subdir(dir, bld):
	"each wscript calls bld.add_subdir"
	try: bld.rescan(bld.path)
	except OSError: raise Utils.WscriptError("No such directory "+bld.path.abspath())

	old = bld.path
	new = bld.path.find_dir(dir)
	if new is None:
		raise Utils.WscriptError("subdir not found (%s), restore is %s" % (dir, bld.path))

	bld.path = new
	# try to open 'wscript_build' for execution
	# if unavailable, open the module wscript and call the build function from it
	try:
		file_path = os.path.join(new.abspath(), WSCRIPT_BUILD_FILE)
		file = open(file_path, 'r')
		exec file
		if file: file.close()
	except IOError:
		file_path = os.path.join(new.abspath(), WSCRIPT_FILE)
		module = Utils.load_module(file_path)
		module.build(bld)

	# restore the old node position
	bld.path = old

def configure():
	tree = Build.BuildContext()

	err = 'The %s is not given in %s:\n * define a top level attribute named "%s"\n * run waf configure --%s=xxx'

	src = getattr(Options.options, SRCDIR, None)
	if not src: src = getattr(Utils.g_module, SRCDIR, None)
	if not src: raise Utils.WscriptError(err % (SRCDIR, os.path.abspath('.'), SRCDIR, SRCDIR))
	src = os.path.abspath(src)

	bld = getattr(Options.options, BLDDIR, None)
	if not bld: bld = getattr(Utils.g_module, BLDDIR, None)
	if not bld: raise Utils.WscriptError(err % (BLDDIR, os.path.abspath('.'), BLDDIR, BLDDIR))
	bld = os.path.abspath(bld)

	tree.load_dirs(src, bld, False)

	conf = Configure.ConfigurationContext(srcdir=src, blddir=bld)

	# calling to main wscript's configure()
	conf.sub_config('')

	conf.store(tree)

	# this will write a configure lock so that subsequent run will
	# consider the current path as the root directory, to remove: use 'waf distclean'
	env = Environment.Environment()
	env[BLDDIR] = bld
	env[SRCDIR] = src
	env['argv'] = sys.argv
	env['hash'] = conf.hash
	env['files'] = conf.files
	env['commands'] = Options.commands
	env['options'] = Options.options.__dict__
	env.store(Options.lockfile)

def read_cache_file(filename):
	env = Environment.Environment()
	env.load(filename)
	return env

def prepare_impl(t, cwd, ver, wafdir):
	Options.tooldir = [t]
	Options.launch_dir = cwd

	# some command-line options can be processed immediately
	if '--version' in sys.argv:
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		sys.exit(0)

	# now find the wscript file
	msg1 = 'Waf: *** Nothing to do! Please run waf from a directory containing a file named "%s"' % WSCRIPT_FILE

	# Some people want to configure their projects gcc-style:
	# mkdir build && cd build && ../waf configure && ../waf
	# check that this is really what is wanted
	build_dir_override = None
	candidate = None

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
			error("arg[0] directory does not contain a wscript file")
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
		cwd = cwd[:cwd.rfind(os.sep)] # climb up

	if not candidate:
		# check if the user only wanted to display the help
		if '-h' in sys.argv or '--help' in sys.argv:
			warn('No wscript file found: the help message may be incomplete')
			opt_obj = Options.Handler()
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
	opt_obj = Options.Handler()
	opt_obj.sub_options('')
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
		print '\033[91mError: %s\033[0m' % msg
		sys.exit(1)

	try:
		prepare_impl(t, cwd, ver, wafdir)
	except Utils.WafError, e:
		error(e)
		sys.exit(1)

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
		proj = read_cache_file(Options.lockfile)
	except IOError:
		if Options.commands['clean']:
			raise Utils.WafError("Nothing to clean (project not configured)")
		else:
			if Configure.autoconfig:
				warn("Reconfiguring the project")
				configure()
				bld = Build.BuildContext()
				proj = read_cache_file(Options.lockfile)
			else:
				raise Utils.WafError("Project not configured (run 'waf configure' first)")

	if Configure.autoconfig:
		if not Options.commands['clean'] and not Options.commands['uninstall']:
			reconf = 0
			hash = 0
			try:
				for file in proj['files']:
					mod = Utils.load_module(file)
					h = Utils.hash_function_with_globals(hash, mod.configure)
				reconf = (h != proj['hash'])
			except Exception, ex:
				warn("Reconfiguring the project (an exception occurred: %s)" % (str(ex),))
				reconf = 1

			if reconf:
				warn("Reconfiguring the project (the configuration has changed)")

				back = (Options.commands, Options.options, Logs.zones, Logs.verbose)

				Options.commands = proj['commands']
				Options.options.__dict__ = proj['options']
				configure()

				(Options.commands, Options.options, Logs.zones, Logs.verbose) = back

				bld = Build.BuildContext()
				proj = read_cache_file(Options.lockfile)

	bld.load_dirs(proj[SRCDIR], proj[BLDDIR])
	bld.load_envs()

	f = getattr(Utils.g_module, 'build', None)
	if f:
		f(bld)
	else:
		# find the main wscript
		main_wscript = None
		for (file_path, module) in Utils.g_loaded_modules.items():
			if module.__name__ == 'wscript_main':
				main_wscript = file_path
				break
		raise Utils.WscriptError("Could not find the function 'def build(bld).'", main_wscript)

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
		#"""
		bld.compile()
		"""
		import cProfile, pstats
		cProfile.run("import Build; Build.bld.compile()", 'profi.txt')
		p = pstats.Stats('profi.txt')
		p.sort_stats('time').print_stats(150)
		#"""

		if Options.options.progress_bar: print ''

		if Options.is_install:
			bld.install()

		ela = ''
		if not Options.options.progress_bar:
			ela = time.strftime(' (%H:%M:%S)', time.gmtime(time.time() - ini))
		if Options.commands['install']: msg = 'Compilation and installation finished successfully%s' % ela
		elif Options.commands['uninstall']: msg = 'Uninstallation finished successfully%s' % ela
		else: msg = 'Compilation finished successfully%s' % ela
		info(msg)

	# clean
	if Options.commands['clean']:
		try:
			bld.clean()
			info('Cleaning finished successfully')
		finally:
			bld.save()
		#if ret:
		#	msg='Cleanup failed for a mysterious reason'
		#	error(msg)

	# shutdown
	fun = getattr(Utils.g_module, 'shutdown', None)
	if fun: fun()

## Note: this is a modified version of shutil.copytree from python
## 2.5.2 library; modified for WAF purposes to exclude dot dirs and
## another list of files.
def copytree(src, dst, symlinks=False, excludes=(), build_dir=None):
	names = os.listdir(src)
	os.makedirs(dst)
	errors = []
	for name in names:
		srcname = os.path.join(src, name)
		dstname = os.path.join(dst, name)
		try:
			if symlinks and os.path.islink(srcname):
				linkto = os.readlink(srcname)
				os.symlink(linkto, dstname)
			elif os.path.isdir(srcname):
				if name in excludes:
					continue
				elif name.startswith('.') or name.startswith(',,') or name.startswith('++'):
					continue
				elif name == build_dir:
					continue
				else:
					## build_dir is not passed into the recursive
					## copytree, but that is intentional; it is a
					## directory name valid only at the top level.
					copytree(srcname, dstname, symlinks, excludes)
			else:
				ends = name.endswith
				to_remove = False
				if name.startswith('.') or name.startswith('++'):
					to_remove = True
				else:
					for x in g_dist_exts:
						if ends(x):
							to_remove = True
							break
				if not to_remove:
					shutil.copy2(srcname, dstname)
			# XXX What about devices, sockets etc.?
		except (IOError, os.error), why:
			errors.append((srcname, dstname, str(why)))
		# catch the Error from the recursive copytree so that we can
		# continue with other files
		except shutil.Error, err:
			errors.extend(err.args[0])
	try:
		shutil.copystat(src, dst)
	except WindowsError:
		# can't copy file access times on Windows
		pass
	except OSError, why:
		errors.extend((src, dst, str(why)))
	if errors:
		raise shutil.Error, errors

def distclean():
	"""clean the project"""

	# remove the temporary files
	# the builddir is given by lock-wscript only
	# we do no try to remove it if there is no lock file (rmtree)
	for (root, dirs, filenames) in os.walk('.'):
		for f in list(filenames):
			to_remove = 0
			if f == Options.lockfile:
				# removes a lock, and the builddir indicated
				to_remove = True
				try:
					proj = read_cache_file(os.path.join(root, f))
					shutil.rmtree(os.path.join(root, proj[BLDDIR]))
				except (OSError, IOError):
					# ignore errors if the lockfile or the builddir not exist.
					pass
			else:
				ends = f.endswith
				for x in g_distclean_exts:
					if ends(x):
						to_remove = 1
						break
			if to_remove:
				os.remove(os.path.join(root, f))
	lst = os.listdir('.')
	for f in lst:
		if f.startswith('.waf-'):
			shutil.rmtree(f, ignore_errors=True)
	info('distclean finished successfully')

def dist(appname='', version=''):
	"""make a tarball with all the sources in it; return (distdirname, tarballname)"""
	import tarfile

	if not appname: appname = getattr(Utils.g_module, APPNAME, 'noname')
	if not version: version = getattr(Utils.g_module, VERSION, '1.0')

	# Our temporary folder where to put our files
	TMPFOLDER = appname + '-' + version

	# Remove an old package directory
	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)

	global g_dist_exts, g_excludes

	# Remove the Build dir
	build_dir = getattr(Utils.g_module, BLDDIR, None)

	# Copy everything into the new folder
	copytree('.', TMPFOLDER, excludes=g_excludes, build_dir=build_dir)

	# undocumented hook for additional cleanup
	dist_hook = getattr(Utils.g_module, 'dist_hook', None)
	if dist_hook:
		os.chdir(TMPFOLDER)
		try:
			dist_hook()
		finally:
			# go back to the root directory
			os.chdir('..')

	tar = tarfile.open(TMPFOLDER+'.tar.'+g_gz,'w:'+g_gz)
	tar.add(TMPFOLDER)
	tar.close()
	info('Your archive is ready -> %s.tar.%s' % (TMPFOLDER, g_gz))

	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)
	return (TMPFOLDER, TMPFOLDER+'.tar.'+g_gz)

def distcheck(appname='', version=''):
	"""Makes some sanity checks on the waf dist generated tarball"""
	import tempfile, tarfile
	import pproc

	if not appname: appname = getattr(Utils.g_module, APPNAME, 'noname')
	if not version: version = getattr(Utils.g_module, VERSION, '1.0')

	waf = os.path.abspath(sys.argv[0])
	distdir, tarball = dist(appname, version)
	t = tarfile.open(tarball)
	for x in t: t.extract(x)
	t.close()

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	cwd_before = os.getcwd()
	os.chdir(distdir)
	try:
		retval = pproc.Popen(
			'%(waf)s configure && %(waf)s '
			'&& %(waf)s check && %(waf)s install --destdir=%(instdir)s'
			' && %(waf)s uninstall --destdir=%(instdir)s' % vars(),
			shell=True).wait()
		if retval:
			raise Utils.WafError('distcheck failed with code %i' % (retval))
	finally:
		os.chdir(cwd_before)
	shutil.rmtree(distdir)
	if os.path.exists(instdir):
		raise Utils.WafError("distcheck succeeded, but files were left in %s" % (instdir))
	else:
		info('distcheck finished successfully')

