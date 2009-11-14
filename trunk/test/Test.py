#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)
# Yinon Ehrlich, 2008, 2009

"Some waf tests"

import os
import sys
import imp
import time

class DIRS:
	WAFADMIN	= "wafadmin"
	WAF			= "waf"
	DEMOS		= "demos"
	TOOLS		= "Tools"

# allow importing from wafadmin dir.
wafadmin = os.path.join(os.path.abspath(os.path.pardir), DIRS.WAFADMIN)
waftools = os.path.join(wafadmin, DIRS.TOOLS)
sys.path = [wafadmin, waftools] + sys.path

import Options
import Utils

# shortcut
writelines = sys.stderr.write

def info(msg):
	Utils.pprint('CYAN', msg)

def testname(file, tests_dir='test'):
	test_file=os.path.join(tests_dir, file)
	return open(test_file, 'r')

def run_tests():
	if Options.options:
		verbose = Options.options.verbose
	else:
		verbose = 1

	tests_modules = '''configure_test build_dir cxx_test gcc_test ar_test
wscript_errors_test scripting build options task_gen'''.split()

	all_results = []
	not_passed = []
	total = 0
	t1 = time.time()
	
	curdir = os.path.dirname(__file__)
	sys.path.append(curdir)

	for test in tests_modules:
		mod = imp.load_source(test, os.path.join(curdir, test + '.py'))
		writelines("******** %s ********\n" % mod.__name__)

		# run_tests return a TestResult instance
		result = mod.run_tests(verbose)
		total += result.testsRun

		# accumulate results for future stat etc.
		if not result.wasSuccessful():
			not_passed += (result.failures + result.errors)

		# TODO: all_results is not used now, may be used for further investigation...
		all_results.append(result)

	writelines('\n' + '='*80 + '\n')
	if not_passed:
# 		for t in not_passed:
# 			writelines( "%s: %s\n" % (t[0]._testMethodName, t[1]) )
		writelines( "\n%d (out of %d) tests didn't passed !" %		(len(not_passed), total) )
	else:
		writelines( "\nall tests (%d) passed successfully !\n" % total )
	t2 = time.time()
	elapsed = t2-t1
	writelines('\nall tests took %.2f seconds.\n' % elapsed)
	writelines('='*80 + '\n')


	return len(not_passed)


if __name__ == "__main__":
	# XXX: not works !
	os.chdir(os.path.pardir)
	sys.exit(run_tests())
