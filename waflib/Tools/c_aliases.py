#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re, subprocess
from waflib import Utils, Build

def sniff_features(**kw):
	"""look at the source files and return the features (mainly cc and cxx)"""
	has_c = False
	has_cxx = False
	s = Utils.to_list(kw['source'])
	for name in s:
		if name.endswith('.c'):
			has_c = True
		elif name.endswith('.cxx') or name.endswith('.cpp') or name.endswith('.c++'):
			has_cxx = True
	lst = []
	if has_c:
		lst.append('cc')
	if has_cxx:
		lst.append('cxx')
	return lst

def program(bld, *k, **kw):
	"""alias for features='cc cprogram' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cprogram'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.program = program

def shlib(bld, *k, **kw):
	"""alias for features='cc cshlib' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cshlib'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.shlib = shlib

def stlib(bld, *k, **kw):
	"""alias for features='cc cstlib' bound to the build context"""
	if not 'features' in kw:
		kw['features'] = ['cstlib'] + sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.stlib = stlib

