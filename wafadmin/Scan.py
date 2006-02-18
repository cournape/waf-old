#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import re
import Params
import Node

def trace(msg):
        Params.trace(msg, 'Scan')
def debug(msg):
	Params.debug(msg, 'Scan')
def error(msg):
	Params.error(msg, 'Scan')

#cregexp='^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")'
cregexp1 = re.compile('^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")', re.M)
cregexp2 = re.compile('^[ \t]*#[ \t]*(?:include)[ \t]*"([^>"]+)"', re.M)
cregexp3 = re.compile('^[ \t]*#[ \t]*(?:include|import)[ \t]*(<|")([^>"]+)(>|")', re.M)

kcfg_regexp = re.compile('[fF]ile\s*=\s*(.+)\s*', re.M)

# A scanner function takes as input a node and a list of paths
# it searches dependencies in the paths, and returns a list of nodes
# that should trigger a rebuild.

# A scanner function returns a list of nodes and a list of filenames

# this example does not return anything
def dummy_scanner(node, path_lst):
	error("dummy scanner called, this one does nothing")
	return []

def c_scanner(node, path_lst):
	trace("c_scanner called for "+str(node))

	file = open(node.abspath(), 'rb')
	found = cregexp1.findall( file.read() )
	file.close()

	nodes = []
	names = []
	for (_, name, _) in found:
		#print 'boo', name

		# quite a few nested 'for' loops, looking suspicious
		found = None
		for dir in path_lst:
			for node in dir.m_files:
				if node.m_name == name:
					found = node
					break
			if found:
				break
		if found: nodes.append(found)
		else:     names.append(name)
	return (nodes, names)

def kcfg_scanner(node, path_lst):
	trace("kcfg scanner called for "+str(node))
	file = open(node.abspath(), 'rb')
	found = kcfg_regexp.findall( file.read() )
	file.close()

	if not found:
		error("no kcfg file found when scanning the .kcfgc- that's very bad")
		import sys
		sys.exit(1)

	name = found[0]
	for dir in path_lst:
		for node in dir.m_files:
			if node.m_name == name:
				return ([node], found)
	error("the kcfg file was not found - that's very bad")
	sys.exit(1)

def add_scanner(name, fun, recurse=0):
	Params.g_scanners[name] = fun
	if recurse: Params.g_recursive_scanners_names.append(name)
	print ( "scanner function added: %s" % (name) )

