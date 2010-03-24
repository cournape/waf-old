#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Module called for configuring, compiling and installing targets"

import os, sys, shutil, traceback, datetime, inspect, errno, subprocess
import Utils, Configure, Build, Logs, Options, ConfigSet, Task
from Logs import error, warn, info
from Constants import *
from Base import WafError, set_main_module
import Base

g_gz = 'bz2'

current_command = ''
"""Name of the currently executing command"""


build_dir_override = None

def waf_entry_point(tools_directory, current_directory, version, wafdir):
	"""This is the main entry point, all Waf execution starts here."""

	if WAFVERSION != version:
		error('Waf script %r and library %r do not match (directory %r)' % (version, WAFVERSION, wafdir))
		sys.exit(1)

	Options.tooldir = [tools_directory]
	Options.launch_dir = current_directory

	if '--version' in sys.argv:
		# some command-line options may be parsed immediately
		opt_obj = Options.OptionsContext()
		opt_obj.curdir = current_directory
		opt_obj.parse_args()
		sys.exit(0)

	try:
		wscript_path = find_wscript_file(current_directory)
		prepare_top_wscript(wscript_path)
		parse_options()
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

def find_wscript_file(current_dir):
	"""Search the directory from which Waf was run, and other dirs, for
	the top-level wscript file."""

	msg1 = 'Waf: Please run waf from a directory containing a file named "%s" or run distclean' % WSCRIPT_FILE

	# in theory projects can be configured in an autotool-like manner:
	# mkdir build && cd build && ../waf configure && ../waf
	candidate = None

	lst = os.listdir(current_dir)

	search_for_candidate = True
	if WSCRIPT_FILE in lst:
		candidate = current_dir

	elif 'configure' in sys.argv and not WSCRIPT_BUILD_FILE in lst:
		# autotool-like configuration
		calldir = os.path.abspath(os.path.dirname(sys.argv[0]))
		if WSCRIPT_FILE in os.listdir(calldir):
			candidate = calldir
			search_for_candidate = False
		else:
			error('arg[0] directory does not contain a wscript file')
			sys.exit(1)
		global build_dir_override
		build_dir_override = current_dir

	# climb up to find a script if it is not found
	while search_for_candidate:
		if len(current_dir) <= 3:
			break # stop at / or c:
		dirlst = os.listdir(current_dir)
		if WSCRIPT_FILE in dirlst:
			candidate = current_dir
		if 'configure' in sys.argv and candidate:
			break
		if Options.lockfile in dirlst:
			env = ConfigSet.ConfigSet()
			try:
				env.load(os.path.join(cwd, Options.lockfile))
			except:
				#error('could not load %r' % Options.lockfile)
				pass
			try:
				os.stat(env['cwd'])
			except:
				candidate = current_dir
			else:
				candidate = env['cwd']
			Options.topdir = candidate
			break
		current_dir = os.path.dirname(current_dir) # climb up

	if not candidate:
		# check if the user only wanted to display the help
		if '-h' in sys.argv or '--help' in sys.argv:
			warn('No wscript file found: the help message may be incomplete')
			opt_obj = Options.OptionsContext()
			opt_obj.curdir = current_dir
			opt_obj.parse_args()
		else:
			error(msg1)
		sys.exit(0)

	# We have found wscript, but there is no guarantee that it is valid
	try:
		os.chdir(candidate)
	except OSError:
		raise WafError("the folder %r is unreadable" % candidate)
	Utils.start_dir = candidate
	return os.path.join(candidate, WSCRIPT_FILE)

def prepare_top_wscript(wscript_path):
	"""Load the Python module contained in the wscript file and prepare it
	for execution. This includes adding standard functions that might be undefined."""

	# define the main module containing the functions init, shutdown, ..
	set_main_module(wscript_path)

	if build_dir_override:
		d = getattr(Base.g_module, BLDDIR, None)
		if d: # test if user has set the build directory in the wscript.
			warn(' Overriding build directory %s with %s' % (d, build_dir_override))
		Base.g_module.BLDDIR = build_dir_override

	# add default installation, uninstallation, etc. functions to the wscript
	# TODO remove this!
	def set_def(obj):
		name = obj.__name__
		if not name in Base.g_module.__dict__:
			setattr(Base.g_module, name, obj)
	for k in [dist, distclean, distcheck]:
		set_def(k)
	# add dummy init and shutdown functions if they're not defined
	if not 'init' in Base.g_module.__dict__:
		Base.g_module.init = Utils.nada
	if not 'shutdown' in Base.g_module.__dict__:
		Base.g_module.shutdown = Utils.nada
	if not 'set_options' in Base.g_module.__dict__:
		Base.g_module.set_options = Utils.nada

def parse_options():
	opt = Options.OptionsContext().execute()

	if not Options.commands:
		Options.commands = ['build']

	if 'install' in sys.argv or 'uninstall' in sys.argv:
		if Options.options.destdir:
			Options.options.destdir = os.path.abspath(os.path.expanduser(Options.options.destdir))

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
	global current_command
	current_command = cmd_name
	Base.create_context(cmd_name).execute()

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

def distclean(ctx=None):
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
				shutil.rmtree(proj[BLDDIR])
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

