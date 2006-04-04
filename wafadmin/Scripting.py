#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, os.path, types, sys, imp, cPickle
import Build, Params, Utils, Options, Configure, Environment
from Params import debug, error, trace, fatal

# each script calls add_subdir
def add_subdir(dir):
	if Params.g_inroot:
		#node = Params.g_curdirnode.find_node(dir.split('/'))
		node = Params.g_build.m_tree.ensure_node_from_lst(Params.g_curdirnode, dir.split('/'))
		Params.g_subdirs.append( [node, Params.g_curdirnode] )

		if not node:
			error("grave error in add_subdir, subdir not found for "+str(dir))
			#print Params.g_curdirnode
			Params.g_curdirnode.debug()
			sys.exit(1)
		return

	restore = Params.g_curdirnode
	#if dir is None:
	#	error("error in subdir( "+dir)
	#	return

	#Params.g_curdirnode = Params.g_curdirnode.find_node(dir.split('/'))
	Params.g_curdirnode = Params.g_build.m_tree.ensure_node_from_lst(Params.g_curdirnode, dir.split('/'))
	if Params.g_curdirnode is None:
		error("subdir not found ("+dir+"), restore is "+str(restore))
		sys.exit(1)

	Params.g_subdirs.append(  [Params.g_curdirnode, restore]    )

def private_setup_build(load=1):
	bld = Build.Build()
	try:
		Utils.g_module.setup_build(bld)
	except AttributeError:
		try:
			cachedir = Utils.g_module.cachedir
			bld.set_dirs(Utils.g_module.srcdir, Utils.g_module.blddir)
			#bld.set_default_env(os.path.join(Utils.g_module.cachedir, 'main.cache.py')) # TODO
			if not load: return bld
			lst = os.listdir(Utils.g_module.cachedir)
			for file in lst:
				env = Environment.Environment()
				ret = env.load(os.path.join(cachedir, file))
				name = file.split('.')[0]

				if not ret:
					print "could not load env ", name
					continue
				Params.g_envs[name] = env
				try:
					env.setup(env['tools'])
				except:
					print "exception 1"
					raise

			Params.g_default_env = Params.g_envs['default']

		except AttributeError:
			msg = "The attributes srcdir or builddir are missing from wscript\n[%s]\n * make sure such a function is defined\n * run configure from the root of the project"
			fatal(msg % os.path.abspath('.'))
		except OSError:
			pass
		except KeyError:
			pass
	return bld

def Main():
	from Object import createObj
	from Configure import sub_config, create_config
	from Common import install_files, install_as
	# configure the project
	if Params.g_commands['configure']:
		bld = private_setup_build(0)
		conf = Configure.Configure()
		conf.sub_config('')
		conf.store()

		# this will write a configure lock so that subsequent run will
		# consider the current path as the root directory
		# to remove: use 'waf distclean'
		file = open('.lock-wscript', 'w')
		file.write(Utils.g_module.blddir)
		file.close()

		sys.exit(0)

	# compile the project and/or install the files
	bld = private_setup_build()
	#bld.m_tree.dump()

	Params.g_inroot=1
	Utils.g_module.build(bld)
	Params.g_inroot=0

	while len(Params.g_subdirs)>0:
		# read scripts, saving the context everytime (Params.g_curdirnode)

		# cheap queue
		lst=Params.g_subdirs[0]
		Params.g_subdirs=Params.g_subdirs[1:]

		new=lst[0]
		old=lst[1]

		# take the new node position
		Params.g_curdirnode=new

		# try to open 'wscript_build' for execution
		# if unavailable, open the module wscript and call the build function from it
		try:
			file_path = os.path.join(new.abspath(), 'wscript_build')
			file = open(file_path, 'r')
			code = file.read()
			file.close()
			exec code
		except IOError:
			file_path = os.path.join(new.abspath(), 'wscript')
			module = Utils.load_module(file_path)
			module.build(bld)

		# restore the old node position
		Params.g_curdirnode=old

	#bld.m_tree.dump()

	# compile
	if Params.g_commands['make'] or Params.g_commands['install']:
	#if ('make' in Params.g_commands and Params.g_commands['make']) or Params.g_commands['install']:
		try:
			bld.compile()
		except:
			raise

	# install
	try:
		if Params.g_commands['install']:
			bld.install()
	finally:
		bld.cleanup()
		bld.store()

	# shutdown
	try:    Utils.g_module.shutdown()
	except: pass

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
			elif f.endswith('.tar.bz2'): to_remove = True
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
				dirname = file.read().strip()
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

