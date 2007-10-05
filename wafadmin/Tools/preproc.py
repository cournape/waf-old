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


#def comp(self, stuff):
#	ret = red(stuff, self.defs)

	##print "running method comp"
	##clean = subst(stuff, self.defs)
	#res = comp(clean)
	#print res
	#if res:
	#	if res[0] == num: return int(res[1])
	#	return res[1]
	#return 0


def subst(lst, defs):
	if not lst: return []

	a1_t = lst[0][0]
	a1 = lst[0][1]
	if len(lst) == 1:
		if a1_t == ident:
			if a1 in defs:
				return defs[a1]
		return lst

	# len(lst) > 1 : search for macros
	a2_type = lst[1][0]
	a2 = lst[1][1]
	if a1_t == ident:
		if a1 == 'defined':
			if a2_type == ident:
				if a2 in defs:
					return [[num, '1']] + subst(lst[2:], defs)
				else:
					return [[num, '0']] + subst(lst[2:], defs)
			if a2_type == op and a2 == '(':
				if len(lst) < 4:
					raise PreprocError, "expected 4 tokens defined(ident)"
				if lst[2][0] != ident:
					raise PreprocError, "expected defined(ident)"
				if lst[2][1] in defs:
					return [[num, '1']] + subst(lst[4:], defs)
				else:
					return [[num, '0']] + subst(lst[4:], defs)
		if a1 in defs:
			#print a2
			if a2_type == op and a2 == '(':
				# beginning of a macro function - ignore for now
				args = []
				i = 2
				while 1:
					if lst[i][1] == ')':
						return subst(lst[i+1:], defs)
					args += lst[i]
				# TODO
				#print 'macro subst'
			else:
				# not a '(', try to substitute now
				if a1 in defs:
					return defs[a1] + subst(lst[1:], defs)
				else:
					return [lst[0]] + subst(lst[1:], defs)
	return [lst[0]] + subst(lst[1:], defs)


defs = None
sym = None

def next_sym(sym):
	pass

def expect(sym):
	pass

def accept(sym):
	pass

def stringize(sym):
	pass

def eval_macro(lst, defis):
	defs = defis

	print "-------- eval macro --------"
	for x in defs:
		print x, "\t\t", defs[x]
	print "------ end eval macro ------"

	return ''

def comp(lst):
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
				if not body in self.deps:
					self.deps.append(body)
				# allow double inclusion
				self.tryfind(body)
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
		return (t[0][1], t[1:])

re_include = re.compile('^\s*(<(.*)>|"(.*)")')
def tokenize_include(txt, defs):
	def replace_v(m):
		return m.group(1)

	if re_include.search(txt):
		t = re_include.sub(replace_v, txt)
		return (t[0], t)

	# perform preprocessing and look at the result, it must match an include
	tokens = tokenize(txt)
	txt = eval_macro(tokens, defs)
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
		#print "look ", c

		if c == ' ' or c == '\t':
			# white space
			i += 1
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
		elif c == '\'':
			# char
			i += 1
			buf = []
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

		elif c in string.digits:
			# number
			buf =[]
			while i<max:
				c = txt[i]
				i += 1
				if c in string.digits: # TODO floats
					buf.append(c)
				else:
					i -= 1
					break
			abuf.append([num, ''.join(buf)])
		elif c in alpha:
			# identifier
			buf = []
			while i<max:
				c = txt[i]
				i += 1
				if c in alpha:
					buf.append(c)
				else:
					i -= 1
					break
			abuf.append([ident, ''.join(buf)])
		else:
			pos = 0
			while i<max:
				c = txt[i]
				i += 1
				if c in punctuators_table[pos].keys():
					pos = punctuators_table[pos][c]
				else:
					i -= 1
					try:
						abuf.append([op, punctuators_table[pos]['$$']])
						break
					except KeyError:
						raise PreprocError, "unknown char"
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

