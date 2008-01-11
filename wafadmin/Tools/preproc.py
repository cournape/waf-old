#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""Waf preprocessor for finding dependencies
  because of the includes system, it is necessary to do the preprocessing in at least two steps:
  - filter the comments and output the preprocessing lines
  - interpret the preprocessing lines, jumping on the headers during the process

  In the preprocessing line step, the following actions are performed:
  - substitute the code in the functions and the defines (and use the # and ## operators)
  - reduce the expression obtained (apply the arithmetic and boolean rules)
"""

import re, sys, os, string
if __name__ == '__main__':
	sys.path = ['.', '..'] + sys.path
import Params
from Params import debug, error, warning
import traceback

class PreprocError(Exception):
	pass

g_findall = 1
'search harder for project includes'

use_trigraphs = 0
'apply the trigraph rules first'

strict_quotes = 0
"Keep <> for system includes (do not search for those includes)"

g_optrans = {
'not':'!',
'and':'&&',
'bitand':'&',
'and_eq':'&=',
'or':'||',
'bitor':'|',
'or_eq':'|=',
'xor':'^',
'xor_eq':'^=',
'compl':'~',
}
"these ops are for c++, to reset, set an empty dict"

# ignore #warning and #error
reg_define = re.compile(\
	'^[ \t]*(#|%:)[ \t]*(ifdef|ifndef|if|else|elif|endif|include|import|define|undef|pragma)[ \t]*(.*)\r*$',
	re.IGNORECASE | re.MULTILINE)
reg_pragma_once = re.compile('^\s*once\s*', re.IGNORECASE)
reg_nl = re.compile('\\\\\r*\n', re.MULTILINE)
reg_cpp = re.compile(\
	r"""(/\*[^*]*\*+([^/*][^*]*\*+)*/)|//[^\n]*|("(\\.|[^"\\])*"|'(\\.|[^'\\])*'|.[^/"'\\]*)""",
	re.MULTILINE)
trig_def = [('??'+a, b) for a, b in zip("=-/!'()<>", r'#~\|^[]{}')]

NUM   = 'i'
OP    = 'O'
IDENT = 'T'
STR   = 's'
CHAR  = 'c'

tok_types = [NUM, STR, IDENT, OP]
exp_types = [
	r"""0[xX](?P<hex>[a-fA-F0-9]+)(?P<qual1>[uUlL]*)|L*?'(?P<char>(\\.|[^\\'])+)'|(?P<n1>\d+)[Ee](?P<exp0>[+-]*?\d+)(?P<float0>[fFlL]*)|(?P<n2>\d*\.\d+)([Ee](?P<exp1>[+-]*?\d+))?(?P<float1>[fFlL]*)|(?P<n4>\d+\.\d*)([Ee](?P<exp2>[+-]*?\d+))?(?P<float2>[fFlL]*)|(?P<oct>0*)(?P<n0>\d+)(?P<qual2>[uUlL]*)""",
	r'L?"([^"\\]|\\.)*"',
	r'[a-zA-Z_]\w*',
	r'%:%:|<<=|>>=|\.\.\.|<<|<%|<:|<=|>>|>=|\+\+|\+=|--|->|-=|\*=|/=|%:|%=|%>|==|&&|&=|\|\||\|=|\^=|:>|!=|##|[\(\)\{\}\[\]<>\?\|\^\*\+&=:!#;,%/\-\?\~\.]',
]
reg_clexer = re.compile('|'.join(["(?P<%s>%s)" % (name, part) for name, part in zip(tok_types, exp_types)]), re.M)

accepted  = 'a'
ignored   = 'i'
undefined = 'u'
skipped   = 's'

def repl(m):
	s = m.group(1)
	if s is not None: return ' '
	s = m.group(3)
	if s is None: return ''
	return s

def filter_comments(filename):
	# return a list of tuples : keyword, line
	f = open(filename, "r")
	code = f.read()
	f.close()
	if use_trigraphs:
		for (a, b) in trig_def: code = code.split(a).join(b)
	code = reg_nl.sub('', code)
	code = reg_cpp.sub(repl, code)
	return [(m.group(2), m.group(3)) for m in re.finditer(reg_define, code)]

prec = {}
# op -> number, needed for such expressions:   #if 1 && 2 != 0
ops = ['. * / %', '+ -', '<< >>', '< <= >= >', '== !=', '& | ^', '&& ||', ',']
for x in range(len(ops)):
	syms = ops[x]
	for u in syms.split():
		prec[u] = x

def reduce_nums(val_1, val_2, val_op):
	#print val_1, val_2, val_op
	# pass two values, return a value

	# now perform the operation, make certain a and b are numeric
	try:    a = 0 + val_1
	except: a = int(val_1)
	try:    b = 0 + val_2
	except: b = int(val_2)

	d = val_op
	if d == '%':  c = a%b
	elif d=='+':  c = a+b
	elif d=='-':  c = a-b
	elif d=='*':  c = a*b
	elif d=='/':  c = a/b
	elif d=='|':  c = a|b
	elif d=='||': c = int(a or b)
	elif d=='&':  c = a&b
	elif d=='&&': c = int(a and b)
	elif d=='==': c = int(a == b)
	elif d=='!=': c = int(a != b)
	elif d=='<=': c = int(a <= b)
	elif d=='<':  c = int(a < b)
	elif d=='>':  c = int(a > b)
	elif d=='>=': c = int(a >= b)
	elif d=='^':  c = int(a^b)
	elif d=='<<': c = a<<b
	elif d=='>>': c = a>>b
	else: c = 0
	return c

def get_expri(lst, defs, ban):
	if not lst: return ([], [], [])

	(p, v) = lst[0]
	if p == NUM:
		return (p, v, lst[1:])

	elif p == STR:
		try:
			(p2, v2) = lst[1]
			if p2 == STR: return (p, v+v2, lst[2:])
		except IndexError: pass
		return (p, v, lst)

	elif p == OP:
		if v in ['+', '-', '~', '!']:
			(p2, v2, lst2) = get_expri(lst[1:], defs, ban)
			if p2 != NUM: raise PreprocError, "num expected %s" % str(lst)
			if v == '+': return (p2, v2, lst2)
			# TODO other cases are be complicated
			return (p2, v2, lst2)

		elif v == '#':
			(p2, v2) = lst[1]
			if p2 != IDENT: raise PreprocError, "ident expected %s" % str(lst)
			return get_expri([(STR, v2)]+lst[2:], defs, ban)

		elif v == '(':
			count_par = 0
			i = 0
			for _, v in lst:
				if v == ')':
					count_par -= 1
					if count_par == 0: break
				elif v == '(': count_par += 1
				i += 1
			else:
				raise PreprocError, "rparen expected %s" % str(lst)

			ret = process_tokens(lst[1:i], defs, ban)
			if len(ret) == 1:
				(p, v) = ret[0]
				return (p, v, lst[i+1:])
			else:
				#return (None, lst1, lst[i+1:])
				raise PreprocError, "cannot reduce %s" % str(lst)

	elif p == IDENT:
		if len(lst)>1:
			(p2, v2) = lst[1]
			if v2 != "##": return (p, v, lst)
			# token pasting
			(p3, v3) = lst[2]
			if p3 != IDENT: raise PreprocError, "expected ident after ## %s" % str(lst)
			return get_expri([(p, v+v3)]+lst[3:], defs, ban)
		return (p, v, lst)

def process_tokens(lst, defs, ban):
	accu = []
	while lst:
		p, v, nlst = get_expri(lst, defs, ban)
		if p == NUM:
			if not nlst: return [(p, v)] # finished

			op1, ov1 = nlst[0]
			if op1 != OP: raise PreprocError, "op expected %s" % str(lst)

			if ov1 == '?':
				i = 0
				count_par = 0
				for _, k in nlst:
					if   k == ')': count_par -= 1
					elif k == '(': count_par += 1
					elif k == ':' and count_par == 0: break
					i += 1
				else: raise PreprocError, "ending ':' expected %s" % str(lst)

				if reduce_nums(v, 0, '+'): lst = nlst[1:i]
				else: lst = nlst[i+1:]
				continue

			elif ov1 == ',':
				lst = nlst[1:]
				continue

			p2, v2, nlst = get_expri(nlst[1:], defs, ban)
			if p2 != NUM: raise PreprocError, "num expected after op %s" % str(lst)
			if nlst:
				# op precedence
				op3, ov3 = nlst[0]
				if prec[ov3] < prec[ov1]:
					#print "ov3", ov3, ov1
					# as needed
					p4, v4, nlst2 = get_expri(nlst[1:], defs, ban)
					v5 = reduce_nums(v2, v4, ov3)
					lst = [(p, v), (op1, ov1), (NUM, v5)] + nlst2
					continue

			# no op precedence or empty list, reduce the first tokens
			lst = [(NUM, reduce_nums(v, v2, ov1))] + nlst
			continue

		elif p == STR:
			if nlst: raise PreprocError, "sequence must terminate with a string %s" % str(lst)
			return [(p, v)]

		elif p == IDENT:
			if v.lower() == 'defined':
				(p2, v2) = nlst[1]
				off = 2
				if v2 == '(':
					(p3, v3) = nlst[2]
					if p3 != IDENT: raise PreprocError, 'expected an identifier after a "defined("'
					(p2, v2) = nlst[3]
					if v2 != ')': raise PreprocError, 'expected a ")" after a "defined(x"'
					off = 4
				elif p2 != IDENT:
					raise PreprocError, 'expected a "(" or an identifier after a defined'

				x = 0
				if v2 in defs: x = 1
				lst = [(NUM, x)] + nlst[off:]
				continue

			elif not v in defs:
				raise PreprocError, 'undefined macro or function "%s"' % v

			macro_def = defs[v]
			if not macro_def[0]:
				# simple macro, substitute
				lst = macro_def[1] + nlst[1:]
				continue
			else:
				# TODO function calls
				pass

		return (None, None, [])



def get_expr(tokens):
	if len(tokens) == 0: return (None, None, tokens)
	lst = []+tokens
	(tok, val) = lst.pop(0)
	if tok == NUM:
		return (tok, val, lst)
	elif tok == OP:
		if val == '!' or val == '~': # TODO handle bitwise complement
			(tok2, val2, lst2) = get_expr(lst)
			v = int(val2)
			if v == 0: v = 1
			else:      v = 0
			return (NUM, v, lst2)
		elif val == '-' or val == '+':
			(tok2, val2, lst2) = get_expr(lst)
			if val == '-': v = - int(val2)
			return (NUM, v, lst2)
		elif val == '(':
			count_par = 0
			accu = []
			while 1:
				(tok, val) = lst.pop(0)
				if tok == OP:
					if val == ')':
						if count_par == 0: break
						else: count_par -= 1
					elif val == '(':
						count_par += 1
				accu.append( (tok, val) )
			(tok_tmp, val_tmp) = reduce_tokens(accu)[0]
			return (tok_tmp, val_tmp, lst)
	else:
		pass
	raise PreprocError, "could not get an expression from %s" % tokens

def reduce_recurse(val_a, op_1, val_b, op_2, val_c, tokens):
	if prec[op_1] < prec[op_2]:
		val_a = reduce_nums(val_a, val_b, op_1)
		if tokens:
			(tok_new, op_new) = tokens.pop(0)
			(tok_d, val_d, new_list) = get_expr(tokens)
			return reduce_recurse(val_a, op_2, val_c, op_new, val_d, new_list)
		else:
			val_a = reduce_nums(val_a, val_c, op_2)
			return (NUM, val_a)
	else:
		val_b = reduce_nums(val_b, val_c, op_2)
		if tokens:
			# now the annoying case
			(tok_new, op_new) = tokens.pop(0)
			(tok_d, val_d, new_list) = get_expr(tokens)
			return reduce_recurse(val_a, op_1, val_b, op_new, val_d, new_list)
		else:
			val_a = reduce_nums(val_a, val_b, op_1)
			return (NUM, val_a)

def reduce_tokens(tokens):
	if not tokens: return [(STR, '')]
	if len(tokens) == 1: return tokens

	lst = []+tokens
	# if the expression cannot be reduced, just return the tokens

	try:
		(tok_a, val_a, lst1) = get_expr(lst)
		if (not tok_a) or tok_a == IDENT: return tokens
		if not lst1:
			return [(tok_a, val_a)]
		(tok_1, val_1) = lst1.pop(0)
		if tok_1 != OP: return tokens

		(tok_b, val_b, lst2) = get_expr(lst1)
		if (not tok_b) or tok_b == IDENT: return tokens
		if not lst2:
			val_a = reduce_nums(val_a, val_b, val_1)
			return [(tok_a, val_a)]
		(tok_2, val_2) = lst2.pop(0)
		if tok_2 != OP: return tokens

		(tok_c, val_c, lst3) = get_expr(lst2)
		if (not tok_c) or tok_c == IDENT: return tokens

		(tok, val) = reduce_recurse(val_a, val_1, val_b, val_2, val_c, lst3)
		return [(tok, val)]
	except PreprocError:
		return tokens

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
		(tok, val) = fun_code.pop(0)
		if tok == OP:
			if val == '#':
				# the next token is one of the args
				(tok_next, val_next) = fun_code.pop(0)
				tokens = params[param_index[val_next]]
				# macro parameter evaluation is postponed
				ret = eval_tokens(tokens, defs, ban+[name])
				ret = (STR, "".join([str(y) for (x,y) in ret]))
				accu.append(ret)

			elif val == '##':
				# the next token is an identifier (token pasting)
				(tok_next, val_next) = fun_code.pop(0)
				(tok_back, val_back) = accu[-1]
				accu = accu[:-1]
				new_token = (IDENT, val_back+val_next)
				accu.append(new_token)
				# FIXME this supposes that "a##b(foo)" evaluates as "ab(foo)"
			else:
				accu.append((tok, val))

		elif tok == IDENT:
			if val in param_index:
				code = params[param_index[val]]
				accu += eval_tokens(code, defs, ban+[name])
			else:
				accu.append((tok, val))
		else:
			accu.append((tok, val))

	ret = eval_tokens(accu, defs, ban+[name])
	return ret

def eval_tokens(lst, adefs, ban=[]):
	#print "lst is ", lst
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
		(tok, val) = lst.pop(0)

		if tok == IDENT and val.lower() == 'defined':
			# "defined(identifier)" or "defined identifier"
			(tok, val) = lst.pop(0)
			if val == '(':
				(tok, val_x) = lst.pop(0)
				if tok != IDENT: raise PreprocError, 'expected an identifier after a defined'
				(tok, val) = lst.pop(0)
				if val != ')': raise PreprocError, 'expected a ")" after a defined'
			elif tok == IDENT:
				val_x = val
			else:
				raise PreprocError, 'expected a "(" or an identifier after a defined'

			if val_x in adefs: accu.append((NUM, 1))
			else: accu.append((NUM, 0))

		elif tok == IDENT and val in adefs:
			# the identifier is a macro
			name = val

			fun_def = adefs[val]
			fun_args=[]
			if fun_def: fun_args = fun_def[0]
			if fun_args == None:
				# simple macro
				# make the substitution
				lst = fun_def[1] + lst
			else:
				# function call, collect the arguments
				params = []
				tmp = []
				(tok, val) = lst.pop(0)
				if tok != OP or val != '(': raise ParseError, "invalid function call "+name
				count_paren = 0
				while 1:
					(tok, val) = lst.pop(0)
					# stop condition
					if count_paren == 0 and tok == OP:
						if val == ')':
							if tmp: params.append(tmp)
							break
						elif val == ',':
							if not tmp: raise ParseError, "invalid function call "+name
							params.append(tmp)
							tmp = []
							continue

					# all other cases we just append the tokens to tmp
					tmp.append((tok, val))

					# but watch out for the matching parenthesis
					if tok == OP:
						if val == '(':
							count_paren += 1
						elif val == ')':
							count_paren -= 1

				accu += eval_fun(name, params, adefs)
		else:
			accu.append((tok, val))

	# now reduce the expressions if possible, like 1+1->2, no more evaluation should take place
	accu = reduce_tokens(accu)
	return accu

def eval_macro(lst, adefs):
	# look at the result, and try to return a 0/1 result
	ret = eval_tokens(lst, adefs, [])

	if len(ret) == 0:
		debug("could not evaluate %s to true or false (empty list)" % str(ret), 'preproc')
		return False
	if len(ret) > 1:
		debug("could not evaluate %s to true or false (could not reduce the expression)" % str(ret), 'preproc')
		return False
	if len(ret) == 1:
		(tok, val) = ret[0]
		if tok == NUM:
			r = int(val)
			return r != 0
		elif tok == IDENT:
			if val.lower() == 'true': return True
			elif val.lower() == 'false': return False
			else: "could not evaluate %s to true or false (not a boolean)" % str(lst)
		else:
			debug("could not evaluate %s to true or false (not a number/boolean)" % str(lst), 'preproc')
	return ret

def try_exists(node, list):
	lst = []+list
	while lst:
		name = lst.pop(0)
		# it is not a build node, else we would already got it
		path = os.path.join(node.abspath(), name)
		try: os.stat(path)
		except OSError:
			#traceback.print_exc()
			return None
		node = node.find_dir_lst([name])
	return node

class cparse(object):
	def __init__(self, nodepaths=None, strpaths=None, defines=None):
		#self.lines = txt.split('\n')
		self.lines = []

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
		global g_findall
		if self.m_nodepaths:
			found = 0
			for n in self.m_nodepaths:
				found = n.find_source(filename, create=0)
				if found:
					break
			# second pass for unreachable folders
			if not found and g_findall:
				lst = filename.split('/')
				if len(lst)>1:
					lst=lst[:-1] # take the folders only
					try: cache = Params.g_build.preproc_cache
					except AttributeError:
						cache = {}
						setattr(Params.g_build, 'preproc_cache', cache)
					key = hash( (str(self.m_nodepaths), str(lst)) )
					if not cache.get(key, None):
						cache[key] = 1
						for n in self.m_nodepaths:
							node = try_exists(n, lst)
							if node:
								found = n.find_source(filename, create=0)
								if found: break
			if found:
				self.m_nodes.append(found)
				# Qt
				if filename[-4:] != '.moc': self.addlines(found.abspath(self.env))
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
                debug("reading file %r" % filepath, 'preproc')
		if filepath in pc.keys():
			self.lines = pc[filepath] + self.lines
			return

		try:
			lines = filter_comments(filepath)
			pc[filepath] = lines # memorize the lines filtered
			self.lines = lines + self.lines
		except IOError:
			raise PreprocError, "could not read the file %s" % filepath
		except Exception:
			if Params.g_verbose > 0:
				warning("parsing %s failed" % filepath)
				traceback.print_exc()

	def start(self, node, env):
		debug("scanning %s (in %s)" % (node.m_name, node.m_parent.m_name), 'preproc')

		self.env = env
		variant = node.variant(env)

		self.addlines(node.abspath(env))
		if env['DEFLINES']:
			self.lines = [('define', x) for x in env['DEFLINES']] + self.lines

		while self.lines:
			# TODO we can skip evaluating conditions (#if) only when we are
			# certain they contain no define, undef or include
			(type, line) = self.lines.pop(0)
			try:
				self.process_line(type, line)
			except Exception, ex:
				if Params.g_verbose:
					warning("line parsing failed (%s): %s" % (str(ex), line))
                                        traceback.print_exc()

	# debug only
	def start_local(self, filename):
		self.addlines(filename)
		#print self.lines
		while self.lines:
			(type, line) = self.lines.pop(0)
			try:
				self.process_line(type, line)
			except Exception, ex:
				if Params.g_verbose:
					warning("line parsing failed (%s): %s" % (str(ex), line))
                                        traceback.print_exc()
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
				#print "return in process line"
				return

		def get_name(line):
			ret = tokenize(line)
			for (x, y) in ret:
				if x == IDENT: return y
			return ''

		if token == 'if':
			ret = eval_macro(tokenize(line), self.defs)
			if ret: self.state[0] = accepted
			else: self.state[0] = ignored
		elif token == 'ifdef':
			name = get_name(line)
			if name in self.defs.keys(): self.state[0] = accepted
			else: self.state[0] = ignored
		elif token == 'ifndef':
			name = get_name(line)
			if name in self.defs.keys(): self.state[0] = ignored
			else: self.state[0] = accepted
		elif token == 'include' or token == 'import':
			(type, inc) = extract_include(line, self.defs)
			debug("include found %s    (%s) " % (inc, type), 'preproc')
			if type == '"' or not strict_quotes:
				if not inc in self.deps:
					self.deps.append(inc)
				# allow double inclusion
				self.tryfind(inc)
		elif token == 'elif':
			if self.state[0] == accepted:
				self.state[0] = skipped
			elif self.state[0] == ignored:
				if eval_macro(tokenize(line), self.defs):
					self.state[0] = accepted
		elif token == 'else':
			if self.state[0] == accepted: self.state[0] = skipped
			elif self.state[0] == ignored: self.state[0] = accepted
		elif token == 'endif':
			self.state.pop(0)
		elif token == 'define':
			(name, val) = extract_define(line)
			debug("define %s   %s" % (name, str(val)), 'preproc')
			self.defs[name] = val
		elif token == 'undef':
			name = get_name(line)
			if name and name in self.defs:
				self.defs.__delitem__(name)
				#print "undef %s" % name
		elif token == 'pragma':
			if reg_pragma_once.search(line.lower()):
				pass
				#print "found a pragma once"

re_function = re.compile('^[a-zA-Z_][a-zA-Z0-9_]*[(]')
def extract_define(txt):
	t = tokenize(txt)
	if re_function.search(txt):
		# this means we have a function
		params = []
		(tok, val) = t.pop(0)
		name = val

		(tok, val) = t.pop(0)
		if tok != OP: raise PreprocError, "expected open parenthesis"
		while 1:
			(tok, val) = t.pop(0)

			if tok == OP and val == ')':
				break
			if tok != IDENT and (tok != OP and val != '...'):
				raise PreprocError, "expected ident"

			(tok2, val2) = t.pop(0)
			if tok2 == OP and val2 == '...':
				params.append((IDENT, val+val2)) # to get the varargs "z..."
			elif tok2 == OP and val2 == ')':
				if tok == IDENT:
					params.append((tok, val))
				else:
					params.append((IDENT, val))
				break
			elif tok2 == OP and val2 == ',':
				params.append((tok, val))
			else:
				raise PreprocError, "unexpected token "+str((tok2, val2))

		return (name, [params, t])
	else:
		(tok, val) = t.pop(0)
		return (val, [None, t])

re_include = re.compile('^\s*(<(.*)>|"(.*)")\s*')
def extract_include(txt, defs):
	def replace_v(m):
		return m.group(1)

	if re_include.search(txt):
		t = re_include.sub(replace_v, txt)
		return (t[0], t[1:-1])

	# perform preprocessing and look at the result, it must match an include
	tokens = tokenize(txt)
	ret = eval_tokens(tokens, defs)
	(tok, val) = ret[0]
	if len(ret) == 1 and tok == STR:
		# a string token, quote it
		txt = '"%s"' % val
	elif tok == OP:
		# a list of tokens, such as <,iostream,.,h,>, concatenate
		txt = "".join([y for (x, y) in ret])
		# TODO if we discard whitespaces, we could test for val == "<"
	else:
		raise PreprocError, "could not parse %s" % str(ret)

	if re_include.search(txt):
		t = re_include.sub(replace_v, txt)
		return (t[0], t[1:-1])

	# if we come here, parsing failed
	raise PreprocError, "include parsing failed %s" % txt

def parse_char(txt):
	# TODO way too complicated!
	try:
		if not txt: raise PreprocError
		if txt[0] != '\\': return ord(txt)
		c = txt[1]
		if c in "ntbrf\\'": return ord(eval('"\\%s"' % c)) # FIXME eval is slow and  ugly
		elif c == 'x':
			if len(txt) == 4 and txt[3] in string.hexdigits: return int(txt[2:], 16)
			return int(txt[2:], 16)
		elif c.isdigit():
			for i in 3, 2, 1:
				if len(txt) > i and txt[1:1+i].isdigit():
					return (1+i, int(txt[1:1+i], 8))
		else:
			raise PreprocError
	except:
		raise PreprocError, "could not parse char literal '%s'" % v

def tokenize(s):
	ret = []
	for match in reg_clexer.finditer(s):
		m = match.group
		for name in tok_types:
			v = m(name)
			if v:
				if name == IDENT:
					try: v = g_optrans[v]; name = OP
					except KeyError:
						# c++ specific
						if v.lower() == "true":
							v = 1
							name = NUM
						elif v.lower() == "false":
							v = 0
							name = NUM
				elif name == NUM:
					if m('oct'): v = int(v, 8)
					elif m('hex'): v = int(m('hex'), 16)
					elif m('n0'): v = m('n0')
					else:
						v = m('char')
						if v: v = parse_char(v)
						else: v = m('n2') or m('n4')
# till i manage to understand what it does exactly (ita)
#					#if v[0] == 'L': v = v[1:]
#					r = parse_literal(v[1:-1])
#					if r[0]+2 != len(v):
#						raise PreprocError, "could not parse char literal %s" % v
#					v = r[1]
				elif name == OP:
					if v == '%:': v='#'
					elif v == '%:%:': v='##'

				ret.append((name, v))
				break
	return ret

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
	f = open(arg, "r"); txt = f.read(); f.close()

	d1 = [[], [(NUM, 1), (OP, '+'), (NUM, 2)]]

	def test(x):
		y = process_tokens(tokenize(x), {'d1':d1}, [])
		print x, y

	test("0&&2<3")
	test("(5>1)*6")
	test("1+2+((3+4)+5)+6==(6*7)/2==1*-1*-1")
	test("1,2,3*9,9")
	test("1?77:88")
	test("0?77:88")
	test("1?1,(0?5:9):3,4")
	test("defined inex")
	test("defined(inex)")
	try: test("inex")
	except: print "inex is not defined"
	test("d1*3")


	"""
	gruik = cparse(strpaths = paths)
	gruik.start_local(arg)
	print "we have found the following dependencies"
	print gruik.deps
	print gruik.deps_paths

	"""
	#f = open(arg, "r")
	#txt = f.read()
	#f.close()
	#print tokenize(txt)

