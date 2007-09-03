#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2007 (ita)

import os, sys, re
sys.path.append(os.path.abspath('..'))
import optparse
import Object, Utils, Action, Params, checks, Configure, Scan


class filter:
	def __init__(self):
		self.fn     = ''
		self.i      = 0
		self.max    = 0
		self.txt    = ""
		self.buf    = []

	def next(self):
		ret = self.txt[self.i]
		# unterminated lines can be eliminated
		if ret == '\\':
			try:
				if self.txt[self.i+1] == '\n':
					self.i += 2
					return self.next()
				elif self.txt[self.i+1] == '\r':
					if self.txt[self.i+2] == '\n':
						self.i += 3
						return self.next()
				else:
					pass
			except:
				pass
		elif ret == '\r':
			if self.txt[self.i+1] == '\n':
				self.i += 2
				return '\n'
		self.i += 1
		return ret

	def good(self):
		return self.i < self.max

	def initialize(self, filename):
		self.fn = filename
		f = open(filename, "r")
		self.txt = f.read()
		f.close()

		self.i = 0
		self.max = len(self.txt)

	def start(self, filename):
		self.initialize(filename)
		while self.good():
			c = self.next()
			if c == '"':
				self.skip_string()
			elif c == "'":
				self.skip_char()
			elif c == '/':
				c = self.next()
				if c == '+': self.get_p_comment()
				if c == '*': self.get_c_comment()
				elif c == '/': self.get_cc_comment()
				#else: self.buf.append('/'+c) # simple punctuator '/'
			else:
				self.buf.append(c)


	def get_p_comment(self):
		self.nesting = 1
		prev = 0
		while self.good():
			c = self.next()
			if c == '+':
				prev = 1
			elif c == '/':
				if prev:
					self.nesting -= 1
					if self.nesting == 0: break
				else:
					if self.good():
						c = self.next()
						if c == '+':
							self.nesting += 1
					else:
						break
			else:
				prev = 0

	def get_cc_comment(self):
		c = self.next()
		while c != '\n': c = self.next()

	def get_c_comment(self):
		c = self.next()
		prev = 0
		while self.good():
			if c == '*':
				prev = 1
			elif c == '/':
				if prev: break
			else:
				prev = 0
			c = self.next()

	def skip_char(self):
		c = self.next()
		# skip one more character if there is a backslash '\''
		if c == '\\':
			c = self.next()
			# skip a hex char (e.g. '\x50')
			if c == 'x':
				c = self.next()
				c = self.next()
		c = self.next()
		if c != '\'': print "uh-oh, invalid character"

	def skip_string(self):
		c=''
		while self.good():
			p = c
			c = self.next()
			if c == '"':
				cnt = 0
				while 1:
					#print "cntcnt = ", str(cnt), self.txt[self.i-2-cnt]
					if self.txt[self.i-2-cnt] == '\\': cnt+=1
					else: break
				#print "cnt is ", str(cnt)
				if (cnt%2)==0: break

class parser:
	def __init__(self):
		self.code = ''
		self.module = ''
		self.imports = []
		self.re_module = re.compile("module\s+([^;]+)")
		self.re_import = re.compile("import\s+([^;]+)")
		self.re_import_bindings = re.compile("([^:]+):(.*)")
		self.re_import_alias = re.compile("[^=]+=(.+)")

	def run(self):
		self.imports = []
		self.module = ''

		# get the module name (if present)

		mod_name = self.re_module.search(self.code)
		if mod_name:
			self.module = re.sub('\s+', '', mod_name.group(1)) # strip all whitespaces

		# go through the code, have a look at all import occurrences

		# first, lets look at anything beginning with "import" and ending with ";"
		import_iterator = self.re_import.finditer(self.code)
		if import_iterator:
			for import_match in import_iterator:
				import_match_str = re.sub('\s+', '', import_match.group(1)) # strip all whitespaces

				# does this end with an import bindings declaration?
				# (import bindings always terminate the list of imports)
				bindings_match = self.re_import_bindings.match(import_match_str)
				if bindings_match:
					import_match_str = bindings_match.group(1)
					# if so, extract the part before the ":" (since the module declaration(s) is/are located there)

				# split the matching string into a bunch of strings, separated by a comma
				matches = import_match_str.split(',')

				for match in matches:
					alias_match = self.re_import_alias.match(match)
					if alias_match:
						# is this an alias declaration? (alias = module name) if so, extract the module name
						match = alias_match.group(1)

					if not match in self.imports:
						self.imports.append(match) # hooray!

	def start(self, file):
		gruik = filter()
		gruik.start(file)
		self.code = "".join(gruik.buf)
		self.run()

class d_scanner(Scan.scanner):
	"scanner for d files"
	def __init__(self):
		Scan.scanner.__init__(self)
		self.do_scan = self.do_scan_new
		self.get_signature = self.get_signature_rec

	def scan(self, node, env, path_lst, defines=None):
		"look for .d/.di the .d source need"
		debug("_scan_preprocessor(self, node, env, path_lst)", 'ccroot')
		gruik = parser()
		gruik.start2(node, env)

		if Params.g_verbose:
			debug("nodes found for %s: %s %s" % (str(node), str(gruik.m_nodes), str(gruik.m_names)), 'deps')
			#debug("deps found for %s: %s" % (str(node), str(gruik.deps)), 'deps')
		return (gruik.m_nodes, gruik.m_names)

g_d_scanner = d_scanner()
"scanner for d programs"

class dobj(Object.genobj):

	s_default_ext = ['.d', '.di', '.D']
	def __init__(self, type='program'):
		Object.genobj.__init__(self, type)

		self.dflags = ''
		self.importpaths = ''
		self.libs = ''
		self.libpaths = ''
		self.uselib = ''
		self.uselib_local = ''

		self.m_nodes = []
		self.m_names = []

	def apply(self):

		global g_d_scanner

		#initialization
		if self.m_type == 'objects':
			type = 'program'
		else:
			type = self.m_type

		env = self.env
		dpath_st         = env['DPATH_ST']
		lib_st           = env['DLIB_ST']
		libpath_st       = env['DLIBPATH_ST']

		importpaths = []
		libpaths = []
		libs = []

		if type == 'staticlib':
			linktask = self.create_task('ar_link_static', self.env, 101)
		else:
			linktask = self.create_task('d_link', self.env, 101)

		# go through the local uselibs
		for local_uselib in self.to_list(self.uselib_local):
			y = Object.name_to_obj(local_uselib)
			if not y: continue

			if not y.m_posted: y.post()

			if y.m_type == 'shlib':
				libs = libs + [y.target]
			elif y.m_type == 'staticlib':
				libs = libs + [y.target]
			elif y.m_type == 'objects':
				pass
			else:
				error('%s has unknown object type %s, in apply_lib_vars, uselib_local.'
				      % (y.name, y.m_type))

			if y.m_linktask is not None:
				linktask.set_run_after(y.m_linktask)

			libpaths = libpaths + [y.path.bldpath(self.env)]


		# add compiler flags
		for i in self.to_list(self.uselib):
			if self.env['DFLAGS_' + i]:
				self.env.append_unique('DFLAGS', self.env['DFLAGS_' + i])
		if self.dflags:
			self.env.append_unique('DFLAGS', self.dflags)

		d_shlib_dflags = self.env['D_' + type + '_DFLAGS']
		if d_shlib_dflags:
			for dflag in d_shlib_dflags:
				self.env.append_unique('DFLAGS', dflag)


		# add import paths
		for i in self.to_list(self.uselib):
			if self.env['DPATH_' + i]:
				importpaths += self.to_list(self.env['DPATH_' + i])
		importpaths = self.to_list(self.importpaths) + importpaths

		# now process the import paths
		for path in importpaths:
			if Utils.is_absolute_path(path):
				imppath = path
			else:
				imppath = self.path.find_source_lst(Utils.split_path(path)).srcpath(self.env)
			self.env.append_unique('_DIMPORTFLAGS', dpath_st % imppath)


		# add library paths
		for i in self.to_list(self.uselib):
			if self.env['LIBPATH_' + i]:
				libpaths += self.to_list(self.env['LIBPATH_' + i])
		libpaths = self.to_list(self.libpaths) + libpaths

		# now process the library paths
		for path in libpaths:
			self.env.append_unique('_DLIBDIRFLAGS', libpath_st % path)


		# add libraries
		for i in self.to_list(self.uselib):
			if self.env['LIB_' + i]:
				libs += self.to_list(self.env['LIB_' + i])
		libs = libs + self.to_list(self.libs)

		# now process the libraries
		for lib in libs:
			self.env.append_unique('_DLIBFLAGS', lib_st % lib)


		# add linker flags
		for i in self.to_list(self.uselib):
			dlinkflags = self.env['DLINKFLAGS_' + i]
			if dlinkflags:
				for linkflag in dlinkflags:
					self.env.append_unique('DLINKFLAGS', linkflag)

		d_shlib_linkflags = self.env['D_' + type + '_LINKFLAGS']
		if d_shlib_linkflags:
			for linkflag in d_shlib_linkflags:
				self.env.append_unique('DLINKFLAGS', linkflag)


		# create compile tasks

		compiletasks = []

		obj_ext = self.env['D_' + type + '_obj_ext'][0]

		find_source_lst = self.path.find_source_lst

		for filename in self.to_list(self.source):
			node = find_source_lst(Utils.split_path(filename))
			base, ext = os.path.splitext(filename)

			if not ext in self.s_default_ext:
				fatal("unknown file " + filename)

			task = self.create_task('d', self.env, 10)
			task.set_inputs(node)
			task.set_outputs(node.change_ext(obj_ext))
			task.m_scanner = g_d_scanner

			compiletasks.append(task)

		# and after the objects, the remaining is the link step
		# link in a lower priority (101) so it runs alone (default is 10)
		global g_prio_link

		outputs = []
		for t in compiletasks: outputs.append(t.m_outputs[0])
		linktask.set_inputs(outputs)
		linktask.set_outputs(self.path.find_build(self.get_target_name()))

		self.m_linktask = linktask

	def get_target_name(self):
		v = self.env

		prefix = v['D_' + self.m_type + '_PREFIX']
		suffix = v['D_' + self.m_type + '_SUFFIX']

		if not prefix: prefix=''
		if not suffix: suffix=''
		return ''.join([prefix, self.target, suffix])

	def install(self):
		pass

def setup(env):
	d_str = '${D_COMPILER} ${DFLAGS} ${_DIMPORTFLAGS} ${D_SRC_F}${SRC} ${D_TGT_F}${TGT}'
	link_str = '${D_LINKER} ${DLNK_SRC_F}${SRC} ${DLNK_TGT_F}${TGT} ${DLINKFLAGS} ${_DLIBDIRFLAGS} ${_DLIBFLAGS}'

	Action.simple_action('d', d_str, 'GREEN')
	Action.simple_action('d_link', link_str, color='YELLOW')

	Object.register('d', dobj)

def detect(conf):
	return 1


if __name__ == "__main__":
	#Params.g_verbose = 2
	#Params.g_zones = ['preproc']
	#class dum:
	#	def __init__(self):
	#		self.parse_cache_d = {}
	#Params.g_build = dum()

	try: arg = sys.argv[1]
	except: arg = "file.d"

	# TODO
	paths = ['.']

	#gruik = filter()
	#gruik.start(arg)

	#code = "".join(gruik.buf)

	#print "we have found the following code"
	#print code

	#print "now parsing"
	#print "-------------------------------------------"

	parser_ = parser()
	parser_.start(arg)

	print "module: %s" % parser_.module
	print "imports: ",
	for imp in parser_.imports:
		print imp + " ",
	print

