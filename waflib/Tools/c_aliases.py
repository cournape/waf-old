#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2010 (ita)

"base for all c/c++ programs and libraries"

import os, sys, re, subprocess
from waflib import Utils, Build

def get_extensions(lst):
	ret = []
	for x in Utils.to_list(lst):
		try:
			ret.append(x[x.rfind('.') + 1:])
		except:
			pass
	return ret

def sniff_features(**kw):
	"""look at the source files and return the features (mainly cc and cxx)"""
	exts = get_extensions(kw['source'])
	type = kw['_type']
	print exts

	if 'cxx' in exts or 'cpp' in exts or 'c++' in exts:
		if '_type' == 'program':
			return 'cxx cxxprogram'
		if '_type' == 'shlib':
			return 'cxx cxxshlib'
		if '_type' == 'stlib':
			return 'cxx cxxstlib'
		return 'cxx'

	if 'd' in exts:
		if '_type' == 'program':
			return 'd dprogram'
		if '_type' == 'shlib':
			return 'd dshlib'
		if '_type' == 'stlib':
			return 'd dstlib'
		return 'd'

	if 'vala' in exts or 'c' in exts:
		if '_type' == 'program':
			return 'c cprogram'
		if '_type' == 'shlib':
			return 'c cshlib'
		if '_type' == 'stlib':
			return 'c cstlib'
		return 'cc'

	if 'java' in exts:
		return 'java'

	return ''

def program(bld, *k, **kw):
	"""alias for features='cc cprogram' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'program'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.program = program

def shlib(bld, *k, **kw):
	"""alias for features='cc cshlib' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'shlib'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.shlib = shlib

def stlib(bld, *k, **kw):
	"""alias for features='cc cstlib' bound to the build context"""
	if not 'features' in kw:
		kw['_type'] = 'stlib'
		kw['features'] = sniff_features(**kw)
	return bld(*k, **kw)
Build.BuildContext.stlib = stlib

