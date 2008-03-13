#! /usr/bin/env python
# encoding: utf-8

"""MacOSX related tools

To compile an executable into a Mac application bundle, set its 'mac_app' attribute
to a True value:

obj.mac_app = True
"""

import ccroot, cc, cpp
import Object, Action
import os
import shutil

from Params import error, debug, fatal, warning

def create_task_macapp(self):
	if self.m_type == 'program':
	    if self.link_task is not None:
    		apptask = self.create_task('macapp', self.env)
    		apptask.set_inputs(self.link_task.m_outputs)
    		apptask.set_outputs(self.link_task.m_outputs[0].change_ext('.app'))
    		self.m_apptask = apptask
    
def apply_link_osx(self):
	# Use env['MACAPP'] to force *all* executables to be transformed into
	# Mac applications, per Thomas Nagy.
	# Or use obj.mac_app = True to build specific targets as Mac apps.
	if self.env['MACAPP'] or getattr(self, 'mac_app', False):
	    create_task_macapp(self)
Object.gen_hook(apply_link_osx)
Object.declare_order("apply_link", "apply_link_osx")
if "apply_link_osx" not in cc.CC_METHS:
    cc.CC_METHS.append("apply_link_osx")
if "apply_link_osx" not in cpp.CXX_METHS:
    cpp.CXX_METHS.append("apply_link_osx")


app_dirs = ['Contents', os.path.join('Contents','MacOS'), os.path.join('Contents','Resources')]

app_info = '''
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist SYSTEM "file://localhost/System/Library/DTDs/PropertyList.dtd">
<plist version="0.9">
<dict>
	<key>CFBundlePackageType</key>
	<string>APPL</string>
	<key>CFBundleGetInfoString</key>
	<string>Created by waf</string>
	<key>CFBundleSignature</key>
	<string>????</string>
	<key>NOTE</key>
	<string>Do not change this file, it will be overwritten by waf.</string>
'''
app_info_foot = '''
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
		f.write(app_info)
		f.write("\t<key>CFBundleExecutable</key>\n\t<string>%s</string>\n" % os.path.basename(srcprg))
		f.write(app_info_foot)
		f.close()

		i += 1

	return 0

x = Action.Action('macapp', vars=[], func=app_build)
x.prio = 300

