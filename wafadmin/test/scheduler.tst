#! /usr/bin/env python

# loading an environment

import time
import Params
import Runner
import Utils
pexec = Runner.exec_command

#### WARNING!! GOTCHA ! comment this line to use the gcc compiler for testing
Params.g_fake=1

Params.set_trace(1, 1, 1)
#Params.set_trace(0, 0, 0)

# constants
cache_x = """
AR = '/usr/bin/ar'
ARFLAGS = 'r'
CXX = '/home/ita/bin/g++'
CXXFLAGS = '-O2'
CXX_ST = '%s -c -o %s'
DESTDIR = '/tmp/blah/'
LIB = []
LIBSUFFIX = '.so'
LINK = '/home/ita/bin/g++'
LINKFLAGS = []
LINK_ST = '%s -o %s'
PREFIX = '/usr'
RANLIB = '/usr/bin/ranlib'
RANLIBFLAGS = ''
_CPPDEFFLAGS = ''
_CXXINCFLAGS = ''
_LIBDIRFLAGS = ''
_LIBFLAGS = ''
program_obj_ext = ['.o']
shlib_CXXFLAGS = ['-fPIC', '-DPIC']
shlib_LINKFLAGS = ['-shared']
shlib_PREFIX = 'lib'
shlib_SUFFIX = '.so'
shlib_obj_ext = ['.os']
staticlib_LINKFLAGS = ['-Wl,-Bstatic']
staticlib_PREFIX = 'lib'
staticlib_SUFFIX = '.a'
staticlib_obj_ext = ['.o']
"""

sconstruct_x = """
bld.set_srcdir('.')
bld.set_bdir('_build_')
bld.set_default_env('main.cache.py')

bld.scandirs('src')

from Common import dummy,cppobj

add_subdir('src')
"""

sconscript_0="""
#print 'test script for creating testprogram is read'
obj=cppobj('program')
obj.source='''
a1.cpp
b1.cpp b2.cpp
'''
obj.includes='. src'
obj.target='testprogram'
"""

sconscript_1="""
#print 'test script for creating testprogram is read'
obj=cppobj('program')
obj.source='''
a1.cpp
b1.cpp b2.cpp b3.cpp
'''
obj.includes='. src'
obj.target='testprogram'
"""

# clean before building
pexec('rm -rf runtest/ && mkdir -p runtest/src/')

dest = open('./runtest/sconstruct', 'w')
dest.write(sconstruct_x)
dest.close()

dest = open('./runtest/src/sconscript', 'w')
dest.write(sconscript_0)
dest.close()

dest = open('./runtest/main.cache.py', 'w')
dest.write(cache_x)
dest.close()

# 1. one cpp files with one header which includes another header
dest = open('./runtest/src/a1.cpp', 'w')
dest.write('#include "a1.h"\n')
dest.write('int main()\n{return 0;}')
dest.close()

dest = open('./runtest/src/a1.h', 'w')
dest.write('#include "a2.h"\n')
dest.close()

dest = open('./runtest/src/a2.h', 'w')
dest.write('int val=2;\n')
dest.close()

# 2. two cpp files including each other headers
dest = open('./runtest/src/b1.cpp', 'w')
dest.write('#include "b1.h"\n')
dest.write('#include "b2.h"\n')
dest.write('static int b1_val=42;')
dest.close()

dest = open('./runtest/src/b2.cpp', 'w')
dest.write('#include "b1.h"\n')
dest.write('#include "b2.h"\n')
dest.write('static int b2_val=24;')
dest.close()

dest = open('./runtest/src/b1.h', 'w')
dest.write('/* */\n')
dest.close()
dest = open('./runtest/src/b2.h', 'w')
dest.write('/* */\n')
dest.close()

# now build a program with all that

Params.g_trace_exclude = "Action Common Deptree Node Option Scripting Build Configure Environment KDE Scan Utils Task".split()
#Params.g_trace_exclude = "Action Deptree Node Option Build Configure Environment Task".split()
#Params.g_trace_exclude = "Action Deptree Node Option Build Configure Environment".split()
#Params.g_trace_exclude = "Configure Environment".split()

def measure():
	# now that the files are there, run the app
	Params.set_trace(0,0,0)

	os.chdir('runtest')
	sys.path.append('..')
	import Scripting

	t1=time.clock()
	Scripting.Main()
	t2=time.clock()

	os.chdir('..')
	#Params.set_trace(1,1,1)

	return (t2-t1)

def check_tasks_done(lst):
	done = map( lambda a: a.m_idx, Params.g_done )
	ok=1
	for i in lst:
		if i not in done:
			Params.pprint('RED', "found a task that has not run" + str(i))
			ok=0
	for i in done:
		if i not in lst:
			Params.pprint('RED', "found a task that has run when it should not have" + str(i))
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
check_tasks_done([1, 2, 3, 4])

# a. modify a1.cpp
Utils.reset()
info("test a: a1.cpp is modified")
time.sleep(wait)
modify_file('./runtest/src/a1.cpp')
t=measure()
check_tasks_done([1, 4])

# b. modify a1.h
Utils.reset()
info("test b: a1.h is modified")
time.sleep(wait)
modify_file('./runtest/src/a1.h')
t=measure()
check_tasks_done([1, 4])

# c. modify a2.h
Utils.reset()
info("test c: a2.h is modified")
time.sleep(wait)
modify_file('./runtest/src/a2.h')
t=measure()
check_tasks_done([1, 4])

# d. modify b1.h
Utils.reset()
info("test d: b1.h is modified")
time.sleep(wait)
modify_file('./runtest/src/b1.h')
t=measure()
check_tasks_done([2, 3, 4])

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
dest = open('./runtest/src/a1.h', 'w')
dest.write('// #include "a2.h"\n')
dest.close()

measure()
check_tasks_done([1, 4])

# g. now that the header a2.h is removed, check if changing it triggers anything
Utils.reset()
info("test g: nothing should be rebuilt now")
time.sleep(wait)
modify_file('./runtest/src/a2.h')
t=measure()
check_tasks_done([])

# h. add a new source file in the directory
Utils.reset()
info("test h: add a new source file to the project")

time.sleep(wait)
dest = open('./runtest/src/b3.cpp', 'w')
dest.write('// #include "a2.h"\n')
dest.close()

dest = open('./runtest/src/sconscript', 'w')
dest.write(sconscript_1)
dest.close()

measure()
check_tasks_done([4, 5])

# i. remove a source file from the project
Utils.reset()
info("test i: remove a source from the project")

time.sleep(wait)
os.unlink('./runtest/src/b3.cpp')

dest = open('./runtest/src/sconscript', 'w')
dest.write(sconscript_0)
dest.close()

measure()
check_tasks_done([4])

# j. nothing changed
Utils.reset()
info("test j: nothing changed")
time.sleep(wait)
t=measure()
check_tasks_done([])


## other tests
# make the app fail ! (ita)

# cleanup
info("scheduler test end")
#pexec('rm -rf runtest/')

