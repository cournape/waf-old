#! /usr/bin/env python
# encoding: utf-8
# Samuel Mendes, 2008 (lok)

import cc
from TaskGen import extension
from Configure import conftest

# and for objective c++ it would be .mm and .M

EXT_OBJC = ['.m']
@extension(EXT_OBJC)
def objc_hook(self, node):
	tsk = cc.c_hook(self, node)
	tsk.env.append_unique('CCFLAGS', tsk.env['GCC-OBJC'])
	tsk.env.append_unique('LINKFLAGS', tsk.env['GCC-OBJCLINK'])

@conftest
def gccobjc_common_flags(conf):
	v = conf.env
	v['GCC-OBJC']         = '-x objective-c'
	v['GCC-OBJCLINK']     = '-lobjc'

detect = 'gccobjc_common_flags'
