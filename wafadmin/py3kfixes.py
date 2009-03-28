#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2009 (ita)

"""
Fixes for py3k go here
"""

all_modifs = {}

def modif(filename, fun):
	f = open(filename, 'r')
	txt = f.read()
	f.close()

	txt = fun(txt)

	f = open(filename, 'w')
	f.write(txt)
	f.close()

def subst(filename):
	def do_subst(fun):
		try:
			all_modifs[filename] += fun
		except KeyError:
			all_modifs[filename] = fun
		return fun
	return do_subst

@subst('Constants.py')
def r1(code):
	return code.replace("'iluvcuteoverload'", "b'iluvcuteoverload'")

@subst('Tools/ccroot.py')
def r2(code):
	code = code.replace("p.stdin.write('\\n')", "p.stdin.write(b'\\n')")
	code = code.replace("out=str(out)", "out=out.decode('utf-8')")
	return code

@subst('Utils.py')
def r3(code):
	code = code.replace("m.update(str(lst))", "m.update(str(lst).encode())")
	return code

@subst('Task.py')
def r4(code):
	code = code.replace("up(self.__class__.__name__)", "up(self.__class__.__name__.encode())")
	code = code.replace("up(self.env.variant())", "up(self.env.variant().encode())")
	code = code.replace("up(x.parent.abspath())", "up(x.parent.abspath().encode())")
	code = code.replace("up(x.name)", "up(x.name.encode())")
	return code

