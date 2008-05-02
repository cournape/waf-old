#! /usr/bin/env python

"""
example of an ill-behaving compiler
* the output files cannot be known in advance
* the output file names are written to stdout
"""

import sys, os
name = sys.argv[1]
file = open(name, 'r')
txt = file.read()
file.close()

lst = txt.split('\n')
for line in lst:
	fname = line.strip()
	if not fname: continue
	(dirs, name) = os.path.split(fname)
	try:
		os.makedirs(dirs)
	except:
		pass
	file = open(fname, 'w')
	varname = name.replace('.', '_')
	file.write('const char* k%s = "%s";\n' % (varname, fname))
	file.close()

	print fname

