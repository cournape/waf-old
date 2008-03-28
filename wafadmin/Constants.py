#! /usr/bin/env python
# encoding: utf-8
# Yinon dot me gmail 2008

# maintainer the version number is updated from the top-level wscript file
HEXVERSION = 0x10303
ABI = 3

CACHE_DIR          = 'c4che'
CACHE_SUFFIX       = '.cache.py'
DBFILE             = '.wafpickle-%d' % ABI
WSCRIPT_FILE       = 'wscript'
WSCRIPT_BUILD_FILE = 'wscript_build'
COMMON_INCLUDES    = 'COMMON_INCLUDES'

VARIANT = '_VARIANT_'
DEFAULT = 'default'

SRCDIR  = 'srcdir'
BLDDIR  = 'blddir'
APPNAME = 'APPNAME'
VERSION = 'VERSION'

DEFINES = 'defines'
UNDEFINED = '#undefined#variable#for#defines#'

