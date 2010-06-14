#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

from waflib import Utils
from waflib.Configure import conf

@conf
def d_platform_flags(self):
	v = self.env
	if Utils.unversioned_sys_platform_to_binary_format(self.env.DEST_OS or Utils.unversioned_sys_platform()) == 'pe':
		v['D_program_PATTERN']   = '%s.exe'
		v['D_shlib_PATTERN']     = 'lib%s.dll'
		v['D_stlib_PATTERN'] = 'lib%s.a'
	else:
		v['D_program_PATTERN']   = '%s'
		v['D_shlib_PATTERN']     = 'lib%s.so'
		v['D_stlib_PATTERN'] = 'lib%s.a'

DLIB = """
version(D_Version2) {
	import std.stdio;
	int main() {
		writefln("phobos2");
		return 0;
	}
} else {
	version(Tango) {
		import tango.stdc.stdio;
		int main() {
			printf("tango");
			return 0;
		}
	} else {
		import std.stdio;
		int main() {
			writefln("phobos1");
			return 0;
		}
	}
}
"""

@conf
def check_dlibrary(self):
	ret = self.check_cc(features='d dprogram', fragment=DLIB, compile_filename='test.d', execute=True)
	self.env.DLIBRARY = ret.strip()

