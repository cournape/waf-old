#! /usr/bin/python env
# encoding: utf-8
#
# written by Ruediger Sonderfeld <ruediger@c-plusplus.de>, 2008
#
# partially based on boost.py written by Gernot Vormayr

"""
Boost Configurator:

written by Ruediger Sonderfeld <ruediger@c-plusplus.de>, 2008
partially based on boost.py written by Gernot Vormayr

ISSUES:
 * find_includes should be called only once!

TODO:
 * see tag matcher. This code sucks sooo bad!!!!!
 * match toolset accordingly
 * run_cache
 * support mandatory
 * ...

"""

import os, glob, types, re
import Params, Configure, config_c
from Params import fatal, warning
from Configure import conf

class boost_configurator(config_c.configurator_base):
    """
    - min_version
    - max_version
    - version
    - include_path
    - lib_path
    - lib
    - toolsettag
    - threadingtag
    - abitag
    - static         - look for static libs (values:
                          'nostatic'  - ignore static libs (default)
                          'both'       - find static libs, too
                          'onlystatic' - find only static libs
    - versiontag     - WARNING: you should rather use version or min_version/max_version
    """
    ## __metaclass__ = config_c.attached_conf ## autohook
    def __init__(self, conf):
        config_c.configurator_base.__init__(self, conf)
        
        self.min_version = ''
        self.max_version = ''
        self.version = ''
        self.lib_path = ['/usr/lib', '/usr/local/lib', '/opt/local/lib', '/sw/lib', '/lib']
        self.include_path = ['/usr/include', '/usr/local/include', '/opt/local/include', '/sw/include']
        self.lib = ''
        self.toolsettag = ''
        self.threadingtag = ''
        self.abitag = ''
        self.versiontag = ''
        self.static = 'nostatic'
        
        self.conf = conf
        self.found_includes = 0

    def error(self):
        fatal('')
    
    def run_cache(self, retval): pass # todo

    def validate(self):
        if self.version:
            self.min_version = self.max_version = self.version

    def get_boost_version_number(self, dir):
        test_obj = Configure.check_data()
        test_obj.code = '''
#include <iostream>
#include <boost/version.hpp>
int main() { std::cout << BOOST_VERSION << std::endl; }
'''
        test_obj.env = self.conf.env
        backup = test_obj.env['CPPPATH']
        test_obj.env['CPPPATH'] = [dir]
        test_obj.execute = 1
        test_obj.force_compiler = 'cpp'
        ret = self.conf.run_check(test_obj)
        test_obj.env['CPPPATH'] = backup
        if ret:
            return int(ret['result'])
        else:
            return -1

    def string_to_version(str):
        version = str.split('.')
        return int(version[0])*100000 + int(version[1])*100 + int(version[2])

    def version_string(self, version):
        major = version / 100000
        minor = version / 100 % 1000
        minor_minor = version % 100
        if minor_minor == 0:
            return "%d_%d" % (major, minor)
        else:
            return "%d_%d_%d" % (major, minor, minor_minor)

    def find_includes(self):
        """
        find_includes checks every path in self.include_path for subdir
        that either starts with boost- or is named boost.
        
        Than the version is checked and selected accordingly to
        min_version/max_version. The highest possible version number is
        selected!

        If no versiontag is set the versiontag is set accordingly to the
        selected library and CPPPATH_BOOST is set.
        """
        env = self.conf.env
        guess = []
        include_paths = [getattr(Params.g_options, 'boostincludes', '')]
        if not include_paths[0]:
            if self.include_path is types.StringType:
                include_paths = [self.include_path]
            else:
                include_paths = self.include_path
        for dir in include_paths:
            try:
                for subdir in os.listdir(dir):
                    if subdir == 'boost':
                        guess.append(dir)
                    elif subdir.startswith('boost-'):
                        guess.append(dir+'/'+subdir)
            except OSError: pass
        if not guess:
            fatal('boost headers not found')
            return 0
        
        min_version = 0
        if self.min_version:
            min_version = string_to_version(self.min_version)
        max_version = 0xFFFFFFFFFFFFFFFF
        if self.max_version:
            max_version = string_to_version(self.max_version)
        
        version_to_dir = {}
        for dir in guess:
            ret = self.get_boost_version_number(dir)
            if ret != -1 and ret >= min_version and ret <= max_version:
                version_to_dir[ret] = dir
	versions = version_to_dir.keys()
	versions.sort()
	if len(versions) is 0:
            fatal('no compatible boost version found! (%s >= version >= %s)'
                  % (self.max_version, self.min_version))
        
        version = versions.pop()
        include_path = version_to_dir[version]
        
        versiontag = self.version_string(version)
        if not self.versiontag:
            self.versiontag = versiontag
        elif self.versiontag != versiontag:
            warning('boost header version and versiontag do _not_ match!')
        self.conf.check_message('header','boost',1,'Version ' + versiontag +
                                ' (' + include_path + ')')
        env['CPPPATH_BOOST'] = include_path
        env['BOOST_VERSION'] = versiontag
        self.found_includes = 1

    is_versiontag = re.compile('\d+_\d+_?\d*')
    is_threadingtag = re.compile('mt')
    is_abitag = re.compile('[sgydpn]+')
    is_toolsettag = re.compile('''
(acc|borland|como|cw|dmc|darwin|gcc|hp_cxx|intel|kylix|msvc|qcc|sun|vacpp)\d*
''')

    def check_tags(self, tags):
        """
        checks library tags

        see http://www.boost.org/doc/libs/1_35_0/more/getting_started/unix-variants.html 6.1
        """
        for tag in tags[1:]:
            if self.is_versiontag.match(tag):     # versiontag
                if self.versiontag and tag != self.versiontag:
                    return 0
            elif self.is_threadingtag.match(tag): # multithreadingtag
                if self.threadingtag == 'st':
                    return 0
                elif self.threadingtag and tag != self.threadingtag:
                    return 0
            elif self.is_abitag.match(tag):        # abitag
                if self.abitag and tag != self.abitag:
                    return 0
                elif tag.find('d') != -1 or tag.find('y') != -1:
                    # ignore debug versions (TODO: check -ddebug)
                    return 0
            elif self.is_toolsettag.match(tag):   # toolsettag
                if self.toolsettag and self.toolsettag != tag:
                    return 0
                elif not tag.startswith(env['CXX']):
                    # todo match version number
                    return 0
        return 1

    def find_library(self, lib):
        """
        searches library paths for lib.
        """
        env = self.conf.env        
        lib_paths = [getattr(Params.g_options, 'boostlibs', '')]
        if not lib_paths[0]:
            if self.lib_path is types.StringType:
                lib_paths = [self.lib_path]
            else:
                lib_paths = self.lib_path
        for lib_path in lib_paths:
            files = []
            if not self.static or self.static == 'nostatic' or self.static == 'both':
                libname_sh = env['shlib_PATTERN'] % ('boost_' + lib + '*')
                files += glob.glob(lib_path + '/' + libname_sh)
            if self.static == 'both' or self.static == 'onlystatic':
                libname_st = env['staticlib_PATTERN'] % ('boost_' + lib + '*')
                files += glob.glob(lib_path + '/' + libname_st)
            if len(files) == 0:
                continue
            for file in files:
                m = re.compile('.*boost_(.*?)\..*').search(file, 1)
                if not m:
                    continue
                libname = m.group(1)
                libtags = libname.split('-')
                if self.check_tags(libtags):
                    self.conf.check_message('library', 'boost_'+lib, 1, file)
                    env['LIBPATH_' + lib] = lib_path
                    env['LIB_' + lib] = 'boost_'+libname
                    break
            if env['LIB_' + lib]:
                break
        if not env['LIB_' + lib]:
            fatal('lib boost_' + lib + ' not found!')
    
    def find_libraries(self):
        if self.lib is types.StringType:
            self.find_library(self.lib)
        else:
            for lib in self.lib:
                self.find_library(lib)
    
    def run_test(self):
        if not self.found_includes: # This is a hack
            self.find_includes()
        self.find_libraries()

def detect(conf):
    def create_boost_configurator(self):
        return boost_configurator(conf)
    conf.hook(create_boost_configurator)

def set_options(opt):
    opt.add_option('--boost-includes', type='string', default='', dest='boostincludes', help='path to the boost directory where the includes are e.g. /usr/local/include/boost-1_35')
    opt.add_option('--boost-libs', type='string', default='', dest='boostlibs', help='path to the directory where the boost libs are e.g. /usr/local/lib')
    #opt.add_option('--boost', type='string', default='', dest='boostfolder', help='path to the directory where the boost lives are e.g. /usr/local')
