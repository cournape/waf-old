#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import re, logging, traceback, sys
import Params
from Constants import *

zones = ''
verbose = 0

re_log = re.compile(r'(\w+): (.*)', re.M)
class log_filter(logging.Filter):
	def __init__(self, name=None):
		pass

	def filter(self, rec):
		col = Params.g_colors
		rec.c1 = col['PINK']
		rec.c2 = col['NORMAL']
		rec.zone = rec.module
		if rec.levelno >= logging.WARNING:
			rec.c1 = col['RED']
			return True

		zone = ''
		m = re_log.match(rec.msg)
		if m:
			zone = rec.zone = m.group(1)
			rec.msg = m.group(2)

		if zones:
			return getattr(rec, 'zone', '') in zones or '*' in zones
		elif not verbose > 2:
			return False
		return True

def fatal(msg, ret=1):
	if verbose:
		st = traceback.extract_stack()
		if st: st = st[:-1]
		buf = []
		for filename, lineno, name, line in st:
			buf.append('  File "%s", line %d, in %s' % (filename, lineno, name))
			if line:
				buf.append('    %s' % line.strip())
		msg = msg + "\n".join(buf)
	logging.error(msg)
	sys.exit(ret)
#logging.fatal = fatal
debug = logging.debug
warn = logging.warn
error = logging.error

def init_log():
	log = logging.getLogger()
	log.handlers = []
	hdlr = logging.StreamHandler()
	hdlr.setFormatter(logging.Formatter(LOG_FORMAT, HOUR_FORMAT))
	log.addHandler(hdlr)
	log.addFilter(log_filter())
	log.setLevel(logging.DEBUG)

