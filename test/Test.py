#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Some waf tests - most are obsolete"

import os
import Params

class DIRS:
	WAFADMIN 	= "wafadmin"
	WAF			= "waf"
	DEMOS		= "demos"
	TOOLS		= "Tools"

def info(msg):
	Params.pprint('CYAN', msg)

def testname(file, tests_dir='test'):
	test_file=os.path.join(tests_dir, file)
	return open(test_file, 'r')

def run_tests():
	# could be run from test dir only !
	import build_dir as test_build_dir
	import cxx_test as test_cxx
	import gcc_test as test_gcc
	import configure_test as test_configure

	if Params.g_options:
		verbose = Params.g_options.verbose
	else:
		verbose = 1

	info("******** Configure tests ********")
	test_configure.run_tests(verbose)
	info("******** build dir tests ********")
	test_build_dir.run_tests(verbose)
	info("******** g++ tests ********")
	test_cxx.run_tests(verbose)
	info("******** gcc tests ********")
	test_gcc.run_tests(verbose)

	for i in ['dist','configure','clean','distclean','make','install','doc']:
		Params.g_commands[i]=0

#	info("******** node path tests ********")
#	exec testname('paths.tst', os.path.join('wafadmin', 'test'))

	# FIXME: fail... :(
#	info("******** scheduler and task tests ********")
#	exec testname('scheduler.tst', os.path.join('wafadmin', 'test'))

if __name__ == "__main__":

	for i in ['dist','configure','clean','distclean','make','install','doc']:
		Params.g_commands[i]=0

	run_tests()
#	exec testname('paths.tst')
	#exec testname('environment.tst')

#	exec testname('scheduler.tst')

	#exec testname('configure.tst')
	#exec testname('stress.tst')
	#exec testname('stress2.tst')
	#exec testname('scanner.tst')
	#exec testname('cpptest.tst') # redundant, the demo does it better

