#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005, 2006 (ita)

"""
This script is not a good example:
 * it is complicated
 * it does not build anything, it just exits in the init method

Have a look at demos/cc/wscript instead
For configuration examples: demos/adv/wscript
For a project without subdirectory: demos/python/wscript
"""

VERSION="1.4.2"
APPNAME='waf'
REVISION=''
srcdir='.'
blddir='build'

demos = ['cpp', 'qt4', 'tex', 'ocaml', 'kde3', 'adv', 'cc', 'idl', 'docbook', 'xmlwaf', 'gnome']
zip_types = ['bz2', 'gz']

# exclude these modules
forbidden = [x+'.py' for x in 'Test Weak'.split()]

from tokenize import *

import os, sys, base64, shutil, re, random, StringIO, optparse, tempfile
import Params, Utils, Options
try: from hashlib import md5
except ImportError: from md5 import md5

pyFileExp = re.compile(".*\.py$")

print "------> Executing code from the top-level wscript <-----"

# this function is called before any other for parsing the command-line
def set_options(opt):

	# generate waf
	opt.add_option('--make-waf', action='store_true', default=False,
		help='creates the waf script', dest='waf')

	opt.add_option('--zip-type', action='store', default='bz2',
		help='specify the zip type [Allowed values: %s]' % ' '.join(zip_types), dest='zip')

	opt.add_option('--make-batch', action='store_true', default=False,
		help='creates a waf.bat file that calls the waf script. (this is done automatically on win32 systems)',
		dest='make_batch')

	opt.add_option('--yes', action='store_true', default=False,
		help=optparse.SUPPRESS_HELP,
		dest='yes')

	# those ones are not too interesting
	opt.add_option('--set-version', default='',
		help='set the version number for waf releases (for the maintainer)', dest='setver')

	opt.add_option('--strip', action='store_true', default=False,
		help='Shrink waf (strip docstrings, saves 33kb)',
		dest='strip_comments')

	default_prefix = os.environ.get('PREFIX')
	if not default_prefix:
		if sys.platform == 'win32': default_prefix = tempfile.gettempdir()
		else: default_prefix = '/usr/local/'

	try:
		opt.add_option('--prefix',
			help    = "installation prefix (configuration only) [Default: '%s']" % default_prefix,
			default = default_prefix,
			dest    = 'prefix')
	except:
		pass

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
	"modify the python 2.4 decorators"
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
	"add the python 2.3 fixes to the redistributable waf"
	header = '#! /usr/bin/env python\n# encoding: utf-8'
	impo = ''
	deco = ''

	if body.find('set(') > -1:
		impo += 'import sys\nif sys.hexversion < 0x020400f0: from sets import Set as set'

	return "\n".join([header, impo, body, deco])

def process_tokens(tokens):
	accu = []
	prev = NEWLINE

	accu_deco = []
	indent = 0
	line_buf = []

	for (type, token, start, end, line) in tokens:
		if type == NEWLINE:
			if line_buf:
				accu.append(indent * '\t')
				ln = "".join(line_buf)
				if ln == 'if __name__=="__main__":': break
				#ln = ln.replace('\n', '')
				accu.append(ln)
				accu.append('\n')
				line_buf = []
				prev = NEWLINE
		elif type == INDENT:
			indent += 1
		elif type == DEDENT:
			indent -= 1
		elif type == NAME:
			if prev == NAME or prev == NUMBER: line_buf.append(' ')
			line_buf.append(token)
		elif type == NUMBER:
			if prev == NAME or prev == NUMBER: line_buf.append(' ')
			line_buf.append(token)
		elif type == STRING:
			if not line_buf and token.startswith('"'): pass
			else: line_buf.append(token)
		elif type == COMMENT:
			pass
		elif type == OP:
			line_buf.append(token)
		else:
			if token != "\n": line_buf.append(token)

		if token != '\n':
			prev = type

	body = "".join(accu)
	return body

def sfilter(path):
	f = open(path, "r")
	if Params.g_options.strip_comments:
		cnt = process_tokens(generate_tokens(f.readline))
	else:
		cnt = f.read()
	f.close()

	cnt = process_decorators(cnt)
	cnt = process_imports(cnt)
	if path.endswith('Scripting.py'):
		cnt = cnt.replace('Utils.python_24_guard()', '')

	return (StringIO.StringIO(cnt), len(cnt), cnt)

def create_waf():
	print "-> preparing waf"
	mw = 'tmp-waf-'+VERSION

	import tarfile, re

	zipType = Params.g_options.zip.strip().lower()
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
	compute_revision()
	reg = re.compile('^REVISION=(.*)', re.M)
	code1 = reg.sub(r'REVISION="%s"' % REVISION, code1)

	prefix = Params.g_options.prefix
	# if the prefix is the default, let's be nice and be platform-independent
	# just in case the created waf is used on either windows or unix
	if prefix == Options.default_prefix:
		prefix = "sys.platform=='win32' and 'c:/temp' or '/usr/local'"
	else:
		prefix = '"%s"' % prefix #encase in quotes

	reg = re.compile('^INSTALL=(.*)', re.M)
	code1 = reg.sub(r'INSTALL=%s' % prefix, code1)
	#change the tarfile extension in the waf script
	reg = re.compile('bz2', re.M)
	code1 = reg.sub(zipType, code1)

	f = open('%s.tar.%s' % (mw, zipType), 'rb')
	cnt = f.read()
	f.close()
	code2 = encodeAscii85(cnt)
	f = open('waf', 'wb')
	f.write(code1)
	f.write('#==>\n')
	f.write('#')
	f.write(code2)
	f.write('\n')
	f.write('#<==\n')
	f.close()

	if sys.platform == 'win32' or Params.g_options.make_batch:
		f = open('waf.bat', 'wb')
		f.write('@python -x waf %* & exit /b\n')
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

	if Params.g_commands['install']:
		if sys.platform == 'win32':
			print "Installing Waf on Windows is not possible."
			sys.exit(0)

	if Params.g_commands['install']:
		val = Params.g_options.yes or (not sys.stdin.isatty() or raw_input("Installing Waf is discouraged. Proceed? [y/n]"))
		if val != True and val != "y": sys.exit(1)

		compute_revision()

		create_waf()

	wafadmin = bld.create_obj('py')
	wafadmin.find_sources_in_dirs('wafadmin', exts=['.py'])
	wafadmin.inst_var = 'PREFIX'
	wafadmin.inst_dir = os.path.join('lib', 'waf-%s-%s' % (VERSION, REVISION), 'wafadmin')

	tools = bld.create_obj('py')
	tools.find_sources_in_dirs('wafadmin/Tools', exts=['.py'])
	tools.inst_var = 'PREFIX'
	tools.inst_dir = os.path.join(wafadmin.inst_dir, 'Tools')

	bld.install_files('PREFIX', 'bin', 'waf', chmod=0755)

	#print "waf is now installed in %s [%s, %s]" % (prefix, wafadmindir, binpath)
	#print "make sure the PATH contains %s/bin:$PATH" % prefix


# the init function is called right after the command-line arguments are parsed
# it is run before configure(), build() and shutdown()
# in this case it calls sys.exit(0) to terminate the program
def init():
	if Params.g_options.setver: # maintainer only (ita)
		ver = Params.g_options.setver
		hexver = '0x'+ver.replace('.','0')
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' wscript""" % ver).close()
		os.popen("""perl -pi -e 's/^VERSION=(.*)?$/VERSION="%s"/' waf-light""" % ver).close()
		os.popen("""perl -pi -e 's/^g_version(.*)?$/g_version="%s"/' wafadmin/Params.py""" % ver).close()
		os.popen("""perl -pi -e 's/^HEXVERSION(.*)?$/HEXVERSION = %s/' wafadmin/Constants.py""" % hexver).close()
		sys.exit(0)
	elif Params.g_options.waf:
		create_waf()
		sys.exit(0)
	elif Params.g_commands['check']:
		import Test
		Test.run_tests()
		sys.exit(0)

#def dist():
#	import Scripting
#	Scripting.g_dist_exts += ['Weak.py'] # shows how to exclude a file from dist
#	Scripting.Dist(APPNAME, VERSION)

