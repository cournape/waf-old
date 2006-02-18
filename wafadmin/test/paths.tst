#! /usr/bin/env python

import Runner

pexec = Runner.exec_command

# scan folders, print relative paths between nodes
pexec('rm -rf runtest')
pexec('mkdir -p runtest/src/blah')
pexec('mkdir -p runtest/src/blah2')
pexec('mkdir -p runtest/tst/bleh')
pexec('mkdir -p runtest/tst/bleh2')

info("> 1")
bld = Build.Build()
Params.g_dbfile='runtest/.dblite'
bld.load()

info("> 2")
bld.set_srcdir('.')
bld.set_bdir('_build_')
bld.scandirs('runtest runtest/src runtest/src/blah runtest/src/blah2 runtest/tst runtest/tst/bleh runtest/tst/bleh2')

info("> 3, check a path under srcnode")
srcnode = Params.g_srcnode
tstnode = Params.g_srcnode.find_node(['runtest','src','blah'])
print tstnode.relpath_gen(srcnode)
	
info("> 4, check two different paths")
tstnode2 = Params.g_srcnode.find_node(['runtest','tst','bleh2'])
print tstnode.relpath_gen(tstnode2)

info("> 5, check srcnode against itself")
print srcnode.relpath_gen(srcnode)

# cleanup
info("paths test end")
pexec('rm -rf runtest .dblite _build_')


