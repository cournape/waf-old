#! /usr/bin/env python

import time, sys, os
dir = os.path.abspath('wafadmin')
sys.path=[dir, os.path.join(dir,'Tools')]+sys.path
Params.g_tooldir = [os.path.join(dir,'Tools')]

import Runner, Build

pexec = Runner.exec_command

wscript_top = """
VERSION='0.0.1'
APPNAME='test_path'

# these variables are mandatory ('/' are converted automatically)
srcdir = '.'
blddir = '_build_'

def build(bld):
	pass
def configure(conf):
	pass
def set_options(opt):
	pass
"""

# scan folders, print relative paths between nodes
pexec('rm -rf tests/runtest')
pexec('mkdir -p tests/runtest')

pexec('cp tests/test_build_dir/waf/waf tests/runtest/')

dest = open('./tests/runtest/wscript', 'w')
dest.write(wscript_top)
dest.close()

pexec('cd tests/runtest/ && ./waf configure && cd ../../')
os.chdir('tests/runtest')
pexec('mkdir -p src/blah')
pexec('mkdir -p src/blah2')
pexec('mkdir -p tst/bleh')
pexec('mkdir -p tst/bleh2')

info("> 1 check relative srcnode path")
bld = Build.BuildContext()
bld.load_dirs('.', '_build_')
srcnode = Params.g_build.m_srcnode
print srcnode.relpath_gen(srcnode)

info("> 2, check a path(src/blah) under srcnode")
tstnode = Params.g_build.m_srcnode.find_dir_lst(['src','blah'])
print tstnode.relpath_gen(srcnode)

info("> 3, relative path to ./src/bleh2 from within ./src/blah")
tstnode2 = Params.g_build.m_srcnode.find_dir_lst(['tst','bleh2'])
print tstnode.relpath_gen(tstnode2)

info("> 4, check srcnode against itself")
print srcnode.relpath_gen(srcnode)

# cleanup
info("paths test end")
os.chdir('..')
os.chdir('..')
pexec('rm -rf tests/runtest')


