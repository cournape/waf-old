#! /usr/bin/env python
# vim:ts=8:sw=8:softtabstop=8
# encoding: utf-8
# Gernot Vormayr, 2006

"""
Quick n dirty boost detections
"""

import os, glob, types
import Params, Configure
from Params import fatal

def detect_boost(conf):
        env = conf.env
        opt = Params.g_options

        want_asio = 0
        v=conf.env.copy()

        if env['WANT_BOOST']:
                if type(env['WANT_BOOST']) is types.StringType:
                        want_libs = env['WANT_BOOST'].split()
                else:
                        want_libs = env['WANT_BOOST']
                if want_libs.count('ASIO'):
                        want_libs.remove('ASIO')
                        want_asio=1
                if want_libs.count('ASIO_MT'):
                        want_libs.remove('ASIO_MT')
                        want_asio=2
        else:
                want_libs = 0

        try: boostlibs = opt.boostlibs
        except: boostlibs=''

        try: boostincludes = opt.boostincludes
        except: boostincludes=''

        try: asioincludes = opt.asioincludes
        except: asioincludes=''

        try: boostfolder = opt.boostfolder
        except: boostfolder=''

        if boostfolder:
                boostincludes=boostfolder+'/include'
                boostlibs=boostfolder+'/lib'

        #let's try to find boost which is not easy, cause boost seems like it wants to hide :(
        if not boostincludes:
                boostincludes= ['/sw/include', '/usr/local/include', '/opt/include', '/opt/local/include', '/usr/include']
        else:
                boostincludes=[boostincludes]
        guess=[]
        for dir in boostincludes:
                try:
                        for subdir in os.listdir(dir):
                                # we have to check for boost or boost-version cause there are systems
                                # which put boost directly into a boost subdir (eg. gentoo)
                                if subdir=='boost': guess.append(dir)
                                elif subdir.startswith('boost-'): guess.append(dir+'/'+subdir)
                except: pass
        if not guess:
                fatal('boost headers not found')
                return 0
        versions={}
        for dir in guess:
                test_obj = Configure.check_data()
                test_obj.code = '#include <iostream>\n#include <boost/version.hpp>\nint main() { std::cout << BOOST_VERSION << std::endl; return 0; }\n'
                test_obj.env = v
                test_obj.env['CPPPATH']=[dir]
                test_obj.execute = 1
                ret=conf.run_check(test_obj)
                if ret:
                        versions[int(ret['result'])]=dir
        version=versions.keys()

        errtext=''

        if env['WANT_BOOST_MIN']:
                errtext+='>= '+env['WANT_BOOST_MIN']+' '
                min_version=env['WANT_BOOST_MIN'].split('.')
                min_version=int(min_version[0])*100000+int(min_version[1])*100+int(min_version[2])
                version=filter(lambda x:x>=min_version,version)
        if env['WANT_BOOST_MAX']:
                errtext+='<= '+env['WANT_BOOST_MAX']+' '
                max_version=env['WANT_BOOST_MAX'].split('.')
                max_version=int(max_version[0])*100000+int(max_version[1])*100+int(max_version[2])
                version=filter(lambda x:x<=max_version,version)

        version.sort()
        if len(version) is 0:
                fatal('No boost '+errtext+'found!')

        version=version.pop()
        boost_includes=versions[version]
        version="%d.%d.%d" % (version/100000,version/100%1000,version%100)
        conf.check_message('header','boost/version.hpp',1,'Version '+boost_includes+' ('+version+')')
        env['CPPPATH_BOOST']=boost_includes

        # search vor asio
        if want_asio:
                errtext=''
                asio_version=min_version=max_version=0
                if env['WANT_ASIO_MIN']:
                        errtext+='>= '+env['WANT_ASIO_MIN']+' '
                        min_version=env['WANT_ASIO_MIN'].split('.')
                        min_version=int(min_version[0])*100000+int(min_version[1])*100+int(min_version[2])
                if env['WANT_ASIO_MAX']:
                        errtext+='<= '+env['WANT_ASIO_MAX']+' '
                        max_version=env['WANT_ASIO_MAX'].split('.')
                        max_version=int(max_version[0])*100000+int(max_version[1])*100+int(max_version[2])
                #first look in the boost dir - but not when asioincludes is set
                if not asioincludes:
                        test_obj = Configure.check_data()
                        test_obj.code = '#include <iostream>\n#include <boost/asio/version.hpp>\nint main() { std::cout << BOOST_ASIO_VERSION << std::endl; return 0; }\n'
                        test_obj.env = v
                        test_obj.env['CPPPATH']=[boost_includes]
                        test_obj.execute = 1
                        ret=conf.run_check(test_obj)
                        if ret:
                                asio_version=int(ret['result'])
                                if min_version and asio_version<min_version:
                                        asio_version=0
                                if max_version and asio_version>max_version:
                                        asio_version=0
                        if asio_version:
                                conf.define('BOOST_ASIO',1)
                                version="%d.%d.%d" % (asio_version/100000,asio_version/100%1000,asio_version%100)
                                conf.check_message('header','boost/asio/version.hpp',1,'Version '+version)
                                if want_asio==1:
                                        if want_libs:
                                                try: want_libs.remove('BOOST_SYSTEM')
                                                except: pass
                                                want_libs.append('BOOST_SYSTEM')
                                        else:
                                                want_libs=['BOOST_SYSTEM']
                                else:
                                        if want_libs:
                                                try: want_libs.remove('BOOST_SYSTEM_MT')
                                                except: pass
                                                want_libs.append('BOOST_SYSTEM_MT')
                                        else:
                                                want_libs=['BOOST_SYSTEM_MT']
                #ok not in boost dir - ahh did i say ok? na imho that's not ok!
                if not asio_version:
                        if not asioincludes:
                                asioincludes= ['/sw/include', '/usr/local/include', '/opt/include', '/opt/local/include', '/usr/include']
                        else:
                                asioincludes=[asioincludes]
                        versions={}
                        for dir in asioincludes:
                                test_obj = Configure.check_data()
                                test_obj.code = '#include <iostream>\n#include <asio/version.hpp>\nint main() { std::cout << ASIO_VERSION << std::endl; return 0; }\n'
                                test_obj.env = v
                                test_obj.env['CPPPATH']=[dir]
                                test_obj.execute = 1
                                ret=conf.run_check(test_obj)
                                if ret:
                                        versions[int(ret['result'])]=dir
                        version=versions.keys()
                        if min_version:
                                version=filter(lambda x:x>=min_version,version)
                        if max_version:
                                version=filter(lambda x:x<=max_version,version)

                        version.sort()
                        if len(version) is 0:
                                fatal('No asio '+errtext+'found!')

                        version=version.pop()
                        asio_includes=versions[version]
                        version="%d.%d.%d" % (version/100000,version/100%1000,version%100)
                        conf.check_message('header','asio/version.hpp',1,'Version '+asio_includes+' ('+version+')')
                        env['CPPPATH_ASIO']=asio_includes
                        env['CPPPATH_ASIO_MT']=asio_includes
                        conf.undefine('BOOST_ASIO')
        #well now we've found our includes - let's search for the precompiled libs
        if want_libs:
                def check_boost_libs(libs,lib_path):
                        files=glob.glob(lib_path+'/libboost_*'+env['shlib_SUFFIX'])
                        files=map(lambda x:x[len(lib_path)+4:-len(env['shlib_SUFFIX'])] ,filter(lambda x: x.find('-d')==-1 ,files))
                        for lib in libs:
                                libname=lib.lower()
                                if libname.endswith('_mt'):
                                        libname=libname[0:-3]+'-mt'
                                for file in files:
                                        if file.startswith(libname):
                                                conf.check_message('library',libname,1,file)
                                                env['LIBPATH_'+lib]=lib_path
                                                env['LIB_'+lib]=file
                                                if lib is 'BOOST_SYSTEM':
                                                        env['LIB_ASIO']=file
                                                        env['LIBPATH_ASIO']=file
                                                elif lib is 'BOOST_SYSTEM_MT':
                                                        env['LIB_ASIO_MT']=file
                                                        env['LIBPATH_ASIO_MT']=file
                                                break
                                else:
                                        fatal('lib '+libname+' not found!')

                if not boostlibs:
                        boostlibs=['/usr/lib64', '/usr/lib32', '/usr/lib', '/sw/lib', '/usr/local/lib', '/opt/lib', '/opt/local/lib']
                else:
                        boostlibs=[boostlibs]

                lib_path=Configure.find_file_ext('libboost_*'+version+'*',boostlibs)
                if lib_path=='':
                        lib_path=Configure.find_file_ext('libboost_*',boostlibs)
                        if lib_path=='':
                                conf.check_message('library','boost',0,'')
                        else:
                                check_boost_libs(want_libs,lib_path)
                else:
                        check_boost_libs(want_libs,lib_path)
        return 1

def detect(conf):
        return detect_boost(conf)

def set_options(opt):
        opt.add_option('--boost-includes', type='string', default='', dest='boostincludes', help='path to the boost directory where the includes are e.g. /usr/local/include/boost-1_34_1')
        opt.add_option('--boost-libs', type='string', default='', dest='boostlibs', help='path to the directory where the boost libs are e.g. /usr/local/lib')
        opt.add_option('--boost', type='string', default='', dest='boostfolder', help='path to the directory where the boost lives are e.g. /usr/local')
        opt.add_option('--asio-includes', type='string', default='', dest='asioincludes', help='path to asio e.g. /usr/local/include/asio')

def setup(env):
        pass

