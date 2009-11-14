#! /usr/bin/env python

"""
copies the input as output
"""

import sys, os

file = open(sys.argv[1], 'rb')
txt = file.read()
file.close()

file = open(sys.argv[2], 'wb')
file.write(txt)
file.close()
