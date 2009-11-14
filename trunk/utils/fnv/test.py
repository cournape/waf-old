#!/usr/bin/env python

import os
os.popen("python setup.py build && ln -s build/lib*/fnv.so .").read()

import fnv

x = fnv.new()
print x
for num in xrange(15):
	x.update("this is a test")
	print x.hexdigest()

