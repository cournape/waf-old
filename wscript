#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005, 2006 (ita)

VERSION="0.8.6b"
APPNAME='waf'

demos = ['cpp', 'qt4', 'tex', 'ocaml', 'kde3', 'adv', 'cc', 'idl', 'docbook', 'xmlwaf', 'gnome']

import Params, os, sys

# this function is called before any other for parsing the command-line
def set_options(opt):
	opt.add_option('--prepare', action='store_true', default=False,
		help='prepare the demo projects RUN ME PLEASE', dest='prepare')
	opt.add_option('--cleanup', action='store_true', default=False,
		help='cleanup the demo after use (removes project files)', dest='cleanup')
	opt.add_option('--make-archive', action='store_true', default=False,
		help='create a waf archive suitable for custom projects', dest='arch')
	opt.add_option('--set-version', default='',
		help='set the version number for waf releases (for the maintainer)', dest='setver')
	opt.add_option('--install', default=False,
		help='install waf on the system', action='store_true', dest='instwaf')

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
			ret = os.popen("rm -f ./demos/%s/waf.py ./demos/%s/setenv.bat ./demos/%s/configure ./demos/%s/wafadmin" % (d,d,d,d))
		sys.exit(0)
	elif Params.g_options.arch:
		print "preparing an archive of waf for use in custom projects"
		mw = 'miniwaf-'+VERSION

		import tarfile, re

		#open a file as tar.bz2 for writing
		tar = tarfile.open('%s.tar.bz2' % mw, "w:bz2")
		tarFiles=['waf.py', 'configure', 'setenv.bat']
		#regexpr for python files
		pyFileExp = re.compile(".*\.py$")

		wafadminFiles = os.listdir('wafadmin')
		#filter all files out that do not match pyFileExp
		wafadminFiles = filter (lambda s: pyFileExp.match(s), wafadminFiles)
		for pyFile in wafadminFiles:
			if pyFile == "Test.py": continue
			#add the dir to the file and append to tarFiles
			tarFiles.append(os.path.join('wafadmin', pyFile))
		    
		wafadTolFiles = os.listdir(os.path.join('wafadmin', 'Tools'))
		wafadTolFiles = filter (lambda s: pyFileExp.match(s), wafadTolFiles)
		for pyFile in wafadTolFiles:
			tarFiles.append(os.path.join('wafadmin', 'Tools', pyFile))
		    
		for tarThisFile in tarFiles:
			tar.add(tarThisFile)
		tar.close()
		
		print "your archive is ready: %s.tar.bz2" % mw
		sys.exit(0)
	elif Params.g_options.setver: # maintainer only (ita)
		ver = Params.g_options.setver
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' wscript""" % ver).close()
		os.popen("""perl -pi -e 's/^g_version(.*)?$/g_version="%s"/' wafadmin/Params.py""" % ver).close()
		sys.exit(0)
	elif Params.g_options.instwaf:
		print "installing waf on the system"

		import shutil, re
		if sys.platform == 'win32':
			print "installing waf on windows is not possible yet"
			sys.exit(0)

		try:
			os.makedirs('/usr/local/wafadmin/Tools/')
		except:
			pass

		try:
			pyFileExp = re.compile(".*\.py$")
			wafadminFiles = os.listdir('wafadmin')
			wafadminFiles = filter (lambda s: pyFileExp.match(s), wafadminFiles)
			for pyFile in wafadminFiles:
				if pyFile == "Test.py": continue
				shutil.copy2(os.path.join('wafadmin', pyFile), os.path.join('/usr/local/wafadmin/', pyFile))
			tooldir = 'wafadmin'+os.sep+'Tools'
			wafadminFiles = os.listdir(tooldir)
			wafadminFiles = filter (lambda s: pyFileExp.match(s), wafadminFiles)
			for pyFile in wafadminFiles:
				if pyFile == "Test.py": continue
				shutil.copy2(os.path.join(tooldir, pyFile), os.path.join('/usr/local/wafadmin/Tools', pyFile))

			shutil.copy2('waf.py', os.path.join('/usr/local/bin/waf'))
		except:
			print "installation failed: cannot write to /usr/local/"
			raise
			sys.exit(0)
		print "waf is now installed in /usr/local [/usr/local/bin/waf, /usr/local/wafadmin]"
		sys.exit(0)
	else:
		print "run 'waf --help' to know more about allowed commands !"
		sys.exit(0)

# provided as an example
def shutdown():
	pass


