#!/usr/bin/env python
# encoding: utf-8
# Thomas Zellman, 2009

"""
Java JNI support

TODO - we will probably want to add JNI tools here as well (javah, etc.)
"""

import os
import Utils, Options

def set_options(opt):
    opt.tool_options('javaw')
    opt.tool_options('compiler_cc')


def detect(conf):
	conf.check_tool('javaw')
	conf.check_tool('compiler_cc')
		
	#if you plan on building JNI code, you'll want the jvm
	javaHome = conf.env['JAVA_HOME'][0]
	incPath = os.path.join(javaHome, 'include')
    #also add the platform-specific dir
	incPath = [incPath, os.path.join(incPath, Options.platform)]
	#TODO there might be some more checks to make here..
	if Options.platform.find('sunos') >= 0:
		incPath.append(os.path.join(incPath[0], 'solaris'))
    
	if conf.check_cc(header_name="jni.h", define_name='HAVE_JNI_H',
					includes=incPath):
		conf.env.append_value('CPPPATH_JAVA', incPath)
	else:
		conf.fatal('unable to find jni.h')
    
	jrePath = os.path.join(javaHome, 'jre')
	jreLibPath = os.path.join(jrePath, 'lib')
	libPaths = [jreLibPath]
	if Options.platform == 'linux':
		libPaths.append(os.path.join(jreLibPath, 'i386', 'client'))
	conf.env.append_value('LIBPATH', libPaths)
	if conf.check_cc(lib='jvm', env=conf.env):
		conf.env.append_value('LIB_JAVA', 'jvm')
		conf.env.append_value('LIBPATH_JAVA', libPaths)
	else:
		conf.fatal('unable to find jvm lib')

