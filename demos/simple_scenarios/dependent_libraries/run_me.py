#! /usr/bin/env python

# This script runs waf in the libs and app directories...
# Their purpose is to demonstrate confugring of dependent libraries.

import os, sys

def print_it(msg):
    print  "\n", msg, "\n", "=" * 80

# make sure we start in the right place
curdir = os.path.abspath(os.path.curdir)
main_dir = os.path.abspath(os.path.dirname(sys.argv[0]))
os.chdir(main_dir)

# start from clean
os.chdir("libs")
os.system("waf distclean")

# configure & build the libs
print_it("configuring and building the libs")
os.system("waf configure")
os.system("waf")

os.chdir(main_dir)
os.chdir("app")

# configure the app - run the tests with the libs built before
print_it("configuring the app")
os.system("waf configure")

os.chdir(curdir)
