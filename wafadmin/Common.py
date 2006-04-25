#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

# Stuff potentially useful for any project

import os, types, shutil
import Action, Params
from Params import debug, error, trace, fatal

class InstallError:
	pass

def check_dir(dir):
	#print "check dir ", dir
	try:    os.stat(dir)
	except: os.makedirs(dir)

def do_install(src, tgt):
	if Params.g_commands['install']:
		print "* installing %s as %s" % (src, tgt)
		try: shutil.copy2( src, tgt )
		except: raise InstallError
	elif Params.g_commands['uninstall']:
		print "* uninstalling %s" % tgt
		try: os.remove( tgt )
		except OSError: pass

def install_files(var, subdir, files, env=None):
	if (not Params.g_commands['install']) and (not Params.g_commands['uninstall']): return

	bld = Params.g_build
	if not env: env=Params.g_build.m_allenvs['default']
	node = bld.m_curdirnode

	if type(files) is types.ListType: lst=files
	else: lst = (' '+files).split()

	destpath = env[var]
	destdir = env['DESTDIR']
	if destdir: destpath = os.path.join(destdir, destpath.lstrip(os.sep))
	if subdir: destpath = os.path.join(destpath, subdir.lstrip(os.sep))

	check_dir(destpath)

	# copy the files to the final destination
	for filename in lst:
		name = filename

		try:
			lname = filename.split('/')
			name  = lname[len(lname)-1]
		except:
			pass

		file = os.path.join(node.abspath(), filename)
		destfile = os.path.join(destpath, name)
		do_install(file, destfile)

def install_as(var, destfile, srcfile, env=None):
	if (not Params.g_commands['install']) and (not Params.g_commands['uninstall']): return

	bld = Params.g_build
	if not env: env=Params.g_build.m_allenvs['default']
	node = bld.m_curdirnode

	tgt = env[var]
	destdir = env['DESTDIR']
	if destdir: tgt = os.path.join(destdir, tgt.lstrip(os.sep))
	tgt = os.path.join(tgt, destfile.lstrip(os.sep))

	dir, name = os.path.split(tgt)
	check_dir(dir)

	src = os.path.join(node.abspath(), srcfile.lstrip(os.sep))
	do_install(src, tgt)

def symlink_as(var, src, dest, env=None):
	if (not Params.g_commands['install']) and (not Params.g_commands['uninstall']): return

	bld = Params.g_build
	if not env: env=Params.g_build.m_allenvs['default']
	node = bld.m_curdirnode

	tgt = env[var]
	destdir = env['DESTDIR']
	if destdir: tgt = os.path.join(destdir, tgt.lstrip(os.sep))
	tgt = os.path.join(tgt, dest.lstrip(os.sep))

	dir, name = os.path.split(tgt)
	check_dir(dir)

	if Params.g_commands['install']:
		try:
			print "* symlink %s -> %s" % (src, tgt)
			os.symlink(src, tgt)
			return 0
		except:
			return 1
	elif Params.g_commands['uninstall']:
		try:
			print "* removing %s" % (tgt)
			os.remove(tgt)
			return 0
		except:
			return 1

