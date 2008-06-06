#!/usr/bin/env python
# encoding: utf-8
# Matthias Jahn, 2008, jahn matthias ath freenet punto de
# Thomas Nagy, 2008 (ita)

import sys, re, os, optparse

import TaskGen, Task, Params, Scan, Common, Utils, preproc
from Params import error, debug, fatal, warning
from TaskGen import taskgen, after, before, feature

REVISION="0.1.3"

"""
if you want to use the code here, you must use something like this:
obj = obj.create(...)
obj.features.append("libtool")
obj.vnum = "1.2.3" # optional, but versioned libraries are common
"""

# fake libtool files
fakelibtool_vardeps = ['CXX', 'PREFIX']
def fakelibtool_build(task):
	# Writes a .la file, used by libtool
	env = task.env()
	dest  = open(task.m_outputs[0].abspath(env), 'w')
	sname = task.m_inputs[0].m_name
	fu = dest.write
	fu("# Generated by ltmain.sh - GNU libtool 1.5.18 - (pwn3d by BKsys II code name WAF)\n")
	if env['vnum']:
		nums = env['vnum'].split('.')
		libname = task.m_inputs[0].m_name
		name3 = libname+'.'+env['vnum']
		name2 = libname+'.'+nums[0]
		name1 = libname
		fu("dlname='%s'\n" % name2)
		strn = " ".join([name3, name2, name1])
		fu("library_names='%s'\n" % (strn) )
	else:
		fu("dlname='%s'\n" % sname)
		fu("library_names='%s %s %s'\n" % (sname, sname, sname) )
	fu("old_library=''\n")
	vars = ' '.join(env['libtoolvars']+env['LINKFLAGS'])
	fu("dependency_libs='%s'\n" % vars)
	fu("current=0\n")
	fu("age=0\nrevision=0\ninstalled=yes\nshouldnotlink=no\n")
	fu("dlopen=''\ndlpreopen=''\n")
	fu("libdir='%s/lib'\n" % env['PREFIX'])
	dest.close()
	return 0

def read_la_file(path):
	sp = re.compile(r'^([^=]+)=\'(.*)\'$')
	dc={}
	file = open(path, "r")
	for line in file.readlines():
		try:
			#print sp.split(line.strip())
			_, left, right, _ = sp.split(line.strip())
			dc[left]=right
		except ValueError:
			pass
	file.close()
	return dc

@taskgen
@feature("libtool")
@after('apply_link')
def apply_link_libtool(self):
	if self.m_type != 'program':
		linktask = self.link_task
		latask = self.create_task('fakelibtool', self.env)
		latask.set_inputs(linktask.m_outputs)
		latask.set_outputs(linktask.m_outputs[0].change_ext('.la'))
		self.m_latask = latask

	if not (Params.g_commands['install'] or Params.g_commands['uninstall']): return
	self.install_results(dest_var, dest_subdir, self.m_latask)

@taskgen
@feature("libtool")
@before('apply_core')
def apply_libtool(self):
	self.env['vnum']=self.vnum

	paths=[]
	libs=[]
	libtool_files=[]
	libtool_vars=[]

	for l in self.env['LINKFLAGS']:
		if l[:2]=='-L':
			paths.append(l[2:])
		elif l[:2]=='-l':
			libs.append(l[2:])

	for l in libs:
		for p in paths:
			dict = read_la_file(p+'/lib'+l+'.la')
			linkflags2 = dict.get('dependency_libs', '')
			for v in linkflags2.split():
				if v.endswith('.la'):
					libtool_files.append(v)
					libtool_vars.append(v)
					continue
				self.env.append_unique('LINKFLAGS', v)
				break

	self.env['libtoolvars']=libtool_vars

	while libtool_files:
		file = libtool_files.pop()
		dict = read_la_file(file)
		for v in dict['dependency_libs'].split():
			if v[-3:] == '.la':
				libtool_files.append(v)
				continue
			self.env.append_unique('LINKFLAGS', v)

Task.task_type_from_func('fakelibtool', vars=fakelibtool_vardeps, func=fakelibtool_build, color='BLUE', prio=200)

class libtool_la_file:
	def __init__ (self, la_filename):
		self.__la_filename = la_filename
		#remove path and .la suffix
		self.linkname = str(os.path.split(la_filename)[-1])[:-3]
		if self.linkname.startswith("lib"):
			self.linkname = self.linkname[3:]
		# The name that we can dlopen(3).
		self.dlname = None
		# Names of this library
		self.library_names = None
		# The name of the static archive.
		self.old_library = None
		# Libraries that this one depends upon.
		self.dependency_libs = None
		# Version information for libIlmImf.
		self.current = None
		self.age = None
		self.revision = None
		# Is this an already installed library?
		self.installed = None
		# Should we warn about portability when linking against -modules?
		self.shouldnotlink = None
		# Files to dlopen/dlpreopen
		self.dlopen = None
		self.dlpreopen = None
		# Directory that this library needs to be installed in:
		self.libdir = '/usr/lib'
		if not self.__parse():
			raise "file %s not found!!" %(la_filename)

	def __parse(self):
		"Retrieve the variables from a file"
		if not os.path.isfile(self.__la_filename): return 0
		la_file=open(self.__la_filename, 'r')
		for line in la_file:
			ln = line.strip()
			if not ln: continue
			if ln[0]=='#': continue
			(key, value) = str(ln).split('=', 1)
			key = key.strip()
			value = value.strip()
			if value == "no": value = False
			elif value == "yes": value = True
			else:
				try: value = int(value)
				except ValueError: value = value.strip("'")
			setattr(self, key, value)
		la_file.close()
		return 1

	def get_libs(self):
		"""return linkflags for this lib"""
		libs = []
		if self.dependency_libs:
			libs = str(self.dependency_libs).strip().split()
		if libs == None:
			libs = []
		# add la lib and libdir
		libs.insert(0, "-l%s" % self.linkname.strip())
		libs.insert(0, "-L%s" % self.libdir.strip())
		return libs

	def __str__(self):
		return '''\
dlname = "%(dlname)s"
library_names = "%(library_names)s"
old_library = "%(old_library)s"
dependency_libs = "%(dependency_libs)s"
version = %(current)s.%(age)s.%(revision)s
installed = "%(installed)s"
shouldnotlink = "%(shouldnotlink)s"
dlopen = "%(dlopen)s"
dlpreopen = "%(dlpreopen)s"
libdir = "%(libdir)s"''' % self.__dict__

class libtool_config:
	def __init__ (self, la_filename):
		self.__libtool_la_file = libtool_la_file(la_filename)
		tmp = self.__libtool_la_file
		self.__version = [int(tmp.current), int(tmp.age), int(tmp.revision)]
		self.__sub_la_files = []
		self.__sub_la_files.append(la_filename)
		self.__libs = None

	def __cmp__(self, other):
		"""make it compareable with X.Y.Z versions (Y and Z are optional)"""
		if not other:
			return 1
		othervers = [int(s) for s in str(other).split(".")]
		selfvers = self.__version

		if selfvers > othervers:
			return 1
		if selfvers < othervers:
			return -1
		return 0

	def __str__(self):
		return "\n".join([
			str(self.__libtool_la_file),
			' '.join(self.__libtool_la_file.get_libs()),
			'* New getlibs:',
			' '.join(self.get_libs())
		])

	def __get_la_libs(self, la_filename):
		return libtool_la_file(la_filename).get_libs()

	def get_libs(self):
		"""return the complete uniqe linkflags that do not
		contain .la files anymore"""
		libs_list = list(self.__libtool_la_file.get_libs())
		libs_map = {}
		while len(libs_list) > 0:
			entry = libs_list.pop(0)
			if entry:
				if str(entry).endswith(".la"):
					## prevents duplicate .la checks
					if entry not in self.__sub_la_files:
						self.__sub_la_files.append(entry)
						libs_list.extend(self.__get_la_libs(entry))
				else:
					libs_map[entry]=1
		self.__libs = libs_map.keys()
		return self.__libs

	def get_libs_only_L(self):
		if not self.__libs: self.get_libs()
		libs = self.__libs
		libs = filter(lambda s: str(s).startswith('-L'), libs)
		return libs

	def get_libs_only_l(self):
		if not self.__libs: self.get_libs()
		libs = self.__libs
		libs = filter(lambda s: str(s).startswith('-l'), libs)
		return libs

	def get_libs_only_other(self):
		if not self.__libs: self.get_libs()
		libs = self.__libs
		libs = filter(lambda s: not (str(s).startswith('-L') or str(s).startswith('-l')), libs)
		return libs

def useCmdLine():
	"""parse cmdline args and control build"""
	usage = '''Usage: %prog [options] PathToFile.la
example: %prog --atleast-version=2.0.0 /usr/lib/libIlmImf.la
nor: %prog --libs /usr/lib/libamarok.la'''
	parser = optparse.OptionParser(usage)
	a = parser.add_option
	a("--version", dest = "versionNumber",
		action = "store_true", default = False,
		help = "output version of libtool-config"
		)
	a("--debug", dest = "debug",
		action = "store_true", default = False,
		help = "enable debug"
		)
	a("--libs", dest = "libs",
		action = "store_true", default = False,
		help = "output all linker flags"
		)
	a("--libs-only-l", dest = "libs_only_l",
		action = "store_true", default = False,
		help = "output -l flags"
		)
	a("--libs-only-L", dest = "libs_only_L",
		action = "store_true", default = False,
		help = "output -L flags"
		)
	a("--libs-only-other", dest = "libs_only_other",
		action = "store_true", default = False,
		help = "output other libs (e.g. -pthread)"
		)
	a("--atleast-version", dest = "atleast_version",
		default=None,
		help = "return 0 if the module is at least version ATLEAST_VERSION"
		)
	a("--exact-version", dest = "exact_version",
		default=None,
		help = "return 0 if the module is exactly version EXACT_VERSION"
		)
	a("--max-version", dest = "max_version",
		default=None,
		help = "return 0 if the module is at no newer than version MAX_VERSION"
		)

	(options, args) = parser.parse_args()
	if len(args) != 1 and not options.versionNumber:
		parser.error("incorrect number of arguments")
	if options.versionNumber:
		print "libtool-config version %s" % REVISION
		return 0
	ltf = libtool_config(args[0])
	if options.debug:
		print(ltf)
	if options.atleast_version:
		if ltf >= options.atleast_version: return 0
		sys.exit(1)
	if options.exact_version:
		if ltf == options.exact_version: return 0
		sys.exit(1)
	if options.max_version:
		if ltf <= options.max_version: return 0
		sys.exit(1)

	def p(x):
		print " ".join(x)
	if options.libs: p(ltf.get_libs())
	elif options.libs_only_l: p(ltf.get_libs_only_l())
	elif options.libs_only_L: p(ltf.get_libs_only_L())
	elif options.libs_only_other: p(ltf.get_libs_only_other())
	return 0

if __name__ == '__main__':
	useCmdLine()

