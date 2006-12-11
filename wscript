#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005, 2006 (ita)

VERSION="1.0.2"
APPNAME='waf'

demos = ['cpp', 'qt4', 'tex', 'ocaml', 'kde3', 'adv', 'cc', 'idl', 'docbook', 'xmlwaf', 'gnome']

import Params, os, sys, base64, shutil

# this function is called before any other for parsing the command-line
def set_options(opt):

	# generate waf
	opt.add_option('--make-waf', action='store_true', default=False,
		help='creates the waf script', dest='waf')

	# ita: i suggest using waf directly, installing is useless but some people cannot live without it
	opt.add_option('--install', default=False,
		help='install waf on the system', action='store_true', dest='install')
	opt.add_option('--uninstall', default=False,
		help='uninstall waf from the system', action='store_true', dest='uninstall')

	# those ones are not too interesting
	opt.add_option('--set-version', default='',
		help='set the version number for waf releases (for the maintainer)', dest='setver')

def encodeAscii85(s):
	out=[]
	app=out.append
	v=[(0,16777216L),(1,65536),(2,256),(3,1)]
	cnt,r = divmod(len(s),4)
	stop=4*cnt
	p1,p2=s[0:stop],s[stop:]
	for i in range(cnt):
		offset=i*4
		num=0
		for (j,mul) in v: num+=mul*ord(p1[offset+j])
		if num==0: out.append('z')
		else:
			x,e=divmod(num,85)
			x,d=divmod(x,85)
			x,c=divmod(x,85)
			a,b=divmod(x,85)
			app(chr(a+33)+chr(b+33)+chr(c+33)+chr(d+33)+chr(e+33))
	if r>0:
		while len(p2)<4: p2=p2+'\x00'
		num=0
		for (j,mul) in v: num+=mul*ord(p2[j])
		x,e=divmod(num,85)
		x,d=divmod(x,85)
		x,c=divmod(x,85)
		a,b=divmod(x,85)
		end=chr(a+33)+chr(b+33)+chr(c+33)+chr(d+33)+chr(e+33)
		app(end[0:1+r])
	return ''.join(out)

def create_waf():
	print "preparing waf"
	mw = 'tmp-waf-'+VERSION

	import tarfile, re

	#open a file as tar.bz2 for writing
	tar = tarfile.open('%s.tar.bz2' % mw, "w:bz2")
	tarFiles=[]
	#regexpr for python files
	pyFileExp = re.compile(".*\.py$")

	# set the revision in the files to avoid version mismatch
	try:
		rev = os.popen("svnversion . TODO").read().strip()
		os.popen("""perl -pi -e 's/^REVISION=(.*)?$/REVISION="%s"/' waf-light""" % rev).close()
		os.popen("""perl -pi -e 's/^REVISION=(.*)?$/REVISION="%s"/' wafadmin/Params.py""" % rev).close()
	except:
		pass

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


	file = open('waf-light', 'rb')
	code1 = file.read()
	file.close()

	# revert the files to normal
	try:
		os.popen("""perl -pi -e 's/^REVISION=(.*)?$/REVISION="x"/' waf-light""").close()
		os.popen("""perl -pi -e 's/^REVISION=(.*)?$/REVISION="x"/' wafadmin/Params.py""").close()
	except:
		pass

	file = open('%s.tar.bz2' % mw, 'rb')
	cnt = file.read()
	file.close()
	code2 = encodeAscii85(cnt)
	if sys.platform == 'win32':
		file = open('waf.bat', 'wb')
		file.write('@python -x "%~f0" %* & exit /b\n')
	else:
		file = open('waf', 'wb')
	file.write(code1)
	file.write('# ===>BEGIN WOOF<===\n')
	file.write('#')
	file.write(code2)
	file.write('\n')
	file.write('# ===>END WOOF<===\n')
	file.close()

	if sys.platform != 'win32':
		os.chmod('waf', 0755)
	os.unlink('%s.tar.bz2' % mw)

def install_waf():
	print "installing waf on the system"

	import shutil, re
	if sys.platform == 'win32':
		print "installing waf on windows is not possible yet"
		sys.exit(0)

	prefix      = Params.g_options.prefix
	binpath     = os.path.join(prefix, 'bin%swaf' % os.sep)
	wafadmindir = os.path.join(prefix, 'lib%swaf-%s%swafadmin%s' % (os.sep, VERSION, os.sep, os.sep))
	toolsdir    = os.path.join(wafadmindir, 'Tools' + os.sep)

	try: os.makedirs(os.path.join(prefix, 'bin'))
	except: pass

	try: os.makedirs(toolsdir)
	except: pass

	try:
		pyFileExp = re.compile(".*\.py$")
		wafadminFiles = os.listdir('wafadmin')
		wafadminFiles = filter (lambda s: pyFileExp.match(s), wafadminFiles)
		for pyFile in wafadminFiles:
			if pyFile == "Test.py": continue
			shutil.copy2(os.path.join('wafadmin', pyFile), os.path.join(wafadmindir, pyFile))
		tooldir = 'wafadmin'+os.sep+'Tools'
		wafadminFiles = os.listdir(tooldir)
		wafadminFiles = filter (lambda s: pyFileExp.match(s), wafadminFiles)
		for pyFile in wafadminFiles:
			if pyFile == "Test.py": continue
			shutil.copy2(os.path.join(tooldir, pyFile), os.path.join(toolsdir, pyFile))

		shutil.copy2('waf', os.path.join(binpath))
	except:
		print "->>> installation failed: cannot write to %s <<<-" % prefix
		sys.exit(1)
	print "waf is now installed in %s [%s, %s]" % (prefix, wafadmindir, binpath)
	if prefix != '/usr/local/':
		print "WARNING: make sure to always set WAFDIR to %s and PATH to %sbin:$PATH" % (prefix, prefix)

def uninstall_waf():
	print "uninstalling waf from the system"
	prefix  = Params.g_options.prefix
	binpath = os.path.join(prefix, 'bin%swaf' % os.sep)
	wafdir  = os.path.join(prefix, 'lib%swaf-%s' % (os.sep, VERSION))
	try:
		shutil.rmtree(wafdir)
	except:
		pass
	try:
		os.unlink(binpath)
	except:
		pass

	try:
		os.stat(wafdir)
		print 'WARNING: the waf directory %s could not be removed' % wafdir
	except:
		pass

# the init function is called right after the command-line arguments are parsed
def init():
	if Params.g_options.setver: # maintainer only (ita)
		ver = Params.g_options.setver
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' wscript""" % ver).close()
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' waf-light""" % ver).close()
		os.popen("""perl -pi -e 's/^g_version(.*)?$/g_version="%s"/' wafadmin/Params.py""" % ver).close()
		sys.exit(0)
	elif Params.g_options.install:
		if len(sys.argv[0]) > 6 and sys.argv[0][-6:]=='-light': create_waf()
		install_waf()
		sys.exit(0)
	elif Params.g_options.uninstall:
		uninstall_waf()
		sys.exit(0)
	elif Params.g_options.waf:
		create_waf()
		sys.exit(0)
	else:
		print "run 'waf --help' to know more about allowed commands !"
		sys.exit(0)

# provided as an example
def shutdown():
	pass


