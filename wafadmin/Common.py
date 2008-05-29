#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
Important functions: install_files, install_as, symlink_as (destdir is taken into account)
if the variable is not set (eval to false), installation is cancelled
if the variable is set but it does not exist, it assumes an absolute path was given
"""

import os, types, shutil, glob
import Params, Utils
from Params import error, fatal
from Constants import *

class InstallError(Exception):
	pass

def check_dir(dir):
	#print "check dir ", dir
	try:
		os.stat(dir)
	except OSError:
		try:
			os.makedirs(dir)
		except OSError:
			fatal("Cannot create folder " + dir)

def do_install(src, tgt, chmod=0644):
	"""returns true if the file was effectively installed or uninstalled, false otherwise"""
	if Params.g_commands['install']:
		# check if the file is already there to avoid a copy
		_do_install = True
		if not Params.g_options.force:
			try:
				t1 = os.stat(tgt).st_mtime
				t2 = os.stat(src).st_mtime
				if t1 >= t2: _do_install = False
			except OSError:
				_do_install = True

		if _do_install:
			srclbl = src
			try:
				srclbl = src.replace(Params.g_build.m_bldnode.abspath(None)+os.sep, '')
				srclbl = src.replace(Params.g_build.m_srcnode.abspath(None)+os.sep, '')
			except OSError:
				pass
			print "* installing %s as %s" % (srclbl, tgt)

			# followig is for shared libs and stale inodes
			try: os.remove(tgt)
			except OSError: pass
			try:
				shutil.copy2(src, tgt)
				os.chmod(tgt, chmod)
			except IOError:
				try:
					os.stat(src)
				except IOError:
					error('file %s does not exist' % str(src))
				fatal('Could not install the file %s' % str(tgt))
		return _do_install
	elif Params.g_commands['uninstall']:
		print "* uninstalling %s" % tgt

		Params.g_build.m_uninstall.append(tgt)

		try: os.remove(tgt)
		except OSError: pass
		return True

def path_install(var, subdir, env=None):
	bld = Params.g_build
	if not env: env = Params.g_build.env()
	destpath = env[var]
	if not destpath:
		error("Installing: to set a destination folder use env['%s']" % (var))
		destpath = var
	destdir = env.get_destdir()
	if destdir: destpath = os.path.join(destdir, destpath.lstrip(os.sep))
	if subdir: destpath = os.path.join(destpath, subdir.lstrip(os.sep))

	return destpath

def install_files(var, subdir, files, env=None, chmod=0644):
	if not Params.g_install: return []
	if not var: return []

	bld = Params.g_build

	if not env: env = bld.env()
	destpath = env[var]
	if not destpath: destpath = var # absolute paths

	node = bld.path
	if type(files) is types.StringType:
		if '*' in files:
			gl = node.abspath()+os.sep+files
			lst = glob.glob(gl)
		else:
			lst = files.split()
	else: lst = files

	destdir = env.get_destdir()
	if destdir: destpath = os.path.join(destdir, destpath.lstrip(os.sep))
	if subdir: destpath = os.path.join(destpath, subdir.lstrip(os.sep))

	check_dir(destpath)

	# copy the files to the final destination
	installed_files = []
	for filename in lst:
		if not os.path.isabs(filename):
			alst = Utils.split_path(filename)
			filenode = node.find_resource_lst(alst)
			if filenode is None:
				Params.fatal("Unable to install the file `%s': not found in %s" % (filename, node))

			file     = filenode.abspath(env)
			destfile = os.path.join(destpath, filenode.m_name)
		else:
			file     = filename
			alst     = Utils.split_path(filename)
			destfile = os.path.join(destpath, alst[-1])

		if do_install(file, destfile, chmod=chmod):
			installed_files.append(destfile)
	return installed_files

def install_as(var, destfile, srcfile, env=None, chmod=0644):
	"""returns True if the file was effectively installed, False otherwise"""
	if not Params.g_install: return False
	if not var: return False

	bld = Params.g_build
	if not env: env = Params.g_build.env()
	node = bld.path

	tgt = env[var]
	if not tgt: tgt = var # absolute paths for example

	destdir = env.get_destdir()
	if destdir: tgt = os.path.join(destdir, tgt.lstrip(os.sep))
	tgt = os.path.join(tgt, destfile.lstrip(os.sep))

	dir, name = os.path.split(tgt)
	check_dir(dir)

	# the source path
	if not os.path.isabs(srcfile):
		alst = Utils.split_path(srcfile)
		filenode = node.find_resource_lst(alst)
		src = filenode.abspath(env)
	else:
		src = srcfile

	return do_install(src, tgt, chmod=chmod)

def symlink_as(var, src, dest, env=None):
	if not Params.g_install: return
	if not var: return

	bld = Params.g_build
	if not env: env=Params.g_build.env()
	node = bld.path

	tgt = env[var]
	if not tgt: tgt = var

	destdir = env.get_destdir()
	if destdir: tgt = os.path.join(destdir, tgt.lstrip(os.sep))
	tgt = os.path.join(tgt, dest.lstrip(os.sep))

	dir, name = os.path.split(tgt)
	check_dir(dir)

	if Params.g_commands['install']:
		try:
			if not os.path.islink(tgt) or os.readlink(tgt) != src:
				print "* symlink %s (-> %s)" % (tgt, src)
				os.symlink(src, tgt)
			return 0
		except OSError:
			return 1
	elif Params.g_commands['uninstall']:
		try:
			print "* removing %s" % (tgt)
			os.remove(tgt)
			return 0
		except OSError:
			return 1

