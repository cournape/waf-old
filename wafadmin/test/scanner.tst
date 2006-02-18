#! /usr/bin/env python

# testing scanners

import Runner
pexec = Runner.exec_command

# constants
sconstruct_x = """
bld.set_srcdir('.')
bld.set_bdir('_build_')
bld.scandirs('src ')
from Common import dummy
add_subdir('src')
"""

sconscript_0="""
obj=dummy()
obj.source='dummy.h'
obj.target='dummy.i'
"""

dummy_hfile="""
#include <iostream>
#include <limits.h>
#include "file1.moc"
	#include    "file2.moc"
  #include "file3.moc" # haha
// #include "file4.moc"
"""

#
# clean before building anything
#
pexec('rm -rf runtest/ && mkdir -p runtest/src/sub/')

#
# write our files
#
dest = open('./runtest/sconstruct', 'w')
dest.write(sconstruct_x)
dest.close()

dest = open('./runtest/src/sconscript', 'w')
dest.write(sconscript_0)
dest.close()

dest = open('./runtest/src/dummy.h', 'w')
dest.write(dummy_hfile)
dest.close()


dest = open('./runtest/src/file1.moc', 'w')
dest.write("file1.moc")
dest.close()

dest = open('./runtest/src/sub/file2.moc', 'w')
dest.write("file2.moc")
dest.close()

dest = open('./runtest/src/sub/file3.moc', 'w')
dest.write("file3.moc")
dest.close()




# now that the files are there, run the app
#Params.set_trace(0,0,0)

#
# change the current directory to 'runtest'
#
os.chdir('runtest')
sys.path.append('..')
import Scripting

#
# load the build application
#
bld = Build.Build()
bld.load()
bld.set_srcdir('.')
bld.set_bdir('_build_')

bld.scandirs('src src/sub/')

src_node = bld.m_tree.m_srcnode
path='src/dummy.h'.split('/')
hfile = src_node.find_node( path )

runtest_src     = src_node.find_node(['src'])
runtest_src_sub = runtest_src.find_node(['sub'])

import Scan
lst = Scan.c_scanner(hfile, [runtest_src, runtest_src_sub, src_node])
print "* list of nodes found by scanning ", lst

#bld.m_tree.dump()

#
# close the build application
#
bld.cleanup()
bld.store()

#Params.set_trace(1,1,1)

#
# cleanup
#
info("scanner test end")
os.chdir('..')
#pexec('rm -rf runtest/')

