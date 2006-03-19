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



# other suggestion - all scripts are modules

import globalEnv
 
def init():
        do_something()
 
def shutdown():
        do_something2()
 
# This one gets called BEFORE configuring & building starts, but after the init() call.
def subprojects():
        add_subproject('blah/sconstruct')
        add_subproject('abc/sconstruct')
 
def set_build():
        bld=Build()
 
def set_options(opt):
        opt.add_option('--prepare', action='store_true', default=False, help='prepare the demo projects RUN ME PLEASE', dest='prepare')
        opt.add_option('--make-archive', action='store_true', default=False, help='create a waf archive suitable for custom projects', dest='arch')
 
def configure():
        conf=config('CPP') # configures for c++. This way waf knows which language to use.
        conf.checkHeader('sdfj.h')
        conf.writeConfig('main.cache.py')
 
def build():
        obj=cppobj('staticlib')
        obj.source=['test.cpp']

