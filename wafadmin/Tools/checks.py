#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import Utils
from Params import error

endian_str = """
#include <stdio.h>
int am_big_endian()
{
        long one = 1;
        return !(*((char *)(&one)));
}

int main()
{
  if (am_big_endian())
     printf("bigendian=1\\n");
  else
     printf("bigendian=0\\n");

  return 0;
}
"""

def checkEndian(self, define='', pathlst=[]):
	if define == '': define = 'HAVE_BIGENDIAN'

	if self.isDefined(define): return self.getDefine(define)

	global endian
	code = self.TryRun(endian_str, pathlst=pathlst)

	try:
		t = Utils.to_hashtable(code)
		is_big = int(t['bigendian'])
	except:
		error('endian test failed '+code)
		is_big = 0
		raise

	if is_big: strbig = 'big endian'
	else:      strbig = 'little endian'

	self.checkMessageCustom('endianness', '', strbig)
	self.addDefine(define, is_big)
	return is_big


def setup(env):
	# we provide no new action or builder
	pass

def detect(conf):
	# attach the checks to the conf object
	setattr(conf.__class__, checkEndian.__name__, checkEndian)
	return 1

