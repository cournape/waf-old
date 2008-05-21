#! /usr/bin/env python

import os
os.popen("python setup.py build && ln -s build/lib*/fnv.so .").read()

import fnv

x = fnv.new()
for num in xrange(15):
	x.update("blahla")
	print x.digest()



