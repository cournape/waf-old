#! /usr/bin/env python
# encoding: utf-8

"""MacOSX related tools

To compile an executable into a Mac application bundle, set its 'mac_app' attribute
to a True value:

obj.mac_app = True
"""

import os, shutil
import Object, Action
from Object import taskgen, feature, after, before
from Params import error, debug, fatal, warning

@taskgen
def create_task_macapp(self):
	if self.m_type == 'program' and self.link_task:
		apptask = self.create_task('macapp', self.env)
		apptask.set_inputs(self.link_task.m_outputs)
		apptask.set_outputs(self.link_task.m_outputs[0].change_ext('.app'))
		self.m_apptask = apptask

@taskgen
@after('apply_link')
@feature('cc')
@feature('cxx')
def apply_link_osx(self):
	"""Use env['MACAPP'] to force *all* executables to be transformed into Mac applications
	or use obj.mac_app = True to build specific targets as Mac apps"""
	if self.env['MACAPP'] or getattr(self, 'mac_app', False):
	    self.create_task_macapp()

@taskgen
@before('apply_link')
@feature('osx_bundle')
def apply_bundle(self):
	"the uselib system cannot modify a few things"
	self.env['shlib_PATTERN'] = '%s.bundle'
	uselib = self.to_list(self.uselib)
	if not 'OSX' in uselib: uselib.append('OSX')

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
	env = task.env()

	i = 0
	for p in task.m_outputs:
		srcfile = p.srcpath(env)

		debug("creating directories")
		try:
			os.mkdir(srcfile)
			[os.makedirs(os.path.join(srcfile, d)) for d in app_dirs]
		except (OSError, IOError):
			pass

		# copy the program to the contents dir
		srcprg = task.m_inputs[i].srcpath(env)
		dst = os.path.join(srcfile, 'Contents', 'MacOS')
		debug("copy %s to %s" % (srcprg, dst))
		shutil.copy(srcprg, dst)

		# create info.plist
		debug("generate Info.plist")
		# TODO:  Support custom info.plist contents.

		f = file(os.path.join(srcfile, "Contents", "Info.plist"), "w")
		f.write(app_info % os.path.basename(srcprg))
		f.close()

		i += 1

	return 0

x = Action.Action('macapp', vars=[], func=app_build)
x.prio = 300

