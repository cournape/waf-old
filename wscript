#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005, 2006 (ita)

VERSION='0.8.3pre1'
APPNAME='waf'

demos = ['cpp', 'qt4', 'tex', 'ocaml', 'kde3', 'adv', 'cc', 'idl', 'docbook']

import Params, os, sys

# this function is called before any other for parsing the command-line
def set_options(opt):
	opt.add_option('--prepare', action='store_true', default=False,
		help='prepare the demo projects RUN ME PLEASE', dest='prepare')
	opt.add_option('--cleanup', action='store_true', default=False,
		help='cleanup the demo after use (removes project files)', dest='cleanup')
	opt.add_option('--make-archive', action='store_true', default=False,
		help='create a waf archive suitable for custom projects', dest='arch')

# the init function is called right after the command-line arguments are parsed
def init():
	if Params.g_options.prepare:
		print "preparing the cpp demo (run ./waf --cleanup to remove)"
		print "cd to demos/cpp/ and execute waf there (there other demos, not all are ready)"
		for d in demos:
			ret = os.popen("if test ! -L ./demos/%s/wafadmin; then ln -sf ../../wafadmin ./demos/%s/wafadmin && cp configure setenv.bat waf.py ./demos/%s/; fi" % (d,d,d))
		sys.exit(0)
	elif Params.g_options.cleanup:
		print "cleaning up the demo folders"
		for d in demos:
			ret = os.popen("rm -f ./demos/%s/waf.py ./demos/%s/setenv.bat ./demos/%s/configure ./demos/%s/wafadmin" % (d,d,d))
		sys.exit(0)
	elif Params.g_options.arch:
		print "preparing an archive of waf for use in custom projects"
		import Runner
		ex = Runner.exec_command
		mw = 'miniwaf-'+VERSION
		cmd = [
		"rm -rf %s/ %s.tar.bz2 && mkdir -p %s/wafadmin/Tools/" % (mw,mw,mw),
		"cp waf.py configure setenv.bat %s/ && cp wafadmin/*.py %s/wafadmin/" % (mw,mw),
		"cp wafadmin/Tools/*.py %s/wafadmin/Tools/" % mw,
		"rm -f %s/wafadmin/Test.py" % mw,
		#"pushd %s/wafadmin/ && perl -pi -e 's/^\s*#[^!].*$//' *.py && popd" % mw,
		#"pushd %s/wafadmin/ && perl -pi -e 's/^$//' *.py && popd" % mw,
		#"pushd %s/wafadmin/Tools && perl -pi -e 's/^\s*#[^!].*$//' *.py && popd" % mw,
		#"pushd %s/wafadmin/Tools && perl -pi -e 's/^$//' *.py && popd" % mw,
		"pushd %s && tar cjvf ../%s.tar.bz2 waf.py setenv.bat configure wafadmin" % (mw, mw),
		"rm -rf %s/" % mw,
		]

		for i in cmd:
			ret = ex(i)
			if ret:
				print "an error occured ",i
				sys.exit(0)
		print "your archive is ready"
		sys.exit(0)
	else:
		print "run 'waf --help' to know more about allowed commands !"
		sys.exit(0)

# provided as an example
def shutdown():
	pass


