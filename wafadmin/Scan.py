#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, re
import Params, Node
from Params import debug, error, trace, fatal

#cregexp='^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")'
#cregexp1 = re.compile('^[ \t]*#[ \t]*(?:include)[ \t]*(<|")([^>"]+)(>|")', re.M)
cregexp1 = re.compile(r'^[ \t]*#[ \t]*(?:include)[ \t]*(?:/\*.*?\*/)?[ \t]*(<|")([^>"]+)(>|")', re.M)
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
	trace("c_scanner gcc called for "+str(node))

	def getincl(p):
		return '-I%s' % p.abspath()

	includes = " ".join(map(getincl, path_lst))
	includes += "  -I/opt/kde3/include -I/usr/lib/qt3/include -I/compilation/playground/edu/kdissert/_build_/src/kdissert/"

	print '/usr/bin/g++ -MG -MMD %s %s 2>/dev/null' % (node.abspath(), includes)

	res = os.popen('/usr/bin/g++ -M %s %s ' % (node.abspath(), includes)).readlines()

	lst2 = map(lambda a: a.strip().rstrip('\\'), res)
	lst2 = " ".join(lst2)



	print " ".join(res)

	print "\n\n\n"
	print lst2


	lst2 = lst2.split()
	lst2 = lst2[2:]



	def getname(a):
		lst=a.split('/')
		return lst[len(lst)-1]

	lst2 = map(getname, lst2)
	print lst2

	names = []
	nodes = []
	for name in lst2:
		found = None
		for dir in path_lst:
			found = dir.find_node([name])
			if found:
				break
		if found: nodes.append(found)
		else:     names.append(name)
	print "-E ", nodes, names
	return (nodes, names)

def c_scanner(node, path_lst):
	file = open(node.abspath(), 'rb')
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
			for node in dir.m_files:
				if node.m_name == name:
					found = node
					break
			if found:
				break
		if found: nodes.append(found)
		else:     names.append(name)
	#print "-S ", nodes, names
	return (nodes, names)

def kcfg_scanner(node, path_lst):
	trace("kcfg scanner called for "+str(node))
	file = open(node.abspath(), 'rb')
	found = kcfg_regexp.findall( file.read() )
	file.close()

	if not found:
		fatal("no kcfg file found when scanning the .kcfgc- that's very bad")

	name = found[0]
	for dir in path_lst:
		for node in dir.m_files:
			if node.m_name == name:
				return ([node], found)
	fatal("the kcfg file was not found - that's very bad")

def add_scanner(name, fun, recurse=0):
	Params.g_scanners[name] = fun
	if recurse: Params.g_recursive_scanners_names.append(name)
	print ( "scanner function added: %s" % (name) )

