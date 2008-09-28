#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)
# Yinon Ehrlich, 2008

"Some waf tests - most are obsolete"

import os, sys

class DIRS:
	WAFADMIN	= "wafadmin"
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
	import build_dir
	import cxx_test
	import gcc_test
	import configure_test
	import wscript_errors_test
	import scripting
	import build
	import options
	import task_gen

	if Options.options:
		verbose = Options.options.verbose
	else:
		verbose = 1

	tests_modules = [configure_test, build_dir, cxx_test, gcc_test,
						wscript_errors_test, scripting, build, options, task_gen]

	for mod in tests_modules:
		info("******** %s ********" % mod.__name__)
		mod.run_tests(verbose)

if __name__ == "__main__":
	# XXX: not works !
	os.chdir(os.path.pardir)
	run_tests()
