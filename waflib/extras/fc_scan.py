#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

import re

from waflib import Utils, Task, TaskGen, Logs
from waflib.TaskGen import feature, before, after, extension
from waflib.Configure import conf

INCLUDE_REGEX = """(?:^|['">]\s*;)\s*INCLUDE\s+(?:\w+_)?[<"'](.+?)(?=["'>])"""
USE_REGEX = """(?:^|;)\s*USE(?:\s+|(?:(?:\s*,\s*(?:NON_)?INTRINSIC)?\s*::))\s*(\w+)"""

EXT_MOD = ".mod"
EXT_FC = ".f"
EXT_FCPP = ".F"
EXT_OBJ = ".o"

# TODO:
#   - handle pre-processed files (FORTRANPPCOM in scons)
#   - handle modules
#   - handle multiple dialects
#   - windows...

class fortran_parser(object):
	def __init__(self, incpaths, modsearchpath):
		self.allnames = []

		self.re_inc = re.compile(INCLUDE_REGEX, re.IGNORECASE)
		self.re_use = re.compile(USE_REGEX, re.IGNORECASE)

		self.nodes = []
		self.names = []
		self.modules = []

		self.incpaths = incpaths
		# XXX:
		self.modsearchpath = modsearchpath

	def tryfind_header(self, filename):
		found = 0
		for n in self.incpaths:
			found = n.find_resource(filename)
			if found:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)

	def tryfind_module(self, filename):
		found = 0
		for n in self.modsearchpath:
			found = n.find_resource(filename + EXT_MOD)
			if found:
				self.nodes.append(found)
				self.waiting.append(found)
				break
		if not found:
			if not filename in self.names:
				self.names.append(filename)

	def find_deps(self, code):
		headers = []
		modules = []
		for line in code.readlines():
			m = self.re_inc.search(line)
			if m:
				headers.append(m.group(1))
			m = self.re_use.search(line)
			if m:
				modules.append(m.group(1))
		return headers, modules

	def start(self, node):
		self.waiting = [node]
		# while the stack is not empty, add the dependencies
		while self.waiting:
			nd = self.waiting.pop(0)
			self.iter(nd)

	def iter(self, node):
		path = node.abspath() # obtain the absolute path
		code = open(path, 'r')
		hnames, mnames = self.find_deps(code)
		for x in hnames:
			# optimization
			if x in self.allnames:
				continue
			self.allnames.append(x)

			# for each name, see if it is like a node or not
			self.tryfind_header(x)

		for x in mnames:
			# optimization
			if x in self.allnames:
				continue
			self.allnames.append(x)

			# for each name, see if it is like a node or not
			self.tryfind_module(x)

def scan(self):
	tmp = fortran_parser(self.generator.includes_nodes, self.env["MODULE_SEARCH_PATH"])
	tmp.start(self.inputs[0])
	if Logs.verbose:
		Logs.debug('deps: deps for %r: %r; unresolved %r' % (self.inputs, tmp.nodes, tmp.names))
	return (tmp.nodes, tmp.names)

