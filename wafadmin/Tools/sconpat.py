#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import Utils, Configure, Action, md5
from Params import error, fatal

class sconpat_error:
	pass

# a nice way to hide parameters when a class would do it
def Builder(**kw):
	if kw.has_key('generator') and kw.has_key('action'):
		raise sconpat_error, 'do not mix action and generator in a builder'

	if kw.has_key('action'):

		a = kw['action'].replace('$SOURCES', '${SRC}')
		a = a.replace('$TARGETS', '${TGT}')
		a = a.replace('$TARGET', '${TGT[0]}')
		a = a.replace('$SOURCE', '${SRC[0]}')

		m = md5.new()
		m.update(a)
		key = m.hexdigest()

		Action.simple_action(key, a, kw.get('color', 'GREEN'))

def setup(env):
	pass

def detect(conf):
	"attach the checks to the conf object"
	return 1

