#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"Main parameters"

import os, sys
import Constants, Utils

# updated from the top-level wscript
g_version="1.4.9"

g_rootname = ''
g_progress = '\x1b[K%s%s%s\r'
if sys.platform=='win32':
	# get the first two letters (c:)
	g_rootname = os.getcwd()[:2]
	g_progress = '\x1b[A\x1b[K%s%s%s\r'

# =================================== #
# Constants set on runtime

g_cwd_launch = None
"directory from which waf was called"

g_tooldir=''
"Tools directory (used in particular by Environment.py)"

g_options = None
"Parsed command-line arguments in the options module"

g_commands = {}
"build, configure, .."

g_verbose = 0
"-v: warnings, -vv: developer info, -vvv: all info"

g_build = None
"only one build object is active at a time"

g_platform = sys.platform
"current platform"

g_cache_global = ''
"config cache directory"

g_conf_name = 'conf-runs-%s-%d.pickle' % (sys.platform, Constants.ABI)

g_install = 0
"true if install or uninstall is set"

try: g_cache_global = os.path.abspath(os.environ['WAFCACHE'])
except KeyError: pass

try: g_lockfile = os.environ['WAFLOCK']
except KeyError: g_lockfile = '.lock-wscript'

# =================================== #
# HELPERS

g_colors = {
'BOLD'  :'\x1b[01;1m',
'RED'   :'\x1b[01;91m',
'REDP'  :'\x1b[01;33m',
'GREEN' :'\x1b[32m',
'YELLOW':'\x1b[33m',
'PINK'  :'\x1b[35m',
'BLUE'  :'\x1b[01;34m',
'CYAN'  :'\x1b[36m',
'NORMAL':'\x1b[0m'
}
"colors used for printing messages"

g_cursor_on ='\x1b[?25h'
g_cursor_off='\x1b[?25l'

def reset_colors():
	global g_colors
	for k in g_colors.keys():
		g_colors[k]=''
		g_cursor_on=''
		g_cursor_off=''

if (sys.platform=='win32') or ('NOCOLOR' in os.environ) \
	or (os.environ.get('TERM', 'dumb') in ['dumb', 'emacs']) \
	or (not sys.stdout.isatty()):
	reset_colors()

g_zones = []

