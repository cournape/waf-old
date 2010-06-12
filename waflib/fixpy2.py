#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

"""
burn a book, save a tree
"""

import os
all_modifs = {}

def fixdir(dir):
	global all_modifs
	for k in all_modifs:
		for v in all_modifs[k]:
			modif(os.path.join(dir, 'waflib'), k, v)

def modif(dir, name, fun):
	if name == '*':
		lst = []
		for y in '. Tools extras'.split():
			for x in os.listdir(os.path.join(dir, y)):
				if x.endswith('.py'):
					lst.append(y + os.sep + x)
		for x in lst:
			modif(dir, x, fun)
		return

	filename = os.path.join(dir, name)
	f = open(filename, 'r')
	txt = f.read()
	f.close()

	txt = fun(txt)

	f = open(filename, 'w')
	f.write(txt)
	f.close()

def subst(*k):
	def do_subst(fun):
		global all_modifs
		for x in k:
			try:
				all_modifs[x].append(fun)
			except KeyError:
				all_modifs[x] = [fun]
		return fun
	return do_subst

@subst('*')
def r0(code):
	code = code.replace('as e:', ',e:')
	code = code.replace(".decode('utf-8')", '')
	code = code.replace('.encode()', '')
	return code

@subst('Utils.py')
def r1(code):
	code = code.replace("b'iluvcuteoverload'", "'iluvcuteoverload'")
	return code

