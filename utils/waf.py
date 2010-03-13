#!/usr/bin/env python
# Python generic wrapper for running extensionless python scripts under windows.
# Sorin Sbarnea, 2010

import os, sys

filename = os.path.splitext(os.path.basename(sys.argv[0]))[0]

if not os.path.exists(filename):
	# filename does not exists, emulate cmd behaviour
	sys.stderr.write("'%s' is not recognized as an internal or external command,\noperable program or batch file." % filename)
	sys.exit(9009)
ret = os.system('python %s %s' % (filename, " ".join(sys.argv[1:])))
sys.exit(ret)

