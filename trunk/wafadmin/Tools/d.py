#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)
# Thomas Nagy, 2007-2008 (ita)

import os, sys, re, optparse
import ccroot # <- leave this
import Object, Utils, Action, Params, checks, Configure, Scan
from Params import debug, error
from Object import taskgen, feature, after, before, extension

EXT_D = ['.d', '.di', '.D']
D_METHS = ['apply_core', 'apply_vnum', 'apply_objdeps'] # additional d methods

def filter_comments(filename):
	f = open(filename, 'r')
	txt = f.read()
	f.close()
	buf = []

	i = 0
	max = len(txt)
	while i < max:
		c = txt[i]
		# skip a string
		if c == '"':
			i += 1
			c = ''
			while i < max:
				p = c
				c = txt[i]
				i += 1
				if i == max: return buf
				if c == '"':
					cnt = 0
					while i < cnt and i < max:
						#print "cntcnt = ", str(cnt), self.txt[self.i-2-cnt]
						if txt[i-2-cnt] == '\\': cnt+=1
						else: break
					#print "cnt is ", str(cnt)
					if (cnt%2)==0: break
		# i -= 1 # <- useless in practice
		# skip a char
		elif c == "'":
			i += 1
			if i == max: return buf
			c = txt[i]
			if c == '\\':
				i += 1
				if i == max: return buf
				c = txt[i]
				if c == 'x':
					i += 2 # skip two chars
			i += 1
			if i == max: return buf
			c = txt[i]
			if c != '\'': print "uh-oh, invalid character"

		# skip a comment
		elif c == '/':
			if i == max: break
			c = txt[i+1]
			# eat /+ +/ comments
			if c == '+':
				i += 1
				nesting = 1
				prev = 0
				while i < max:
					c = txt[i]
					if c == '+':
						prev = 1
					elif c == '/':
						if prev:
							nesting -= 1
							if nesting == 0: break
						else:
							if i < max:
								i += 1
								c = txt[i]
								if c == '+':
									nesting += 1
							else:
								return buf
					else:
						prev = 0
					i += 1
			# eat /* */ comments
			elif c == '*':
				i += 1
				while i < max:
					c = txt[i]
					if c == '*':
						prev = 1
					elif c == '/':
						if prev: break
					else:
						prev = 0
					i += 1
			# eat // comments
			elif c == '/':
				i += 1
				c = txt[i]
				while i < max and c != '\n':
					i += 1
					c = txt[i]
		# a valid char, add it to the buffer
		else:
			buf.append(c)
		i += 1
	return buf

class d_parser(object):
	def __init__(self, env, incpaths):
		#self.code = ''
		#self.module = ''
		#self.imports = []

		self.allnames = []

		self.re_module = re.compile("module\s+([^;]+)")
		self.re_import = re.compile("import\s+([^;]+)")
		self.re_import_bindings = re.compile("([^:]+):(.*)")
		self.re_import_alias = re.compile("[^=]+=(.+)")

		self.env = env

		self.m_nodes = []
		self.m_names = []

		self.incpaths = incpaths

	def tryfind(self, filename):
		found = 0
		for n in self.incpaths:
			found = n.find_resource(filename.replace('.', '/') + '.d')
			if found:
				self.m_nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.m_names:
				self.m_names.append(filename)

	def get_strings(self, code):
		#self.imports = []
		self.module = ''
		lst = []

		# get the module name (if present)

		mod_name = self.re_module.search(code)
		if mod_name:
			self.module = re.sub('\s+', '', mod_name.group(1)) # strip all whitespaces

		# go through the code, have a look at all import occurrences

		# first, lets look at anything beginning with "import" and ending with ";"
		import_iterator = self.re_import.finditer(code)
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

					lst.append(match)
		return lst

	def start(self, node):
		self.waiting = [node]
		# while the stack is not empty, add the dependencies
		while self.waiting:
			nd = self.waiting.pop(0)
			self.iter(nd)

	def iter(self, node):
		path = node.abspath(self.env) # obtain the absolute path
		code = "".join(filter_comments(path)) # read the file and filter the comments
		names = self.get_strings(code) # obtain the import strings
		for x in names:
			# optimization
			if x in self.allnames: continue
			self.allnames.append(x)

			# for each name, see if it is like a node or not
			self.tryfind(x)

class d_scanner(Scan.scanner):
	"scanner for d files"
	def __init__(self):
		Scan.scanner.__init__(self)

	def scan(self, task, node):
		"look for .d/.di the .d source need"
		debug("_scan_preprocessor(self, node, env, path_lst)", 'ccroot')
		gruik = d_parser(task.env(), task.path_lst)
		gruik.start(node)

		if Params.g_verbose:
			debug("nodes found for %s: %s %s" % (str(node), str(gruik.m_nodes), str(gruik.m_names)), 'deps')
			#debug("deps found for %s: %s" % (str(node), str(gruik.deps)), 'deps')
		return (gruik.m_nodes, gruik.m_names)

g_d_scanner = d_scanner()
"scanner for d programs"

def get_target_name(self):
	"for d programs and libs"
	v = self.env
	return v['D_%s_PATTERN' % self.m_type] % self.target

d_params = {
'dflags': {'gdc':'', 'dmd':''},
'importpaths':'',
'libs':'',
'libpaths':'',
'generate_headers':False,
}

@taskgen
@before('apply_type_vars')
@feature('d')
def init_d(self):
	for x in d_params:
		setattr(self, x, getattr(self, x, d_params[x]))

class d_taskgen(Object.task_gen):
	def __init__(self, *k):
		Object.task_gen.__init__(self, *k)

		# TODO m_type is obsolete
		if len(k)>1: self.m_type = k[1]
		else: self.m_type = ''
		if self.m_type:
			self.features.append('d' + self.m_type)

		self.dflags = {'gdc':'', 'dmd':''}
		self.importpaths = ''
		self.libs = ''
		self.libpaths = ''
		self.uselib = ''
		self.uselib_local = ''
		self.inc_paths = []

		self.generate_headers = False # set to true if you want .di files as well as .o

		self.compiled_tasks = []

		self.add_objects = []

		self.vnum = '1.0.0'

Object.add_feature('d', D_METHS)

@taskgen
@feature('d')
@after('apply_d_link')
@before('apply_vnum')
def apply_d_libs(self):
	uselib = self.to_list(self.uselib)
	seen = []
	local_libs = self.to_list(self.uselib_local)
	libs = []
	libpaths = []
	env = self.env
	while local_libs:
		x = local_libs.pop()

		# visit dependencies only once
		if x in seen:
			continue
		else:
			seen.append(x)

		# object does not exist ?
		y = Object.name_to_obj(x)
		if not y:
			fatal('object not found in uselib_local: obj %s uselib %s' % (self.name, x))

		# object has ancestors to process first ? update the list of names
		if y.uselib_local:
			added = 0
			lst = y.to_list(y.uselib_local)
			lst.reverse()
			for u in lst:
				if u in seen: continue
				added = 1
				local_libs = [u]+local_libs
			if added: continue # list of names modified, loop

		# safe to process the current object
		if not y.m_posted: y.post()
		seen.append(x)

		if 'dshlib' in y.features or 'dstaticlib' in y.features:
			libs.append(y.target)

		# add the link path too
		tmp_path = y.path.bldpath(env)
		if not tmp_path in libpaths: libpaths = [tmp_path] + libpaths

		# set the dependency over the link task
		if y.link_task is not None:
			self.link_task.set_run_after(y.link_task)
			dep_nodes = getattr(self.link_task, 'dep_nodes', [])
			self.link_task.dep_nodes = dep_nodes + y.link_task.m_outputs

		# add ancestors uselib too
		# TODO potential problems with static libraries ?
		morelibs = y.to_list(y.uselib)
		for v in morelibs:
			if v in uselib: continue
			uselib = [v]+uselib
	self.uselib = uselib

@taskgen
@feature('dprogram', 'dshlib', 'dstaticlib')
@after('apply_core')
def apply_d_link(self):
	link = getattr(self, 'link', None)
	if not link:
		if 'dstaticlib' in self.features: link = 'ar_link_static'
		else: link = 'd_link'
	linktask = self.create_task(link, self.env)
	outputs = [t.m_outputs[0] for t in self.compiled_tasks]
	linktask.set_inputs(outputs)
	linktask.set_outputs(self.path.find_or_declare(get_target_name(self)))

	self.link_task = linktask

@taskgen
@feature('d')
@after('apply_core')
def apply_d_vars(self):
	env = self.env
	dpath_st   = env['DPATH_ST']
	lib_st     = env['DLIB_ST']
	libpath_st = env['DLIBPATH_ST']

	dflags = {'gdc':[], 'dmd':[]}
	importpaths = self.to_list(self.importpaths)
	libpaths = []
	libs = []
	uselib = self.to_list(self.uselib)

	# add compiler flags
	for i in uselib:
		if env['DFLAGS_' + i]:
			for dflag in self.to_list(env['DFLAGS_' + i][env['COMPILER_D']]):
				if not dflag in dflags[env['COMPILER_D']]:
					dflags[env['COMPILER_D']] += [dflag]
	dflags[env['COMPILER_D']] = self.to_list(self.dflags[env['COMPILER_D']]) + dflags[env['COMPILER_D']]

	for dflag in dflags[env['COMPILER_D']]:
		if not dflag in env['DFLAGS'][env['COMPILER_D']]:
			env['DFLAGS'][env['COMPILER_D']] += [dflag]

	d_shlib_dflags = env['D_' + self.m_type + '_DFLAGS']
	if d_shlib_dflags:
		for dflag in d_shlib_dflags:
			if not dflag in env['DFLAGS'][env['COMPILER_D']]:
				env['DFLAGS'][env['COMPILER_D']] += [dflag]

	env['_DFLAGS'] = env['DFLAGS'][env['COMPILER_D']]

	# add import paths
	for i in uselib:
		if env['DPATH_' + i]:
			for entry in self.to_list(env['DPATH_' + i]):
				if not entry in importpaths:
					importpaths.append(entry)

	# now process the import paths
	for path in importpaths:
		if os.path.isabs(path):
			env.append_unique('_DIMPORTFLAGS', dpath_st % path)
		else:
			node = self.path.find_dir(path)
			self.inc_paths.append(node)
			env.append_unique('_DIMPORTFLAGS', dpath_st % node.srcpath(env))
			env.append_unique('_DIMPORTFLAGS', dpath_st % node.bldpath(env))

	# add library paths
	for i in uselib:
		if env['LIBPATH_' + i]:
			for entry in self.to_list(env['LIBPATH_' + i]):
				if not entry in libpaths:
					libpaths += [entry]
	libpaths = self.to_list(self.libpaths) + libpaths

	# now process the library paths
	for path in libpaths:
		env.append_unique('_DLIBDIRFLAGS', libpath_st % path)

	# add libraries
	for i in uselib:
		if env['LIB_' + i]:
			for entry in self.to_list(env['LIB_' + i]):
				if not entry in libs:
					libs += [entry]
	libs = libs + self.to_list(self.libs)

	# now process the libraries
	for lib in libs:
		env.append_unique('_DLIBFLAGS', lib_st % lib)

	# add linker flags
	for i in uselib:
		dlinkflags = env['DLINKFLAGS_' + i]
		if dlinkflags:
			for linkflag in dlinkflags:
				env.append_unique('DLINKFLAGS', linkflag)

@taskgen
@after('apply_d_vars')
@feature('dshlib')
def add_shlib_d_flags(self):
	for linkflag in self.env['D_shlib_LINKFLAGS']:
		self.env.append_unique('DLINKFLAGS', linkflag)

@extension(EXT_D)
def d_hook(self, node):
	# create the compilation task: cpp or cc
	task = self.create_task('d', self.env)
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

	global g_d_scanner
	task.m_scanner = g_d_scanner
	task.path_lst = self.inc_paths
	#task.defines  = self.scanner_defines

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

	if self.generate_headers:
		task.m_action = Action.g_actions['d_with_header']
		header_node = node.change_ext(self.env['DHEADER_ext'])
		task.m_outputs += [header_node]

d_str = '${D_COMPILER} ${_DFLAGS} ${_DIMPORTFLAGS} ${D_SRC_F}${SRC} ${D_TGT_F}${TGT}'
d_with_header_str = '${D_COMPILER} ${_DFLAGS} ${_DIMPORTFLAGS} \
${D_HDR_F}${TGT[1].bldpath(env)} \
${D_SRC_F}${SRC} \
${D_TGT_F}${TGT[0].bldpath(env)}'
link_str = '${D_LINKER} ${DLNK_SRC_F}${SRC} ${DLNK_TGT_F}${TGT} ${DLINKFLAGS} ${_DLIBDIRFLAGS} ${_DLIBFLAGS}'

Action.simple_action('d', d_str, 'GREEN', prio=100)
Action.simple_action('d_with_header', d_with_header_str, 'GREEN', prio=100)
Action.simple_action('d_link', link_str, color='YELLOW', prio=101)

# for feature request #104
@taskgen
def generate_header(self, filename, inst_var, inst_dir):
	if not hasattr(self, 'header_lst'): self.header_lst = []
	self.meths.add('process_header')
	self.header_lst.append([filename, inst_var, inst_dir])

@taskgen
@before('apply_core')
def process_header(self):
	env = self.env
	for i in getattr(self, 'header_lst', []):
		node = self.path.find_resource(i[0])

		if not node:
			fatal('file not found on d obj '+i[0])

		task = self.create_task('d_header', env, 2)
		task.set_inputs(node)
		task.set_outputs(node.change_ext('.di'))

d_header_str = '${D_COMPILER} ${D_HEADER} ${SRC}'
Action.simple_action('d_header', d_header_str, color='BLUE', prio=80)


# quick test #
if __name__ == "__main__":
	#Params.g_verbose = 2
	#Params.g_zones = ['preproc']
	#class dum:
	#	def __init__(self):
	#		self.parse_cache_d = {}
	#Params.g_build = dum()

	try: arg = sys.argv[1]
	except IndexError: arg = "file.d"

	print "".join(filter_comments(arg))
	# TODO
	paths = ['.']

	#gruik = filter()
	#gruik.start(arg)

	#code = "".join(gruik.buf)

	#print "we have found the following code"
	#print code

	#print "now parsing"
	#print "-------------------------------------------"
	"""
	parser_ = d_parser()
	parser_.start(arg)

	print "module: %s" % parser_.module
	print "imports: ",
	for imp in parser_.imports:
		print imp + " ",
	print
"""

