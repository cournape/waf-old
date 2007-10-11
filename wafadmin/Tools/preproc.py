#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""Waf preprocessor for finding dependencies
  because of the includes system, it is necessary to do the preprocessing in at least two steps:
  - filter the comments and output the preprocessing lines
  - interpret the preprocessing lines, jumping on the headers during the process
"""

import re, sys, os, string
sys.path = ['.', '..'] + sys.path
import Params
from Params import debug, error, warning

class PreprocError(Exception):
	pass

# ignore #warning and #error
reg_define = re.compile('^\s*(#|%:)\s*(if|ifdef|ifndef|else|elif|endif|include|import|define|undef|pragma)\s*(.*)\r*')

reg_nl = re.compile('\\\\\r*\n', re.MULTILINE)
reg_cpp = re.compile(r"""(/\*[^*]*\*+([^/*][^*]*\*+)*/)|//[^\n]*|("(\\.|[^"\\])*"|'(\\.|[^'\\])*'|.[^/"'\\]*)""", re.MULTILINE)
def repl(m):
	s = m.group(1)
	if s is not None: return ' '
	s = m.group(3)
	if s is None: return ''
	return s

def replace_inc(m):
	return (m.group(2), m.group(3))

def filter_comments(filename):
	# return a list of tuples : keyword, line
	f = open(filename, "r")
	code = f.read()
	f.close()

	code = reg_nl.sub('', code)
	code = reg_cpp.sub(repl, code)
	code = code.split('\n')

	return [reg_define.sub(replace_inc, line) for line in code if reg_define.search(line)]

strict_quotes = 0
"Keep <> for system includes (do not search for those includes)"

alpha = string.letters + '_' + string.digits

accepted  = 'a'
ignored   = 'i'
undefined = 'u'
skipped   = 's'

num = 'i' # number
op = '@' # operator
ident = 'T' # identifier
stri = 's' # string
chr = 'c' # char

# TODO handle the trigraphs
trigs = {
'=' : '#',
'-' : '~',
'/' : '\\',
'!' : '|',
'\'': '^',
'(' : '[',
')' : ']',
'<' : '{',
'>' : '}',
}

punctuators_table = [
{'!': 43, '#': 45, '%': 22, '&': 30, ')': 50, '(': 49, '+': 11, '*': 18, '-': 14,
 ',': 56, '/': 20, '.': 38, ';': 55, ':': 41, '=': 28, '<': 1, '?': 54, '>': 7,
 '[': 47, ']': 48, '^': 36, '{': 51, '}': 52, '|': 33, '~': 53},
{'=': 6, ':': 5, '%': 4, '<': 2, '$$': '<'},
{'$$': '<<', '=': 3},
{'$$': '<<='},
{'$$': '<%'},
{'$$': '<:'},
{'$$': '<='},
{'$$': '>', '=': 10, '>': 8},
{'$$': '>>', '=': 9},
{'$$': '>>='},
{'$$': '>='},
{'$$': '+', '+': 12, '=': 13},
{'$$': '++'},
{'$$': '+='},
{'=': 17, '-': 15, '$$': '-', '>': 16},
{'$$': '--'},
{'$$': '->'},
{'$$': '-='},
{'$$': '*', '=': 19},
{'$$': '*='},
{'$$': '/', '=': 21},
{'$$': '/='},
{'$$': '%', ':': 23, '=': 26, '>': 27},
{'$$': '%:', '%': 24},
{':': 25},
{'$$': '%:%:'},
{'$$': '%='},
{'$$': '%>'},
{'$$': '=', '=': 29},
{'$$': '=='},
{'$$': '&', '=': 32, '&': 31},
{'$$': '&&'},
{'$$': '&='},
{'$$': '|', '=': 35, '|': 34},
{'$$': '||'},
{'$$': '|='},
{'$$': '^', '=': 37},
{'$$': '^='},
{'$$': '.', '.': 39},
{'.': 40},
{'$$': '...'},
{'$$': ':', '>': 42},
{'$$': ':>'},
{'$$': '!', '=': 44},
{'$$': '!='},
{'#': 46, '$$': '#'},
{'$$': '##'},
{'$$': '['},
{'$$': ']'},
{'$$': '('},
{'$$': ')'},
{'$$': '{'},
{'$$': '}'},
{'$$': '~'},
{'$$': '?'},
{'$$': ';'},
{'$$': ','}
]

def reduce(tokens):
	# TODO evaluate the tokens for 1+1, etc
	return tokens

	#
	print "entering comp"
	if not lst: return [stri, '']

	print "a"
	if len(lst) == 1:
		return lst[0]

	print "lst len is ", len(lst)
	print "lst is ", str(lst)
	print "hey \n\n\n"

	a1_type = lst[0][0]
	a1 = lst[0][1]

	a2_type = lst[1][0]
	a2 = lst[1][1]

	if a1_type == ident:
		if a2 == '#':
			return comp( [[stri, a1]] + lst[2:] )
	if a1 == '#':
		if a2_type == ident:
			return comp( [[stri, a2]] + lst[2:] )
	if a1_type == op:
		if a2_type == num:
			if a1 == '-':
				return [num, - int(a2)]
			if a1 == '!':
				if int(a2) == 0:
					return [num, 1]
				else:
					return [num, 0]
			raise PreprocError, "cannot compute %s (1)" % str(lst)
		raise PreprocError, "cannot compute %s (2)" % str(lst)
	if a1_type == stri:
		if a2_type == stri:
			if lst[2:]:
				return comp( [[stri, a1+a2], comp(lst[2:])] )
			else:
				return [[stri, a1+a2]]

	## we need to scan the third argument given
	try:
		a3_type = lst[2][0]
		a3 = lst[2][1]
	except:
		raise PreprocError, "cannot compute %s (3)" % str(lst)

	if a1_type == ident:
		#print "a1"
		if a2 == '#':
			#print "a2"
			if a3_type == stri:
				#print "hallo"
				return comp([[stri, a1 + a3]] + lst[3:])

	if a1_type == num:
		if a3_type == num:
			a1 = int(a1)
			a3 = int(a3)
			if a2_type == op:
				val = None
				if a2 == '+':    val = a1+a3
				elif a2 == '-':  val = a1-a3
				elif a2 == '/':  val = a1/a3
				elif a2 == '*':  val = a1 * a3
				elif a2 == '%':  val = a1 % a3

				if not val is None:
					return comp( [[num, val]] + lst[3:] )

				elif a2 == '|':  val = a1 | a3
				elif a2 == '&':  val = a1 & a3
				elif a2 == '||': val = a1 or a3
				elif a2 == '&&': val = a1 and a3

				if val: val = 1
				else: val = 0
				return comp( [[num, val]] + lst[3:] )

	raise PreprocError, "could not parse the macro %s " % str(lst)

def eval_fun(name, params, defs, ban=[]):

	fun_def = defs[name]
	fun_code = []+fun_def[1]
	fun_args = fun_def[0]

	# a map  x->1st param, y->2nd param, etc
	param_index = {}
	i = 0
	for u in fun_args:
		param_index[u[1]] = i
		i += 1

	# substitute the arguments within the define expression
	accu = []
	while fun_code:
		tok = fun_code.pop(0)
		if tok[0] == op:
			if tok[1] == '#':
				# the next token is one of the args
				next = fun_code.pop(0)
				tokens = params[param_index[next[1]]]
				# macro parameter evaluation is postponed
				ret = eval_macro(tokens, defs, ban+[name])
				ret = "".join(x[1] for x in ret)
				accu.append(ret)

			elif tok[1] == '##':
				# the next token is an identifier (token pasting)
				next = fun_code.pop(0)
				r = accu[-1]
				accu = accu[:-1]
				new_tokens = [ident, r[1]+next[1]]
				accu.append(new_token)
				# FIXME this supposes that "a##b(foo)" evaluates as "ab(foo)"
			else:
				accu.append(tok)

		elif tok[0] == ident:
			if tok[1] in param_index:
				code = params[param_index[tok[1]]]
				accu += eval_macro(code, defs, ban+[name])
			else:
				accu.append(tok)
		else:
			accu.append(tok)

	ret = eval_macro(accu, defs, ban+[name])
	return ret

def eval_macro(lst, adefs, ban=[]):

	lst = []+lst # lists are mutable

	#print "\n\n\n\n"
	#print "---eval---> ", lst
	#print "-------- eval macro --------"
	#for x in adefs:
	#	print x, "\t\t", adefs[x]
	#print "------ end eval macro ------"
	#print "the huge lst is ", lst

	# substitute the defines (functions and simple macros)
	accu = []
	while lst:
		tok = lst.pop(0)

		if tok[0] == ident and tok[1] in adefs: # TODO the defined() case
			# the identifier is a macro
			name = tok[1]

			fun_def = adefs[tok[1]]
			fun_args=[]
			if fun_def: fun_args = fun_def[0]
			if fun_args == None:
				# simple macro
				# make the substitution, TODO make certain to disallow recursion
				lst = fun_def[1] + lst
			else:
				# function call, collect the arguments
				params = []
				tmp = []
				tok = lst.pop(0)
				if tok[0] != op or tok[1] != '(': raise ParseError, "invalid function call "+name
				count_paren = 0
				while 1:
					tok = lst.pop(0)
					# stop condition
					if count_paren == 0 and tok[0] == op:
						if tok[1] == ')':
							if tmp: params.append(tmp)
							break
						elif tok[1] == ',':
							if not tmp: raise ParseError, "invalid function call "+name
							params.append(tmp)
							continue

					# all other cases we just append the tokens to tmp
					tmp.append(tok)

					# but watch out for the matching parenthesis
					if tok[0] == op:
						if tok[1] == '(':
							count_paren += 1
						elif tok[1] == ')':
							count_paren -= 1

				accu += eval_fun(name, params, adefs)
		else:
			accu.append(tok)

	# now reduce the expressions if possible, like 1+1->2, no more evaluation should take place

	accu = reduce(accu)
	return accu

class cparse:
	def __init__(self, nodepaths=None, strpaths=None, defines=None):
		#self.lines = txt.split('\n')
		self.lines = []
		#self.i     = 0
		#self.txt   = ''
		self.max   = 0
		self.buf   = []

		if defines is None:
			self.defs  = {}
		else:
			self.defs  = dict(defines) # make a copy
		self.state = []

		self.env   = None # needed for the variant when searching for files

		# include paths
		if strpaths is None:
			self.strpaths = []
		else:
			self.strpaths = strpaths
		self.pathcontents = {}

		self.deps  = []
		self.deps_paths = []

		# waf uses
		if nodepaths is None:
			self.m_nodepaths = []
		else:
			self.m_nodepaths = nodepaths
		self.m_nodes = []
		self.m_names = []

		# dynamic cache
		try:
			self.parse_cache = Params.g_build.parse_cache
		except AttributeError:
			Params.g_build.parse_cache = {}
			self.parse_cache = Params.g_build.parse_cache

	def tryfind(self, filename):
		if self.m_nodepaths:
			found = 0
			for n in self.m_nodepaths:
				found = n.find_source(filename, create=0)
				if found:
					self.m_nodes.append(found)
					# screw Qt
					if filename[-4:] != '.moc': self.addlines(found.abspath(self.env))
					break
			if not found:
				if not filename in self.m_names:
					self.m_names.append(filename)
		else:
			found = 0
			for p in self.strpaths:
				if not p in self.pathcontents.keys():
					self.pathcontents[p] = os.listdir(p)
				if filename in self.pathcontents[p]:
					#print "file %s found in path %s" % (filename, p)
					np = os.path.join(p, filename)
					# screw Qt two times
					if filename[-4:] != '.moc': self.addlines(np)
					self.deps_paths.append(np)
					found = 1
			if not found:
				pass
				#error("could not find %s " % filename)

	def addlines(self, filepath):
		pc = self.parse_cache
		if filepath in pc.keys():
			self.lines = pc[filepath] + self.lines
			return

		try:
			lines = filter_comments(filepath)
			pc[filepath] = lines # memorize the lines filtered
			self.lines = lines + self.lines
		except IOError:
			raise PreprocError, "could not read the file"
		except:
			if Params.g_verbose > 0: warning("parsing %s failed" % filepath)
			raise PreprocError, "unknown exception"

	def start2(self, node, env):
		debug("scanning %s (in %s)" % (node.m_name, node.m_parent.m_name), 'preproc')

		self.env = env
		variant = node.variant(env)

		self.addlines(node.abspath(env))
		if env['DEFLINES']:
			self.lines = env['DEFLINES'] + self.lines

		while self.lines:
			# TODO we can skip evaluating conditions (#if) only when we are
			# certain they contain no define, undef or include
			(type, line) = self.lines.pop(0)
			try:
				self.process_line(type, line)
			except Exception, ex:
				if Params.g_verbose:
					warning("line parsing failed (%s): %s" % (str(ex), line))

	# debug only
	def start(self, filename):
		self.addlines(filename)
		#print self.lines
		while self.lines:
			(type, line) = self.lines.pop(0)
			try:
				self.process_line(type, line)
			except Exception, ex:
				if Params.g_verbose:
					warning("line parsing failed (%s): %s" % (str(ex), line))
				raise
	def isok(self):
		if not self.state: return 1
		if self.state[0] in [skipped, ignored]: return None
		return 1

	def process_line(self, token, line):

		debug("line is %s - %s state is %s" % (token, line, self.state), 'preproc')


		# make certain we define the state if we are about to enter in an if block
		if token in ['ifdef', 'ifndef', 'if']:
			self.state = [undefined] + self.state

		# skip lines when in a dead 'if' branch, wait for the endif
		if not token in ['else', 'elif', 'endif']:
			if not self.isok():
				print "return in process line"
				return

		if token == 'if':
			ret = eval_macro(line, self.defs)
			if ret: self.state[0] = accepted
			else: self.state[0] = ignored
		elif token == 'ifdef':
			ident = self.get_name()
			if ident in self.defs.keys(): self.state[0] = accepted
			else: self.state[0] = ignored
		elif token == 'ifndef':
			ident = self.get_name()
			if ident in self.defs.keys():
				self.state[0] = ignored
			else: self.state[0] = accepted
		elif token == 'include' or token == 'import':
			(type, inc) = tokenize_include(line, self.defs)
			debug("include found %s    (%s) " % (inc, type), 'preproc')
			if strict_quotes or type == '"':
				if not inc in self.deps:
					self.deps.append(inc)
				# allow double inclusion
				self.tryfind(inc)
		elif token == 'elif':
			if self.state[0] == accepted:
				self.state[0] = skipped
			elif self.state[0] == ignored:
				if eval_macro(self.get_body(), self.defs):
					self.state[0] = accepted
		elif token == 'else':
			if self.state[0] == accepted: self.state[0] = skipped
			elif self.state[0] == ignored: self.state[0] = accepted
		elif token == 'endif':
			self.state.pop(0)
		elif token == 'define':
			(name, val) = tokenize_define(line)
			debug("define %s   %s" % (name, str(val)), 'preproc')
			self.defs[name] = val
		elif token == 'undef':
			name = self.get_name()
			if name and name in self.defs:
				self.defs.__delitem__(name)
				#print "undef %s" % name

re_function = re.compile('^[a-zA-Z_][a-zA-Z0-9_]*[(]')
def tokenize_define(txt):
	t = tokenize(txt)
	if re_function.search(txt):
		# this means we have a function
		params = []
		tok = t.pop(0)
		name = tok[1]

		tok = t.pop(0)
		if tok[0] != op: raise PreprocError, "expected open parenthesis"
		while 1:
			tok = t.pop(0)

			if tok[0] == op and tok[1] == ')':
				break
			if tok[0] != ident and (tok[0] != op and tok[1] != '...'):
				raise PreprocError, "expected ident"

			tok2 = t.pop(0)
			if tok2[0] == op and tok2[1] == '...':
				params.append([ident, tok[1]+tok2[1]]) # to get the varargs "z..."
			elif tok2[0] == op and tok2[1] == ')':
				if tok[0] == ident:
					params.append(tok)
				else:
					params.append([ident, tok[1]])
				break
			elif tok2[0] == op and tok2[1] == ',':
				params.append(tok)
			else:
				raise PreprocError, "unexpected token "+str(tok2)

		return (name, [params, t])
	else:
		return (t[0][1], [None, t[1:]])

re_include = re.compile('^\s*(<(.*)>|"(.*)")')
def tokenize_include(txt, defs):
	def replace_v(m):
		return m.group(1)

	if re_include.search(txt):
		t = re_include.sub(replace_v, txt)
		return (t[0], t)

	# perform preprocessing and look at the result, it must match an include
	tokens = tokenize(txt)
	ret = eval_macro(tokens, defs) # it must return a string token
	txt = '"%s"' % ret[0]

	if re_include.search(txt):
		t = re_include.sub(replace_v, txt)
		return (t[0], t)

	# if we come here, parsing failed
	raise PreprocError, "include parsing failed %s" % txt

def tokenize(txt):
	i = 0
	max = len(txt)

	abuf = []
	while i<max:
		#print abuf
		#print "---------------------------------"

		c = txt[i]

		#print "look ", c, '   ->', i

		if c == ' ' or c == '\t':
			i += 1
			# white space
			continue
		elif c == '"':
			# string
			i += 1
			c=''
			buf = []
			while i<max:
				p = c
				c = txt[i]
				i += 1
				if c == '"':
					cnt = 0
					while 1:
						#print "cntcnt = ", str(cnt), txt[i-2-cnt]
						if txt[i-2-cnt] == '\\': cnt+=1
						else: break
					#print "cnt is ", str(cnt)
					if (cnt%2)==0: break
					else: buf.append(c)
				else:
					buf.append(c)
			abuf.append([stri, ''.join(buf)])
			i += 1
		elif c == '\'':
			# char
			buf = []
			i += 1
			c = txt[i]
			i += 1
			buf.append(c)
			# skip one more character if there is a backslash '\''
			if c == '\\':
				c = txt[i]
				i += 1
				buf.append(c)
			c = txt[i]
			i += 1
			if c != '\'': error("uh-oh, invalid character"+str(c)) # TODO special chars
			abuf.append([chr, ''.join(buf)])

			i += 1

		elif c in string.digits:
			# number
			buf =[]
			while 1:
				c = txt[i]
				if c in string.digits: # TODO floats
					buf.append(c)
					i += 1
					if c >= max: break
				else:
					break
			abuf.append([num, ''.join(buf)])
		elif c in alpha:
			# identifier
			buf = []
			while 1:
				c = txt[i]
				if c in alpha:
					buf.append(c)
					i += 1
					if i>= max: break
				else:
					break
			abuf.append([ident, ''.join(buf)])
		else:
			# operator
			pos = 0
			while 1:
				c = txt[i]
				i += 1
				if c in punctuators_table[pos].keys():
					pos = punctuators_table[pos][c]
					if i >= max:
						abuf.append([op, punctuators_table[pos]['$$']])
						break
				else:
					try:
						abuf.append([op, punctuators_table[pos]['$$']])
						i -= 1
						break
					except KeyError:
						raise PreprocError, "unknown op"
					# lexer error
			#abuf.append([op, table[pos]['$$']])
			#r = parse_token(stuff, punctuators_table)
	return abuf

# quick test #
if __name__ == "__main__":
	Params.g_verbose = 2
	Params.g_zones = ['preproc']
	class dum:
		def __init__(self):
			self.parse_cache = {}
	Params.g_build = dum()

	try: arg = sys.argv[1]
	except: arg = "file.c"

	paths = ['.']
	gruik = cparse(strpaths = paths)
	gruik.start(arg)
	print "we have found the following dependencies"
	print gruik.deps
	print gruik.deps_paths

