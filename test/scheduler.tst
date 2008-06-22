#! /usr/bin/env python

# loading an environment

import time, sys, os
dir = os.path.abspath('wafadmin')
sys.path=[dir, os.path.join(dir,'Tools')]+sys.path
Params.g_tooldir = [os.path.join(dir,'Tools')]

import Params, Runner, Task
import Utils
pexec = Runner.exec_command
#### WARNING!! GOTCHA ! comment this line to use the gcc compiler for testing
Params.g_fake=1

Params.set_trace(1, 1, 1)
#Params.set_trace(0, 0, 0)

if sys.platform == "cygwin":
	cache_x += "program_SUFFIX = '.exe'\n"

wscript_top = """
VERSION='0.0.1'
APPNAME='cpp_test'

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = '_build_'

def build(bld):
	bld.add_subdirs('src')

def configure(conf):
	conf.check_tool(['g++'])

	conf.env['CXXFLAGS_MYPROG']='-O3'
	conf.env['LIB_MYPROG']='m'
	conf.env['SOME_INSTALL_DIR']='/tmp/ahoy/lib/'

	# set a variant called "default", with another config.h
	env_variant2 = conf.env.copy()
	conf.set_env_name('debug', env_variant2)
	env_variant2.set_variant('debug')

def set_options(opt):
	pass
#	opt.sub_options('src')
"""

wscript_build_0="""
obj = bld.create_obj('cpp', 'program')
obj.source='''
a1.cpp b1.cpp b2.cpp
'''
obj.includes='.'
obj.target='testprogram'
"""

wscript_build_1="""
obj = bld.create_obj('cpp', 'program')
obj.source='''
a1.cpp b1.cpp b2.cpp b3.cpp
'''
obj.includes='.'
obj.target='testprogram'
"""

wscript_build_variant="""
obj = bld.create_obj('cpp', 'program')
obj.source='''
a1.cpp b1.cpp b2.cpp
'''
obj.includes='.'
obj.target='testprogram'

obj_debug = obj.clone('debug')
"""

# clean before building
pexec('rm -rf tests/runtest/ && mkdir -p tests/runtest/src/')
pexec('cp tests/test_build_dir/waf/waf tests/runtest/')

dest = open('./tests/runtest/wscript', 'w')
dest.write(wscript_top)
dest.close()

dest = open('./tests/runtest/src/wscript_build', 'w')
dest.write(wscript_build_0)
dest.close()

pexec('cd tests/runtest/ && ./waf configure && cd ../../')

# ================================================ #
# initialisations


Utils.set_main_module(os.path.join('tests','runtest', 'wscript'))


import Options
opt_obj = Options.Handler()
opt_obj.parse_args()


# 1. one cpp files with one header which includes another header
dest = open('./tests/runtest/src/a1.cpp', 'w')
dest.write('#include "a1.h"\n')
dest.write('int main()\n{return 0;}\n')
dest.close()

dest = open('./tests/runtest/src/a1.h', 'w')
dest.write('#include "a2.h"\n')
dest.close()

dest = open('./tests/runtest/src/a2.h', 'w')
dest.write('int val=2;\n')
dest.close()

# 2. two cpp files including each other headers
dest = open('./tests/runtest/src/b1.cpp', 'w')
dest.write('#include "b1.h"\n')
dest.write('#include "b2.h"\n')
dest.write('static int b1_val=42;\n')
dest.close()

dest = open('./tests/runtest/src/b2.cpp', 'w')
dest.write('#include "b1.h"\n')
dest.write('#include "b2.h"\n')
dest.write('static int b2_val=24;\n')
dest.close()

dest = open('./tests/runtest/src/b1.h', 'w')
dest.write('/* */\n')
dest.close()
dest = open('./tests/runtest/src/b2.h', 'w')
dest.write('/* */\n')
dest.close()

# now build a program with all that

Params.g_trace_exclude = "Action Common Deptree Node Option Scripting Build Configure Environment KDE Scan Utils Task".split()
#Params.g_trace_exclude = "Action Deptree Node Option Build Configure Environment Task".split()
#Params.g_trace_exclude = "Action Deptree Node Option Build Configure Environment".split()
#Params.g_trace_exclude = "Configure Environment".split()

def measure():
	global sys, time
	# now that the files are there, run the app
	Params.set_trace(0,0,0)

	os.chdir('tests/runtest')
	sys.path.append('..')
	import Scripting

	t1=time.clock()
	Scripting.main()
	t2=time.clock()

	os.chdir('..')
	os.chdir('..')
	#Params.set_trace(1,1,1)

	return (t2-t1)

def check_tasks_done(lst):
	global Task
	done = map( lambda a: a.m_idx, Task.g_tasks_done )
	ok=1
	for i in lst:
		if i not in done:
			Params.pprint('RED', "found a task that has not run " + str(i))
			ok=0
	for i in done:
		if i not in lst:
			Params.pprint('RED', "found a task that has run when it should not have " + str(i))
			ok=0
	if not ok:
		Params.pprint('RED', " -> test failed, fix the errors !")
	else:
		Params.pprint('GREEN', " -> test successful\n")

def modify_file(file):
	dest = open(file, 'a')
	dest.write('/* file is modified */ \n')
	dest.close()

wait=0

# 0. build all targets normally
Params.pprint('YELLOW', "===> There is a %d second(s) pause between each test <==="%wait)
info("test 0: build all targets normally")
t=measure()
check_tasks_done([0, 1, 2, 3])
#############
Params.pprint('YELLOW', "check if reset works 1")
Utils.reset()
check_tasks_done([])

# a. modify a1.cpp
Utils.reset()
info("test a: a1.cpp is modified")
time.sleep(wait)
modify_file('./tests/runtest/src/a1.cpp')
t=measure()
check_tasks_done([0, 3])

# b. modify a1.h
Utils.reset()
info("test b: a1.h is modified")
time.sleep(wait)
modify_file('./tests/runtest/src/a1.h')
t=measure()
check_tasks_done([0, 3])

# c. modify a2.h
Utils.reset()
info("test c: a2.h is modified")
time.sleep(wait)
modify_file('./tests/runtest/src/a2.h')
t=measure()
check_tasks_done([0, 3])

# d. modify b1.h
Utils.reset()
info("test d: b1.h is modified")
time.sleep(wait)
modify_file('./tests/runtest/src/b1.h')
t=measure()
check_tasks_done([1, 2, 3])

# e. nothing changed
Utils.reset()
info("test e: nothing changed")
time.sleep(wait)
t=measure()
check_tasks_done([])


# f. remove the a2.h include from a1.h, it should trigger a rebuild of a1.cpp
Utils.reset()
info("test f: remove the a2.h include from a1.h")

time.sleep(wait)
dest = open('./tests/runtest/src/a1.h', 'w')
dest.write('// #include "a2.h"\n')
dest.close()

measure()
check_tasks_done([0, 3])

# g. now that the header a2.h is removed, check if changing it triggers anything
Utils.reset()
info("test g: nothing should be rebuilt now (a2.h modified)")
time.sleep(wait)
modify_file('./tests/runtest/src/a2.h')
t=measure()
check_tasks_done([])

# h. add a new source file in the directory
Utils.reset()
info("test h: add a new source file to the project")

time.sleep(wait)
dest = open('./tests/runtest/src/b3.cpp', 'w')
dest.write('// #include "a2.h"\n')
dest.close()

dest = open('./tests/runtest/src/wscript_build', 'w')
dest.write(wscript_build_1)
dest.close()

measure()
check_tasks_done([3, 4])

# i. remove a source file from the project
Utils.reset()
info("test i: remove a source from the project")

time.sleep(wait)
os.unlink('./tests/runtest/src/b3.cpp')

dest = open('./tests/runtest/src/wscript_build', 'w')
dest.write(wscript_build_0)
dest.close()

measure()
check_tasks_done([3])

# j. nothing changed
Utils.reset()
info("test j: nothing changed")
time.sleep(wait)
t=measure()
check_tasks_done([])

#############
# variant tests
#############
Utils.reset()
info("test k: [variant] add debug variant")
dest = open('./tests/runtest/src/wscript_build', 'w')
dest.write(wscript_build_variant)
dest.close()

time.sleep(wait)
t=measure()
check_tasks_done([4,5,6,7])

# l. nothing changed
Utils.reset()
info("test l: [variant] nothing changed")
time.sleep(wait)
t=measure()
check_tasks_done([])

# m. modify b1.h [variant]
Utils.reset()
info("test m: [variant] b1.h is modified")
time.sleep(wait)
modify_file('./tests/runtest/src/b1.h')
t=measure()
check_tasks_done([1, 2, 3, 5, 6, 7])

## other tests
# make the app fail ! (ita)

# cleanup
info("scheduler test end")
#pexec('rm -rf runtest/')

