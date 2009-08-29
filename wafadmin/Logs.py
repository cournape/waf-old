#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, re, logging, traceback, sys
from Constants import *

zones = ''
verbose = 0

colors_lst = {
'USE' : True,
'BOLD'  :'\x1b[01;1m',
'RED'   :'\x1b[01;91m',
'GREEN' :'\x1b[32m',
'YELLOW':'\x1b[33m',
'PINK'  :'\x1b[35m',
'BLUE'  :'\x1b[01;34m',
'CYAN'  :'\x1b[36m',
'NORMAL':'\x1b[0m',
'cursor_on'  :'\x1b[?25h',
'cursor_off' :'\x1b[?25l',
}

got_tty = not os.environ.get('TERM', 'dumb') in ['dumb', 'emacs']
if got_tty:
	try:
		got_tty = sys.stderr.isatty()
	except AttributeError:
		got_tty = False

import Utils

if not got_tty or 'NOCOLOR' in os.environ:
	colors_lst['USE'] = False

def get_color(cl):
	if not colors_lst['USE']: return ''
	return colors_lst.get(cl, '')

class foo(object):
	def __getattr__(self, a):
		return get_color(a)
	def __call__(self, a):
		return get_color(a)

colors = foo()

re_log = re.compile(r'(\w+): (.*)', re.M)
class log_filter(logging.Filter):
	def __init__(self, name=None):
		pass

	def filter(self, rec):
		rec.c1 = colors.PINK
		rec.c2 = colors.NORMAL
		rec.zone = rec.module
		if rec.levelno >= logging.INFO:
			if rec.levelno >= logging.ERROR:
				rec.c1 = colors.RED
			elif rec.levelno >= logging.WARNING:
				rec.c1 = colors.YELLOW
			else:
				rec.c1 = colors.GREEN
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

class formatter(logging.Formatter):
	def __init__(self):
		logging.Formatter.__init__(self, LOG_FORMAT, HOUR_FORMAT)

	def format(self, rec):
		if rec.levelno >= logging.WARNING or rec.levelno == logging.INFO:
			try:
				return '%s%s%s' % (rec.c1, rec.msg.decode('utf-8'), rec.c2)
			except:
				return rec.c1+rec.msg+rec.c2
		return logging.Formatter.format(self, rec)

def debug(msg):
	if verbose:
		# FIXME why does it eat the newlines????
		msg = msg.replace('\n', ' ')
		logging.debug(msg)

def error(msg):
	logging.error(msg)
	if verbose > 1:
		if isinstance(msg, Utils.WafError):
			st = msg.stack
		else:
			st = traceback.extract_stack()
		if st:
			st = st[:-1]
			buf = []
			for filename, lineno, name, line in st:
				buf.append('  File "%s", line %d, in %s' % (filename, lineno, name))
				if line:
					buf.append('	%s' % line.strip())
			if buf: logging.error("\n".join(buf))

warn = logging.warn
info = logging.info

def init_log():
	log = logging.getLogger()
	log.handlers = []
	log.filters = []
	hdlr = logging.StreamHandler()
	hdlr.setFormatter(formatter())
	log.addHandler(hdlr)
	log.addFilter(log_filter())
	log.setLevel(logging.DEBUG)

# may be initialized more than once
init_log()


# win32 console, grrrr
try:
	from ctypes import *
except ImportError:
	pass
else:
	import re

	STD_OUTPUT_HANDLE = -11
	STD_ERROR_HANDLE = -12

	escape_to_color = { (0, 30): 0x0,			 #black
						(0, 31): 0x4,			 #red
						(0, 32): 0x2,			 #green
						(0, 33): 0x4+0x2,		 #dark yellow
						(0, 34): 0x1,			 #blue
						(0, 35): 0x1+0x4,		 #purple
						(0, 36): 0x2+0x4,		 #cyan
						(0, 37): 0x1+0x2+0x4,	 #grey
						(1, 30): 0x1+0x2+0x4,	 #dark gray
						(1, 31): 0x4+0x8,		 #red
						(1, 32): 0x2+0x8,		 #light green
						(1, 33): 0x4+0x2+0x8,	 #yellow
						(1, 34): 0x1+0x8,		 #light blue
						(1, 35): 0x1+0x4+0x8,	 #light purple
						(1, 36): 0x1+0x2+0x8,	 #light cyan
						(1, 37): 0x1+0x2+0x4+0x8, #white
		}

	class AnsiTerm(object):
		def __init__(self, type):
			self.hconsole = windll.kernel32.GetStdHandle(type)

		ansi_tokens = re.compile('(?:\x1b\[([0-9;]*)([a-zA-Z])|([^\x1b]+))')
		def write(self, text):
			for param, cmd, txt in self.ansi_tokens.findall(text):
				if cmd:
					intensity, sep, color = param.partition(';')
					intensity = int(intensity)
					color = int(color)
					attrib = self.escape_to_color.get((intensity, color), 0x7)
					windll.kernel32.SetConsoleTextAttribute(self.hconsole, attrib)
				else:
					chars_written = c_int()
					windll.kernel32.WriteConsoleA(self.hconsole, txt, len(txt), byref(chars_written), None)

		def flush(self):
			pass

	if sys.platform == 'win32':
		sys.stdout = AnsiTerm(STD_OUTPUT_HANDLE)
		sys.stderr = AnsiTerm(STD_ERROR_HANDLE)
		os.environ['TERM'] = 'vt100'


