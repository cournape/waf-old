#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007 (ita)

"Enable other signature/preprocessing/timestamp schemes - all tweaks go here"

import Params
from Params import hash_sig_weak

cregexp1 = re.compile(r'^[ \t]*#[ \t]*(?:include)[ \t]*(?:/\*.*?\*/)?[ \t]*(<|")([^>"]+)(>|")', re.M)
"regexp for computing dependencies (when not using the preprocessor)"


g_timestamp = 0
"if 1: do not look at the file contents for dependencies"

g_preprocess = 1
"use the c/c++ preprocessor"

def h_simple_str(str):
	return str.__hash__()

def h_simple_lst(lst):
	return hash(str(lst))

def h_md5_file_tstamp(filename):
	st = os.stat(filename)
	if stat.S_ISDIR(st.st_mode): raise OSError
	tt = st.st_mtime
	m = md5.new()
	m.update(str(tt)+filename)
	return m.digest()
def h_simple_file(filename):
	f = file(filename,'rb')
	s = f.read().__hash__()
	f.close()
	return s
def h_simple_file_tstamp(filename):
	st = os.stat(filename)
	if stat.S_ISDIR(st.st_mode): raise OSError
	m = md5.new()
	return hash( (st.st_mtime, filename) )

def set_weak_hash():
	"TODO: some projects (or skeptics) might want to compare without md5 hashes"
	"TODO: move this code into a separate module, and replace vars and functions dynamically"
	Params.sig_nil = 17

        Params.hash_sig = hash_sig_weak
        Params.h_string = h_simple_str
        Params.h_list = h_simple_lst
        if g_timestamp: Params.h_file = h_simple_file_tstamp
        else: Params.h_file = h_simple_file


"""

	def _get_signature_regexp_strong(self, task):
		m = md5.new()
		tree = Params.g_build
		seen = []
		env  = task.m_env
		def add_node_sig(node):
			if not node: warning("null node in get_node_sig")
			if node in seen: return

			# TODO - using the variant each time is stupid
			variant = node.variant(env)
			seen.append(node)

			# rescan if necessary, and add the signatures of the nodes it depends on
			if tree.needs_rescan(node, task.m_env):
				self.do_scan(node, task.m_env, task.m_scanner_params)
			lst = tree.m_depends_on[variant][node]
			for dep in lst: add_node_sig(dep)
			m.update(tree.m_tstamp_variants[variant][node])
		# add the signatures of the input nodes
		for node in task.m_inputs: add_node_sig(node)
		# add the signatures of the task it depends on
		for task in task.m_run_after: m.update(task.signature())
		return m.digest()

	def _get_signature_regexp_weak(self, task):
		msum = 0
		tree = Params.g_build
		seen = []
		env  = task.m_env
		def add_node_sig(node):
			if not node: warning("null node in get_node_sig")
			if node in seen: return 0

			sum = 0

			# TODO - using the variant each time is stupid
			variant = node.variant(env)
			seen.append(node)

			sum += tree.m_tstamp_variants[variant][node]
			# rescan if necessary, and add the signatures of the nodes it depends on
			if tree.needs_rescan(node, task.m_env): self.do_scan(node, task.m_env, task.m_scanner_params)
			lst = tree.m_depends_on[variant][node]
			for dep in lst: sum += add_node_sig(dep)
			return sum
		# add the signatures of the input nodes
		for node in task.m_inputs: msum = hash_sig_weak(msum, add_node_sig(node))
		# add the signatures of the task it depends on
		for task in task.m_run_after: msum = hash_sig_weak(msum, task.signature())
		return int(msum)

	def _get_signature_preprocessor_weak(self, task):
		msum = 0
		tree = Params.g_build
		rescan = 0
		env=task.m_env
		seen=[]
		def add_node_sig(n):
			if not n: warning("null node in get_node_sig")
			if n.m_name in seen: return 0

			# TODO - using the variant each time is stupid
			variant = n.variant(env)
			seen.append(n.m_name)
			return tree.m_tstamp_variants[variant][n]

		# there is only one c/cpp file as input
		node = task.m_inputs[0]

		variant = node.variant(env)

		if tree.needs_rescan(node, task.m_env): rescan = 1
		if not rescan:
			for anode in tree.m_depends_on[variant][node]:
				if tree.needs_rescan(anode, task.m_env): rescan = 1

		# rescan the cpp file if necessary
		if rescan:
			#print "rescanning ", node
			self.do_scan(node, task.m_env, task.m_scanner_params)

#		print "rescan for ", task.m_inputs[0], " is ", rescan,  " and deps ", \
#			tree.m_depends_on[variant][node], tree.m_raw_deps[variant][node]

		# we are certain that the files have been scanned - compute the signature
		msum = hash_sig_weak(msum, add_node_sig(node))
		for n in tree.m_depends_on[variant][node]:
			msum = hash_sig_weak(msum, add_node_sig(n))

		# and now xor the signature with the other tasks
		for task in task.m_run_after:
			msum = hash_sig_weak(msum, task.signature())
		#debug("signature of the task %d is %s" % (task.m_idx, Params.vsig(sig)), 'ccroot')

		return int(msum)

	def get_signature(self, task):
		debug("get_signature(self, task)", 'ccroot')
		return self._get_signature_preprocessor(task)
		if Params.g_preprocess:
			if Params.g_strong_hash:
				return self._get_signature_preprocessor(task)
			else:
				return self._get_signature_preprocessor_weak(task)
		else:
			if Params.g_strong_hash:
				return self._get_signature_regexp_strong(task)
			else:
				return self._get_signature_regexp_weak(task)

	def scan(self, node, env, path_lst, defines=None):
		debug("scan", 'ccroot')
		if Params.g_preprocess:
			return self._scan_preprocessor(node, env, path_lst, defines)
		else:
			# the regular scanner does not use the define values
			return self._scan_default(node, env, path_lst)
		#return self._scan_default(node, env, path_lst)

	def _scan_default(self, node, env, path_lst):
		debug("_scan_default(self, node, env, path_lst)", 'ccroot')
		variant = node.variant(env)
		file = open(node.abspath(env), 'rb')
		found = cregexp1.findall( file.read() )
		file.close()

		nodes = []
		names = []
		if not node: return (nodes, names)

		for (_, name, _) in found:
			#print 'boo', name

			# quite a few nested 'for' loops, looking suspicious
			found = None
			for dir in path_lst:
				found = dir.get_file(name)
				if found:
					break
			if found: nodes.append(found)
			else:     names.append(name)
		#print "-S ", nodes, names
		return (nodes, names)

	def get_signature_default_weak(self, task):
		msum = 0
		tree = Params.g_build
		seen = []
		env  = task.m_env
		variant = task.m_inputs[0].variant(env)
		def add_node_sig(node):
			if not node: print "warning: null node in get_node_sig"

			sum = 0
			seen.append(node.m_name)

			sum += tree.m_tstamp_variants[variant][node]
			# rescan if necessary, and add the signatures of the nodes it depends on
			if tree.needs_rescan(node, task.m_env): self.do_scan(node, task.m_env, task.m_scanner_params)
			try: lst = tree.m_depends_on[variant][node]
			except KeyError: lst = []
			for dep in lst:
				if not dep.m_name in seen:
					sum += add_node_sig(dep)
			return sum
		# add the signatures of the input nodes
		for node in task.m_inputs: msum = hash_sig_weak(msum, add_node_sig(node))
		# add the signatures of the task it depends on
		for task in task.m_run_after: msum = hash_sig_weak(msum, task.signature())
		return int(msum)


"""

