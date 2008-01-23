#! /usr/bin/env python
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
	try:
		# when running from wafadmin dir
		import test.build_dir as test_build_dir
		import test.gpp_test as test_gpp
		import test.gcc_test as test_gcc
	except ImportError:
		# when running from waf dir
		import wafadmin.test.build_dir as test_build_dir
		import wafadmin.test.gpp_test as test_gpp
		import wafadmin.test.gcc_test as test_gcc
		
	info("******** build dir tests ********")
	test_build_dir.run_tests(Params.g_options.verbose)
	info("******** g++ tests ********")
	test_gpp.run_tests(Params.g_options.verbose)
	info("******** gcc tests ********")
	test_gcc.run_tests(Params.g_options.verbose)
	
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

