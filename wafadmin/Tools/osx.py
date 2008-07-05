#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy 2008

"""MacOSX related tools

To compile an executable into a Mac application bundle (a .app), set its 'mac_app' attribute
  obj.mac_app = True

To make a bundled shared library (a .bundle), set the 'mac_bundle' attribute:
  obj.mac_bundle = True
"""

import os, shutil, sys
import TaskGen, Task, Build
from TaskGen import taskgen, feature, after, before
from Logs import error, debug, fatal

@taskgen
def create_task_macapp(self):
	if self.type == 'program' and self.link_task:
		apptask = self.create_task('macapp', self.env)
		apptask.set_inputs(self.link_task.outputs)
		apptask.set_outputs(self.link_task.outputs[0].change_ext('.app'))
		self.apptask = apptask

@taskgen
@after('apply_link')
@feature('cc', 'cxx')
def apply_link_osx(self):
	"""Use env['MACAPP'] to force *all* executables to be transformed into Mac applications
	or use obj.mac_app = True to build specific targets as Mac apps"""
	if self.env['MACAPP'] or getattr(self, 'mac_app', False):
	    self.create_task_macapp()
		name = self.link_task.outputs[0].name
		if self.vnum: name = name.replace('.dylib', '.%s.dylib' % self.vnum)
		path = os.path.join(self.env['PREFIX'], lib, name)
		path = '-install_name %s' % path
		self.env.append_value('LINKFLAGS', path)

@taskgen
@before('apply_link')
@before('apply_lib_vars')
@feature('cc', 'cxx')
def apply_bundle(self):
	"""the uselib system cannot modify a few things, use env['MACBUNDLE'] to force all shlibs into mac bundles
	or use obj.mac_bundle = True for specific targets only"""
	if not 'shlib' in self.features: return
	if self.env['MACBUNDLE'] or getattr(self, 'mac_bundle', False):
		self.env['shlib_PATTERN'] = '%s.bundle'
		uselib = self.to_list(self.uselib)
		if not 'MACBUNDLE' in uselib: uselib.append('MACBUNDLE')

@taskgen
@after('apply_link')
@feature('cc', 'cxx')
def apply_bundle_remove_dynamiclib(self):
	if not 'shlib' in self.features: return
	if self.env['MACBUNDLE'] or getattr(self, 'mac_bundle', False):
		self.env["LINKFLAGS"].remove("-dynamiclib")
		self.env.append_value("LINKFLAGS", "-bundle")



app_dirs = ['Contents', os.path.join('Contents','MacOS'), os.path.join('Contents','Resources')]

app_info = '''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleGetInfoString</key>
	<string>Created by Waf</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>NOTE</key>
	<string>THIS IS A GENERATED FILE, DO NOT MODIFY</string>
	<key>CFBundleExecutable</key>
	<string>%s</string>
</dict>
</plist>
'''

def app_build(task):
	global app_dirs
	env = task.env

	i = 0
	for p in task.outputs:
		srcfile = p.srcpath(env)

		debug('osx: creating directories')
		try:
			os.mkdir(srcfile)
			[os.makedirs(os.path.join(srcfile, d)) for d in app_dirs]
		except (OSError, IOError):
			pass

		# copy the program to the contents dir
		srcprg = task.inputs[i].srcpath(env)
		dst = os.path.join(srcfile, 'Contents', 'MacOS')
		debug('osx: copy %s to %s' % (srcprg, dst))
		shutil.copy(srcprg, dst)

		# create info.plist
		debug('osx: generate Info.plist')
		# TODO:  Support custom info.plist contents.

		f = file(os.path.join(srcfile, "Contents", "Info.plist"), "w")
		f.write(app_info % os.path.basename(srcprg))
		f.close()

		i += 1

	return 0

def install_shlib(task):
	"""see http://code.google.com/p/waf/issues/detail?id=173"""
	nums = task.vnum.split('.')

	inst_var = task.inst_var
	inst_dir = task.inst_dir

	libname = task.outputs[0].name

	name3 = libname.replace('.dylib', '.%s.dylib' % task.vnum)
	name2 = libname.replace('.dylib', '.%s.dylib' % nums[0])
	name1 = libname

	filename = task.outputs[0].abspath(task.env)
	bld = Build.bld
	bld.install_as(inst_var, os.path.join(inst_dir, name3), filename, env=task.env)
	bld.symlink_as(inst_var, name3, os.path.join(inst_dir, name2))
	bld.symlink_as(inst_var, name3, os.path.join(inst_dir, name1))

@taskgen
@feature('osx')
@after('install_target_cshlib')
def install_target_osx_cshlib(self):
	if not Options.is_install: return
	if getattr(self, 'vnum', '') and sys.platform != 'win32':
		self.link_task.install = install_shlib

Task.task_type_from_func('macapp', vars=[], func=app_build, after="cxx_link cc_link ar_link_static")

