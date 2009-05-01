#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005, 2006, 2007, 2008

VERSION="1.5.6"
APPNAME='waf'
REVISION=''
srcdir='.'
blddir='build'

demos = ['cpp', 'qt4', 'tex', 'ocaml', 'kde3', 'adv', 'cc', 'idl', 'docbook', 'xmlwaf', 'gnome']
zip_types = ['bz2', 'gz']

# exclude these modules
forbidden = [x+'.py' for x in 'Test Weak'.split()]

#from tokenize import *
import tokenize

import os, sys, base64, shutil, re, random, StringIO, optparse, tempfile
import Utils, Options, Build
try: from hashlib import md5
except ImportError: from md5 import md5

pyFileExp = re.compile(".*\.py$")

print "------> Executing code from the top-level wscript <-----"

def init():
	if Options.options.setver: # maintainer only (ita)
		ver = Options.options.setver
		hexver = '0x'+ver.replace('.','0')
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' wscript""" % ver).close()
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' waf-light""" % ver).close()
		os.popen("""perl -pi -e 's/^WAFVERSION=(.*)?$/WAFVERSION="%s"/' wafadmin/Constants.py""" % ver).close()
		os.popen("""perl -pi -e 's/^HEXVERSION(.*)?$/HEXVERSION = %s/' wafadmin/Constants.py""" % hexver).close()

		try:
			p = os.popen("svnversion")
			rev =  p.read().strip()
			p.close()
			os.popen("""perl -pi -e 's/^WAFREVISION(.*)?$/WAFREVISION = "%s"/' wafadmin/Constants.py""" % rev).close()
		except:
			pass
	elif Options.options.waf:
		create_waf()
	elif Options.commands['check']:
		sys.path.insert(0,'')
		import test.Test
		test.Test.run_tests()
	else:
		return
	sys.exit(0)

# this function is called before any other for parsing the command-line
def set_options(opt):

	# generate waf
	opt.add_option('--make-waf', action='store_true', default=False,
		help='creates the waf script', dest='waf')

	opt.add_option('--zip-type', action='store', default='bz2',
		help='specify the zip type [Allowed values: %s]' % ' '.join(zip_types), dest='zip')

	opt.add_option('--make-batch', action='store_true', default=False,
		help='creates a convenience waf.bat file (done automatically on win32 systems)',
		dest='make_batch')

	opt.add_option('--yes', action='store_true', default=False,
		help=optparse.SUPPRESS_HELP,
		dest='yes')

	# those ones are not too interesting
	opt.add_option('--set-version', default='',
		help='sets the version number for waf releases (for the maintainer)', dest='setver')

	opt.add_option('--strip', action='store_true', default=True,
		help='shrinks waf (strip docstrings, saves 33kb)',
		dest='strip_comments')
	opt.add_option('--nostrip', action='store_false', help='no shrinking',
		dest='strip_comments')
	opt.tool_options('python')

def compute_revision():
	global REVISION

	def visit(arg, dirname, names):
		for pos, name in enumerate(names):
			if name[0] == '.' or name in ['_build_', 'build']:
				del names[pos]
			elif name.endswith('.py'):
				arg.append(os.path.join(dirname, name))
	sources = []
	os.path.walk('wafadmin', visit, sources)
	sources.sort()
	m = md5()
	for source in sources:
		f = file(source,'rb')
		readBytes = 100000
		while (readBytes):
			readString = f.read(readBytes)
			m.update(readString)
			readBytes = len(readString)
		f.close()
	REVISION = m.hexdigest()

#deco_re = re.compile('def\\s+([a-zA-Z_]+)\\(')
deco_re = re.compile('(def|class)\\s+(\w+)\\(.*')
def process_decorators(body):
	lst = body.split('\n')
	accu = []
	all_deco = []
	buf = [] # put the decorator lines
	for line in lst:
		if line.startswith('@'):
			buf.append(line[1:])
		elif buf:
			name = deco_re.sub('\\2', line)
			if not name:
				raise IOError, "decorator not followed by a function!"+line
			for x in buf:
				all_deco.append("%s(%s)" % (x, name))
			accu.append(line)
			buf = []
		else:
			accu.append(line)
	return "\n".join(accu+all_deco)

def process_imports(body):
	header = '#! /usr/bin/env python\n# encoding: utf-8'
	impo = ''
	deco = ''

	if body.find('set(') > -1:
		impo += 'import sys\nif sys.hexversion < 0x020400f0: from sets import Set as set'

	return "\n".join([header, impo, body, deco])

def process_tokens(tokens):
	accu = []
	prev = tokenize.NEWLINE

	accu_deco = []
	indent = 0
	line_buf = []

	for (type, token, start, end, line) in tokens:
		if type == tokenize.NEWLINE:
			if line_buf:
				accu.append(indent * '\t')
				ln = "".join(line_buf)
				if ln == 'if __name__=="__main__":': break
				#ln = ln.replace('\n', '')
				accu.append(ln)
				accu.append('\n')
				line_buf = []
				prev = tokenize.NEWLINE
		elif type == tokenize.INDENT:
			indent += 1
		elif type == tokenize.DEDENT:
			indent -= 1
		elif type == tokenize.NAME:
			if prev == tokenize.NAME or prev == tokenize.NUMBER: line_buf.append(' ')
			line_buf.append(token)
		elif type == tokenize.NUMBER:
			if prev == tokenize.NAME or prev == tokenize.NUMBER: line_buf.append(' ')
			line_buf.append(token)
		elif type == tokenize.STRING:
			if not line_buf and token.startswith('"'): pass
			else: line_buf.append(token)
		elif type == tokenize.COMMENT:
			pass
		elif type == tokenize.OP:
			line_buf.append(token)
		else:
			if token != "\n": line_buf.append(token)

		if token != '\n':
			prev = type

	body = "".join(accu)
	return body

def sfilter(path):
	f = open(path, "r")
	if Options.options.strip_comments:
		cnt = process_tokens(tokenize.generate_tokens(f.readline))
	else:
		cnt = f.read()
	f.close()

	cnt = process_decorators(cnt)
	cnt = process_imports(cnt)
	if path.endswith('Options.py') or path.endswith('Scripting.py'):
		cnt = cnt.replace('Utils.python_24_guard()', '')

	return (StringIO.StringIO(cnt), len(cnt), cnt)

def create_waf():
	print "-> preparing waf"
	mw = 'tmp-waf-'+VERSION

	import tarfile, re

	zipType = Options.options.zip.strip().lower()
	if zipType not in zip_types:
		zipType = zip_types[0]

	#open a file as tar.[extension] for writing
	tar = tarfile.open('%s.tar.%s' % (mw, zipType), "w:%s" % zipType)
	tarFiles=[]

	lst = os.listdir('wafadmin')
	files = [os.path.join('wafadmin', s) for s in lst if pyFileExp.match(s) and not s in forbidden]
	tooldir = os.path.join('wafadmin', 'Tools')
	lst = os.listdir(tooldir)
	files += [os.path.join(tooldir, s) for s in lst if pyFileExp.match(s) and not s in forbidden]
	for x in files:
		tarinfo = tar.gettarinfo(x, x)
		tarinfo.uid=tarinfo.gid=1000
		tarinfo.uname=tarinfo.gname="bozo"
		(code, size, cnt) = sfilter(x)
		tarinfo.size = size
		tar.addfile(tarinfo, code)
	tar.close()

	f = open('waf-light', 'rb')
	code1 = f.read()
	f.close()

	# now store the revision unique number in waf
	#compute_revision()
	#reg = re.compile('^REVISION=(.*)', re.M)
	#code1 = reg.sub(r'REVISION="%s"' % REVISION, code1)

	prefix = ''
	if Build.bld:
		prefix = Build.bld.env['PREFIX'] or ''

	reg = re.compile('^INSTALL=(.*)', re.M)
	code1 = reg.sub(r'INSTALL=%r' % prefix, code1)
	#change the tarfile extension in the waf script
	reg = re.compile('bz2', re.M)
	code1 = reg.sub(zipType, code1)

	f = open('%s.tar.%s' % (mw, zipType), 'rb')
	cnt = f.read()
	f.close()

	# the REVISION value is the md5 sum of the binary blob (facilitate audits)
	m = md5()
	m.update(cnt)
	REVISION = m.hexdigest()
	reg = re.compile('^REVISION=(.*)', re.M)
	code1 = reg.sub(r'REVISION="%s"' % REVISION, code1)

	def find_unused(kd, ch):
		for i in xrange(35, 125):
			for j in xrange(35, 125):
				if i==j: continue
				if i == 39 or j == 39: continue
				if i == 92 or j == 92: continue
				s = chr(i) + chr(j)
				if -1 == kd.find(s):
					return (kd.replace(ch, s), s)
		raise

	# The reverse order prevent collisions
	(cnt, C2) = find_unused(cnt, '\r')
	(cnt, C1) = find_unused(cnt, '\n')
	f = open('waf', 'wb')
	f.write(code1.replace("C1='x'", "C1='%s'" % C1).replace("C2='x'", "C2='%s'" % C2))
	f.write('#==>\n')
	f.write('#')
	f.write(cnt)
	f.write('\n')
	f.write('#<==\n')
	f.close()

	if sys.platform == 'win32' or Options.options.make_batch:
		f = open('waf.bat', 'wb')
		f.write('@python -x %~dp0waf %* & exit /b\n')
		f.close()

	if sys.platform != 'win32':
		os.chmod('waf', 0755)
	os.unlink('%s.tar.%s' % (mw, zipType))

def make_copy(inf, outf):
	(a, b, cnt) = sfilter(inf)
	f = open(outf, "wb")
	f.write(cnt)
	f.close()

def configure(conf):
	conf.check_tool('python')
	conf.check_python_version((2,4))


def build(bld):

	import shutil, re

	if Options.commands['install']:
		if sys.platform == 'win32':
			print "Installing Waf on Windows is not possible."
			sys.exit(0)

	if Options.is_install:
		compute_revision()

	if Options.commands['install']:
		val = Options.options.yes or (not sys.stdin.isatty() or raw_input("Installing Waf is discouraged. Proceed? [y/n]"))
		if val != True and val != "y": sys.exit(1)
		create_waf()

	dir = os.path.join('lib', 'waf-%s-%s' % (VERSION, REVISION), 'wafadmin')

	wafadmin = bld.new_task_gen('py')
	wafadmin.find_sources_in_dirs('wafadmin', exts=['.py'])
	wafadmin.install_path = os.path.join('${PREFIX}', dir)

	tools = bld.new_task_gen('py')
	tools.find_sources_in_dirs('wafadmin/Tools', exts=['.py'])
	tools.install_path = os.path.join('${PREFIX}', dir, 'Tools')

	bld.install_files('${PREFIX}/bin', 'waf', chmod=0755)

	#print "waf is now installed in %s [%s, %s]" % (prefix, wafadmindir, binpath)
	#print "make sure the PATH contains %s/bin:$PATH" % prefix


#def dist():
#	import Scripting
#	Scripting.g_dist_exts += ['Weak.py'] # shows how to exclude a file from dist
#	Scripting.Dist(APPNAME, VERSION)

