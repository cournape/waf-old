#! /usr/bin/env python

# What we would like to write:

#
# In the root of the project:
#

bld = Build()
bld.set_srcdir('.')          # or bld.set_srcdir('src/')
bld.set_bdir('build')        # set the build dir where to put all objects
bld.set_default_env('cache/options.cache.py')
bld.set_cache_file('cache/.dblite')
bld.scandirs('src src/test') # scan folders

#
# In scripts:
#

obj = object(type)
obj.source = "file.cpp file.h"
obj.target = "target.ext"

obj.setopt('CXXFLAGS', '-DBSD_SOURCE=500')
obj.setopt('CXXFLAGS', '-DTEST=0')
obj.setopt('CXXFLAGS', '-g')

# or ..
obj.cxxflags.append('-g')

#
# configuration
#

conf.setConfigHeader("dcop/config-dcop.h")
conf.checkFunction("setenv")
conf.checkHeaders(['sys/time.h', ['unistd.h'])
if conf.results.contains("have_getmntent"):
	conf.checkFunction("mntctl")

