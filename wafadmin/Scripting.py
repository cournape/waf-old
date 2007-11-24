#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, cPickle
import Params, Utils, Configure, Environment, Build, Runner, Options
from Params import error, fatal, warning, g_lockfile
import pproc as subprocess

g_dirwatch   = None
g_daemonlock = 0
g_excludes = '.svn CVS wafadmin .arch-ids {arch}'.split()
"exclude folders from dist"
g_dist_exts  = '.rej .orig ~ .pyc .pyo .bak config.log .tar.bz2 .zip Makefile'.split()
"exclude files from dist"

g_distclean_exts = '~ .pyc .wafpickle'.split()

def add_subdir(dir, bld):
	"each wscript calls bld.add_subdir"
	try: bld.rescan(bld.m_curdirnode)
	except OSError: fatal("No such directory "+bld.m_curdirnode.abspath())

	old = bld.m_curdirnode
	new = bld.m_curdirnode.ensure_node_from_lst(Utils.split_path(dir))
	if new is None:
		fatal("subdir not found (%s), restore is %s" % (dir, bld.m_curdirnode))

	bld.m_curdirnode=new
	# try to open 'wscript_build' for execution
	# if unavailable, open the module wscript and call the build function from it
	from Common import install_files, install_as, symlink_as # do not remove
	try:
		file_path = os.path.join(new.abspath(), 'wscript_build')
		file = open(file_path, 'r')
		exec file
		if file: file.close()
	except IOError:
		file_path = os.path.join(new.abspath(), 'wscript')
		module = Utils.load_module(file_path)
		module.build(bld)

	# restore the old node position
	bld.m_curdirnode=old

	#
	#node = bld.m_curdirnode.ensure_node_from_lst(Utils.split_path(dir))
	#if node is None:
	#	fatal("subdir not found (%s), restore is %s" % (dir, bld.m_curdirnode))
	#bld.m_subdirs = [[node, bld.m_curdirnode]] + bld.m_subdirs

def call_back(idxName, pathName, event):
	#print "idxName=%s, Path=%s, Event=%s "%(idxName, pathName, event)
	# check the daemon lock state
	global g_daemonlock
	if g_daemonlock: return
	g_daemonlock = 1

	# clean up existing variables, and start a new instance
	Utils.reset()
	Main()
	g_daemonlock = 0

def start_daemon():
	"if it does not exist already:start a new directory watcher; else: return immediately"
	global g_dirwatch
	if not g_dirwatch:
		import DirWatch
		g_dirwatch = DirWatch.DirectoryWatcher()
		m_dirs=[]
		for nodeDir in Params.g_build.m_srcnode.dirs():
			tmpstr = "%s" %nodeDir
			tmpstr = "%s" %(tmpstr[3:])[:-1]
			m_dirs.append(tmpstr)
		g_dirwatch.add_watch("tmp Test", call_back, m_dirs)
		# infinite loop, no need to exit except on ctrl+c
		g_dirwatch.loop()
		g_dirwatch = None
	else:
		g_dirwatch.suspend_all_watch()
		m_dirs=[]
		for nodeDir in Params.g_build.m_srcnode.dirs():
			tmpstr = "%s" %nodeDir
			tmpstr = "%s" %(tmpstr[3:])[:-1]
			m_dirs.append(tmpstr)
		g_dirwatch.add_watch("tmp Test", call_back, m_dirs)

def configure():
	Runner.set_exec('normal')
	tree = Build.Build()

	err = 'The %s is not given in %s:\n * define a top level attribute named "%s"\n * run waf configure --%s=xxx'

	src = getattr(Params.g_options, 'srcdir', None)
	if not src: src = getattr(Utils.g_module, 'srcdir', None)
	if not src: fatal(err % ('srcdir', os.path.abspath('.'), 'srcdir', 'srcdir'))

	bld = getattr(Params.g_options, 'blddir', None)
	if not bld: bld = getattr(Utils.g_module, 'blddir', None)
	if not bld: fatal(err % ('blddir', os.path.abspath('.'), 'blddir', 'blddir'))

	Params.g_cachedir = os.path.join(bld, '_cache_')
	tree.load_dirs(src, bld)

	conf = Configure.Configure(srcdir=src, blddir=bld)
	try:
		conf.sub_config('')
	except Configure.ConfigurationError, e:
		Params.pprint('RED', str(e))
		sys.exit(2)
	conf.store(tree)
	conf.cleanup()

	# this will write a configure lock so that subsequent run will
	# consider the current path as the root directory, to remove: use 'waf distclean'
	file = open(g_lockfile, 'w')
	w = file.write

	proj={}
	proj['blddir']=bld
	proj['srcdir']=src
	proj['argv']=sys.argv[1:]
	proj['hash']=conf.hash
	proj['files']=conf.files
	cPickle.dump(proj, file)
	file.close()

def read_cache_file(filename):
	file = open(g_lockfile, 'r')
	proj = cPickle.load(file)
	file.close()
	return proj

def Main():
	import inspect
	if Params.g_commands['configure']:
		configure()
		Params.pprint('GREEN', 'Configuration finished successfully; project is now ready to build.')
		sys.exit(0)

	Runner.set_exec('noredir')

	# compile the project and/or install the files
	bld = Build.Build()
	try:
		proj = read_cache_file(g_lockfile)
	except IOError:
		if Params.g_commands['clean']:
			fatal("Nothing to clean (project not configured)", ret=0)
		else:
			warning("Run waf configure first...")
			if Params.g_autoconfig:
				configure()
				bld = Build.Build()
				proj = read_cache_file(g_lockfile)
			else:
				sys.exit(0)

	if Params.g_autoconfig:
		reconf = 0

		try:
			hash = 0
			for file in proj['files']:
				mod = Utils.load_module(file)
				hash = Params.hash_function_with_globals(hash, mod.configure)
			reconf = (hash != proj['hash'])
		except Exception, ex:
			warning("Reconfiguring the project as an exception occured: %s" % (str(ex),))
			reconf=1

		if reconf:
			warning("Reconfiguring the project as the configuration changed")


			a1 = Params.g_commands
			a2 = Params.g_options
			a3 = Params.g_zones
			a4 = Params.g_verbose

			Options.g_parser.parse_args(args=proj['argv'])
			configure()

			Params.g_commands = a1
			Params.g_options = a2
			Params.g_zones = a3
			Params.g_verbose = a4

			bld = Build.Build()
			proj = read_cache_file(g_lockfile)

	Params.g_cachedir = os.path.join(proj['blddir'], '_cache_')

	bld.load_dirs(proj['srcdir'], proj['blddir'])
	bld.load_envs()

	#bld.dump()
	Utils.g_module.build(bld)

	"""
	# bld.m_subdirs can be modified *within* the loop, so do not touch this piece of code
	while bld.m_subdirs:
		# read scripts, saving the context everytime (bld.m_curdirnode)

		# cheap queue
		lst=bld.m_subdirs[0]
		bld.m_subdirs=bld.m_subdirs[1:]

		new=lst[0]
		old=lst[1]

		# take the new node position
		bld.m_curdirnode=new

		try: bld.rescan(bld.m_curdirnode)
		except OSError: fatal("No such directory "+bld.m_curdirnode.abspath())

		# try to open 'wscript_build' for execution
		# if unavailable, open the module wscript and call the build function from it
		try:
			file_path = os.path.join(new.abspath(), 'wscript_build')
			file = open(file_path, 'r')
			exec file
			if file: file.close()
		except IOError:
			file_path = os.path.join(new.abspath(), 'wscript')
			module = Utils.load_module(file_path)
			module.build(bld)

		# restore the old node position
		bld.m_curdirnode=old
	"""
	#bld.dump()

	# TODO undocumented hook
	pre_build = getattr(Utils.g_module, 'pre_build', None)
	if pre_build: pre_build()

	# compile
	if Params.g_commands['build'] or Params.g_commands['install']:
		try:
			ret = bld.compile()
			if Params.g_options.progress_bar: print ''
			if not ret: Params.pprint('GREEN', 'Compilation finished successfully')
		finally:
			bld.save()
		if ret:
			msg='Compilation failed'
			if not Params.g_options.daemon: fatal(msg)
			else: error(msg)

	# install
	if Params.g_commands['install'] or Params.g_commands['uninstall']:
		try:
			ret = bld.install()
			if not ret: Params.pprint('GREEN', 'Installation finished successfully')
		finally:
			bld.save()
		if ret: fatal('Compilation failed')

	# clean
	if Params.g_commands['clean']:
		try:
			ret = bld.clean()
			if not ret: Params.pprint('GREEN', 'Project cleaned successfully')
		finally:
			bld.save()
		if ret:
			msg='Cleanup failed for a mysterious reason'
			error(msg)

	# daemon look here
	if Params.g_options.daemon and Params.g_commands['build']:
		start_daemon()
		return

	# shutdown
	fun = getattr(Utils.g_module, 'shutdown', None)
	if fun: fun()

def DistDir(appname, version):
	"make a distribution directory with all the sources in it"
	import shutil

	# Our temporary folder where to put our files
	TMPFOLDER=appname+'-'+version

	# Remove an old package directory
	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)

	# Copy everything into the new folder
	shutil.copytree('.', TMPFOLDER)

	# Remove the Build dir
	dir = getattr(Utils.g_module, 'blddir', None)
	if dir: shutil.rmtree(os.path.join(TMPFOLDER, dir), True)

	# additional exclude files and dirs
	global g_dist_exts, g_excludes

	# Enter into it and remove unnecessary files
	os.chdir(TMPFOLDER)
	for (root, dirs, filenames) in os.walk('.'):
		clean_dirs = []
		for d in dirs:
			if d in g_excludes:
				shutil.rmtree(os.path.join(root,d))
			elif d.startswith('.') or d.startswith(',,') or d.startswith('++'):
				shutil.rmtree(os.path.join(root,d))
			else:
				clean_dirs += d
		dirs = clean_dirs

		for f in list(filenames):
			to_remove = 0
			ends = f.endswith
			if f.startswith('.') or f.startswith('++'):
				to_remove = 1
			else:
				for x in g_dist_exts:
					if ends(x):
						to_remove = True
						break
			if to_remove:
				os.remove(os.path.join(root, f))

	# TODO undocumented hook
	dist_hook = getattr(Utils.g_module, 'dist_hook', None)
	if dist_hook: dist_hook()

	# go back to the root directory
	os.chdir('..')
	return TMPFOLDER

def DistTarball(appname, version):
	"""make a tarball with all the sources in it; return (distdirname, tarballname)"""
	import tarfile, shutil

	TMPFOLDER = DistDir(appname, version)
	tar = tarfile.open(TMPFOLDER+'.tar.bz2','w:bz2')
	tar.add(TMPFOLDER)
	tar.close()
	Params.pprint('GREEN', 'Your archive is ready -> %s.tar.bz2' % TMPFOLDER)

	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)
	return (TMPFOLDER, TMPFOLDER+'.tar.bz2')

def Dist(appname, version):
	"""make a tarball with all the sources in it"""
	DistTarball(appname, version)
	sys.exit(0)

def DistClean():
	"""clean the project"""
	import os, shutil, types
	import Build

	# remove the temporary files
	# the builddir is given by lock-wscript only
	# we do no try to remove it if there is no lock file (rmtree)
	for (root, dirs, filenames) in os.walk('.'):
		for f in list(filenames):
			to_remove = 0
			if f==g_lockfile:
				# removes a lock, and the builddir indicated
				to_remove = True
				try:
					proj = read_cache_file(os.path.join(root, f))
					shutil.rmtree(os.path.join(root, proj['blddir']))
				except OSError: pass
				except IOError: pass
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
			try: shutil.rmtree(f)
			except: pass
	sys.exit(0)

def DistCheck(appname, version):
	"""Makes some sanity checks on the waf dist generated tarball"""
	import shutil, tempfile

	waf = os.path.abspath(sys.argv[0])
	distdir, tarball = DistTarball(appname, version)
	retval = subprocess.Popen('bzip2 -dc %s | tar x' % tarball, shell=True).wait()
	if retval:
		Params.fatal('uncompressing the tarball failed with code %i' % (retval))

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	cwd_before = os.getcwd()
	os.chdir(distdir)
	try:
		retval = subprocess.Popen(
			'%(waf)s configure --prefix %(instdir)s && %(waf)s '
			'&& %(waf)s check && %(waf)s install'
			' && %(waf)s uninstall' % vars(),
			shell=True).wait()
		if retval:
			Params.fatal('distcheck failed with code %i' % (retval))
	finally:
		os.chdir(cwd_before)
	shutil.rmtree(distdir)
	if os.path.exists(instdir):
		Params.fatal("uninstall left files in %s" % (instdir))
