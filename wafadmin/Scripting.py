#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, shutil, traceback, datetime, inspect, errno, subprocess
import Utils, Configure, Build, Logs, Options, ConfigSet, Task
from Logs import error, warn, info
from Constants import *
from Base import WafError
import Base

g_gz = 'bz2'

build_dir_override = None

def waf_entry_point(current_directory, version, wafdir):
	"""This is the main entry point, all Waf execution starts here."""

	if WAFVERSION != version:
		error('Waf script %r and library %r do not match (directory %r)' % (version, WAFVERSION, wafdir))
		sys.exit(1)

	Options.waf_dir = wafdir
	Options.launch_dir = current_directory

	# try to find a lock file (if the project was configured)
	# at the same time, store the first wscript file seen
	cur = current_directory
	while cur:
		if len(cur) <= 3:
			break # root or c:

		lst = os.listdir(cur)
		if Options.lockfile in lst:
			env = ConfigSet.ConfigSet()
			try:
				env.load(os.path.join(cur, Options.lockfile))
			except Exception as e:
				continue

			Options.run_dir = env.run_dir
			Options.top_dir = env.top_dir
			Options.out_dir = env.out_dir

			break

		if not Options.run_dir:
			if WSCRIPT_FILE in lst:
				Options.run_dir = cur

		cur = os.path.dirname(cur)

	if not Options.run_dir:
		if '--version' in sys.argv:
			opt_obj = Options.OptionsContext()
			opt_obj.curdir = current_directory
			opt_obj.parse_args()
			sys.exit(0)
		error('Waf: Run from a directory containing a file named "%s"' % WSCRIPT_FILE)
		sys.exit(1)

	try:
		os.chdir(Options.run_dir)
	except OSError:
		error("Waf: The folder %r is unreadable" % Options.run_dir)
		sys.exit(1)

	try:
		set_main_module(Options.run_dir + os.sep + WSCRIPT_FILE)
	except:
		error("Waf: The wscript in %r is unreadable" % Options.run_dir)
		sys.exit(1)

	parse_options()

	try:
		run_commands()
	except Exception as e:
		traceback.print_exc(file=sys.stdout)
		print(e)
	except WafError as e:
		traceback.print_exc(file=sys.stdout)
		error(str(e))
		sys.exit(1)
	except KeyboardInterrupt:
		Logs.pprint('RED', 'Interrupted')
		sys.exit(68)

def set_main_module(file_path):
	"Load custom options, if defined"
	Base.g_module = Base.load_module(file_path, 'wscript_main')
	Base.g_module.root_path = file_path

	# note: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

	def set_def(obj):
		name = obj.__name__
		if not name in Base.g_module.__dict__:
			setattr(Base.g_module, name, obj)
	for k in [update, dist, distclean, distcheck]:
		set_def(k)
	# add dummy init and shutdown functions if they're not defined
	if not 'init' in Base.g_module.__dict__:
		Base.g_module.init = Utils.nada
	if not 'shutdown' in Base.g_module.__dict__:
		Base.g_module.shutdown = Utils.nada
	if not 'options' in Base.g_module.__dict__:
		Base.g_module.options = Utils.nada

def parse_options():
	opt = Options.OptionsContext().execute()

	if not Options.commands:
		Options.commands = ['build']

	# process some internal Waf options
	Logs.verbose = Options.options.verbose
	Logs.init_log()

	if Options.options.zones:
		Logs.zones = Options.options.zones.split(',')
		if not Logs.verbose:
			Logs.verbose = 1
	elif Logs.verbose > 0:
		Logs.zones = ['runner']

	if Logs.verbose > 2:
		Logs.zones = ['*']

def run_command(cmd_name):
	"""Run a command like it was invoked from the command line."""
	ctx = Base.create_context(cmd_name)
	ctx.current_command = cmd_name
	ctx.execute()

def run_commands():
	run_command('init')
	while Options.commands:
		cmd_name = Options.commands.pop(0)

		timer = Utils.Timer()
		run_command(cmd_name)
		if not Options.options.progress_bar:
			elapsed = ' (%s)' % str(timer)
		info('%r finished successfully%s' % (cmd_name, elapsed))
	run_command('shutdown')

###########################################################################################

excludes = '.bzr .bzrignore .git .gitignore .svn CVS .cvsignore .arch-ids {arch} SCCS BitKeeper .hg _MTN _darcs Makefile Makefile.in config.log'.split()
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

def distclean(ctx):
	'''removes the build directory'''
	lst = os.listdir('.')
	for f in lst:
		if f == Options.lockfile:
			try:
				proj = ConfigSet.ConfigSet(f)
			except:
				Logs.warn('could not read %r' % f)
				continue

			try:
				shutil.rmtree(proj['out_dir'])
			except IOError:
				pass
			except OSError as e:
				if e.errno != errno.ENOENT:
					Logs.warn('project %r cannot be removed' % proj[BLDDIR])

			try:
				os.remove(f)
			except OSError as e:
				if e.errno != errno.ENOENT:
					Logs.warn('file %r cannot be removed' % f)

		# remove the local waf cache
		if f.startswith('.waf-'):
			shutil.rmtree(f, ignore_errors=True)

def dist(ctx):
	'''makes a tarball for redistributing the sources'''
	import tarfile

	appname = getattr(Base.g_module, APPNAME, 'noname')
	version = getattr(Base.g_module, VERSION, '1.0')

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
	copytree('.', tmp_folder, getattr(Base.g_module, BLDDIR, None))

	# undocumented hook for additional cleanup
	dist_hook = getattr(Base.g_module, 'dist_hook', None)
	if dist_hook:
		back = os.getcwd()
		os.chdir(tmp_folder)
		try:
			dist_hook()
		finally:
			# go back to the root directory
			os.chdir(back)

	tar = tarfile.open(arch_name, 'w:' + g_gz)
	tar.add(tmp_folder)
	tar.close()

	from hashlib import sha1
	try:
		digest = " (sha=%r)" % sha1(Utils.readf(arch_name)).hexdigest()
	except:
		digest = ''

	info('New archive created: %s%s' % (arch_name, digest))

	if os.path.exists(tmp_folder): shutil.rmtree(tmp_folder)
	return arch_name

def distcheck(ctx):
	'''checks if the sources compile (tarball from 'dist')'''
	import tempfile, tarfile

	appname = getattr(Base.g_module, APPNAME, 'noname')
	version = getattr(Base.g_module, VERSION, '1.0')

	waf = os.path.abspath(sys.argv[0])
	tarball = dist(appname, version)
	t = tarfile.open(tarball)
	for x in t: t.extract(x)
	t.close()

	path = appname + '-' + version

	instdir = tempfile.mkdtemp('.inst', '%s-%s' % (appname, version))
	ret = subprocess.Popen([waf, 'configure', 'install', 'uninstall', '--destdir=' + instdir], cwd=path).wait()
	if ret:
		raise WafError('distcheck failed with code %i' % ret)

	if os.path.exists(instdir):
		raise WafError('distcheck succeeded, but files were left in %s' % instdir)

	shutil.rmtree(path)

def update(ctx):
	try:
		from urllib import request
	except:
		from urllib import urlopen
	else:
		urlopen = request.urlopen


	local_repo = Options.local_repo or Options.waf_dir
	#tool = Options.option.tool
	tool = 'wafadmin/Tools/tex.py'
	for x in Utils.to_list(Options.remote_repo):
		try:
			print(x + '/' + tool)
			web = urlopen(x + '/' + tool)
		except:
			raise
		else:
			try:
				loc = open(local_repo + os.sep + tool, 'wb')
				loc.write(web.read())
				web.close()
			finally:
				loc.close()
			Logs.warn('updated ' + tool)
			break

