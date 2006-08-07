#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, os.path, types, sys, imp
import Build, Params, Utils, Options, Configure, Environment, DirWatch
from Params import debug, error, trace, fatal

g_inroot     = 1
g_dirwatch   = None
g_daemonlock = 0

# each script calls add_subdir
def add_subdir(dir, bld):
	global g_inroot
	if g_inroot:
		node = bld.ensure_node_from_lst(bld.m_curdirnode, dir.split('/'))
		bld.m_subdirs.append( [node, bld.m_curdirnode] )

		if not node:
			error("grave error in add_subdir, subdir not found for "+str(dir))
			#print bld.m_curdirnode
			bld.m_curdirnode.debug()
			sys.exit(1)
		return

	restore = bld.m_curdirnode
	#if restore is None:
	#	error("error in subdir( "+dir)
	#	return

	bld.m_curdirnode = bld.ensure_node_from_lst(bld.m_curdirnode, dir.split('/'))
	if bld.m_curdirnode is None:
		error("subdir not found ("+dir+"), restore is "+str(restore))
		sys.exit(1)

	bld.m_subdirs.append(  [bld.m_curdirnode, restore]    )

def callBack(idxName, pathName, event):
	#print "idxName=%s, Path=%s, Event=%s "%(idxName, pathName, event)

	# check the daemon lock state
	global g_daemonlock
	if g_daemonlock: return
	g_daemonlock = 1

	# Utils.reset cleans up existing variables (at least, this is the intent)
	Utils.reset()

	# start another main function
	Main()

	# release the daemon lock
	g_daemonlock = 0

def startDaemon():
	# start a new directory watcher, if it does not exist already
	# else, return immediately
	global g_dirwatch
	if not g_dirwatch:
		g_dirwatch = DirWatch.DirectoryWatcher()
		#print "daemon"

		m_dirs=[]
		for nodeDir in Params.g_build.m_srcnode.m_dirs:
			tmpstr = "%s" %nodeDir
			tmpstr = "%s" %(tmpstr[3:])[:-1]
			m_dirs.append(tmpstr)
			#print "DirList : ", m_dirs

		g_dirwatch.addDirWatch("tmp Test", callBack, m_dirs)

		# infinite loop, no need to exit except on ctrl+c
		g_dirwatch.loop()

def load_envs():
	cachedir = Params.g_cachedir
	try:
		lst = os.listdir(cachedir)
	except:
		fatal('The project was not configured: run "waf configure" first!')

	if not lst: raise "file not found"
	for file in lst:
		env = Environment.Environment()
		ret = env.load(os.path.join(cachedir, file))
		name = file.split('.')[0]

		if not ret:
			print "could not load env ", name
			continue
		Params.g_build.m_allenvs[name] = env
		try:
			env.setup(env['tools'])
		except:
			print "loading failed:", file
			raise

def Main():
	# configure the project
	from Common import install_files, install_as
	if Params.g_commands['configure']:
		bld = Build.Build()
		try:
			try: srcdir = Params.g_options.srcdir
			except: pass
			if not srcdir: srcdir = Utils.g_module.srcdir

			try: blddir = Params.g_options.blddir
			except: pass
			if not blddir: blddir = Utils.g_module.blddir
	
			Params.g_cachedir = blddir+os.sep+'_cache_'

		except AttributeError:
			msg = "The attributes srcdir or blddir are missing from wscript\n[%s]\n * make sure such a function is defined\n * run configure from the root of the project\n * use waf configure --srcdir=xxx --blddir=yyy"
			fatal(msg % os.path.abspath('.'))
		except OSError:
			pass
		except KeyError:
			pass

		bld.load_dirs(srcdir, blddir)

		conf = Configure.Configure(srcdir=srcdir, blddir=blddir)
		conf.sub_config('')
		conf.store(bld)
		conf.cleanup()

		# this will write a configure lock so that subsequent run will
		# consider the current path as the root directory
		# to remove: use 'waf distclean'
		file = open('.lock-wscript', 'w')
		file.write(blddir)
		file.write('\n')
		file.write(srcdir)
		file.close()

		sys.exit(0)

	# compile the project and/or install the files
	#bld = private_setup_build()
	bld = Build.Build()
	try:
		file = open('.lock-wscript', 'r')
		blddir = file.readline().strip()
		srcdir = file.readline().strip()
		file.close()
	except:
		#raise
		fatal("Configuration loading failed - re-run waf configure (.lock-wscript cannot be read)")

	Params.g_cachedir = blddir+os.sep+'_cache_'

	# init the Build object.
	try:
		bld.load_dirs(srcdir, blddir)
	except:
		#fatal("bld.load_dirs failed")
		raise

	try:
		load_envs()
	except:
		raise
		fatal("Configuration loading failed\n" \
			"-> This is due most of the time because the project is not configured \n" \
			"-> Run 'waf configure' or run 'waf distclean' and configure once again")

	#bld.dump()

	global g_inroot
	g_inroot=1
	Utils.g_module.build(bld)
	g_inroot=0

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
		bld.rescan(bld.m_curdirnode)

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

	#bld.dump()

	# compile
	if Params.g_commands['build'] or Params.g_commands['install']:
		try:
			ret = bld.compile()
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

	# daemon here
	if Params.g_options.daemon and Params.g_commands['build']:
		startDaemon()
		return

	# shutdown
	try:
		Utils.g_module.shutdown()
	except:
		#raise
		pass

# dist target - should be portable
def Dist(appname, version):
	import shutil, tarfile

	# Our temporary folder where to put our files
	TMPFOLDER=appname+'-'+version

	# Remove an old package directory
	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)

	# Copy everything into the new folder
	shutil.copytree('.', TMPFOLDER)

	# Enter into it and remove unnecessary files
	os.chdir(TMPFOLDER)
	for (root, dirs, filenames) in os.walk('.'):
		clean_dirs = []
		for d in dirs:
			if d in ['CVS', 'cache', '_build_', '{arch}']:
				shutil.rmtree(os.path.join(root,d))
			elif d.startswith('.'):
				shutil.rmtree(os.path.join(root,d))
			else:
				clean_dirs += d
		dirs = clean_dirs
					
		to_remove = False
		for f in list(filenames):
			if f.startswith('.'): to_remove = True
			elif f.endswith('~'): to_remove = True
			elif f.endswith('.pyc'): to_remove = True
			elif f.endswith('.bak'): to_remove = True
			elif f.endswith('.orig'): to_remove = True
			elif f in ['config.log']: to_remove = True
			elif f.endswith('.tar.bz2') and not f.endswith('miniwaf.tar.bz2'): to_remove = True
			elif f.endswith('.zip'): to_remove = True
			
			if to_remove:
				os.remove(os.path.join(root, f))
				to_remove = False

	# go back to the root directory
	os.chdir('..')
	
	tar = tarfile.open(TMPFOLDER+'.tar.bz2','w:bz2')
	tar.add(TMPFOLDER)
	tar.close()
	print 'Your archive is ready -> '+TMPFOLDER+'.tar.bz2'

	if os.path.exists(TMPFOLDER): shutil.rmtree(TMPFOLDER)

	sys.exit(0)

# distclean target - should be portable too
def DistClean():
	import os, shutil, types
	import Build

	#print "Executing distclean in ", os.path.abspath('.')

	# remove the distclean folders (may not exist)
	try:
		li=Utils.g_module.distclean
		if not type(li) is types.ListType:
			li = li.split()
		for dir in li:
			if not dir: continue
			try: shutil.rmtree(os.path.abspath(dir))
			except: pass
	except:
		pass

	# remove the builddir declared
	try: shutil.rmtree(os.path.abspath(Utils.g_module.blddir))
	except: pass

	# remove the temporary files
	for (root, dirs, filenames) in os.walk('.'):
		to_remove = False
		for f in list(filenames):
			if f=='.lock-wscript':
				# removes a lock, and the builddir indicated
				to_remove = True
				file = open(os.path.join(root, f), 'r')
				dirname = file.readline().strip()
				file.close()
				try: shutil.rmtree(os.path.join(root, dirname))
				except: pass
			elif f.endswith('~'): to_remove = True
			elif f.endswith('.pyc'): to_remove = True
			elif f.startswith('.dblite'): to_remove = True
			
			if to_remove:
				#print "removing ",os.path.join(root, f)
				os.remove(os.path.join(root, f))
				to_remove = False
	sys.exit(0)

