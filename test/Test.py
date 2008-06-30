#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Some waf tests - most are obsolete"

import os, sys

class DIRS:
	WAFADMIN 	= "wafadmin"
	WAF			= "waf"
	DEMOS		= "demos"
	TOOLS		= "Tools"

# allow importing from wafadmin dir.
wafadmin = os.path.join(os.path.abspath(os.path.pardir), DIRS.WAFADMIN)
sys.path.append(wafadmin)

import Options
import Utils

def info(msg):
	Utils.pprint('CYAN', msg)

def testname(file, tests_dir='test'):
	test_file=os.path.join(tests_dir, file)
	return open(test_file, 'r')

def run_tests():
	# could be run from test dir only !
	import build_dir as test_build_dir
	import cxx_test as test_cxx
	import gcc_test as test_gcc
	import configure_test as test_configure

	if Options.options:
		verbose = Options.options.verbose
	else:
		verbose = 1

	for i in ['dist','configure','clean','distclean','make','install','doc']:
		Options.commands[i]=0
		
	info("******** Configure tests ********")
	test_configure.run_tests(verbose)
	info("******** build dir tests ********")
	test_build_dir.run_tests(verbose)
	info("******** g++ tests ********")
	test_cxx.run_tests(verbose)
	info("******** gcc tests ********")
	test_gcc.run_tests(verbose)

if __name__ == "__main__":
	# XXX: not works !
	os.chdir(os.path.pardir)
	run_tests()
