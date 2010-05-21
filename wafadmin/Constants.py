#!/usr/bin/env python
# encoding: utf-8
# Yinon dot me gmail 2008

"""
these constants are somewhat public, try not to mess them

maintainer: the version number is updated from the top-level wscript file
"""

# do not touch these three lines, they are updated automatically
HEXVERSION = 0x106000
WAFVERSION="1.6.0"
WAFREVISION = "XXXXX"
ABI = 98

# permissions
O644 = 420
O755 = 493

CACHE_DIR          = 'c4che'
CACHE_SUFFIX       = '.cache.py'
DBFILE             = '.wafpickle-%d' % ABI
WAF_CONFIG_LOG     = 'config.log'
WAF_CONFIG_H       = 'config.h'

SIG_NIL = b'iluvcuteoverload'

SRCDIR  = 'top'
BLDDIR  = 'out'
APPNAME = 'APPNAME'
VERSION = 'VERSION'

DEFINES = 'defines'
UNDEFINED = ()

CFG_FILES = 'cfg_files'

