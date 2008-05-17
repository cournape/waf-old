#! /usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

"""Add options for the standard GNU directories, this tool will add the options
found in autotools, and will update the environment with the following
installation variables:

 * PREFIX : architecture-independent files [/usr/local]
 * EXEC_PREFIX : architecture-dependent files [PREFIX]
 * BINDIR : user executables [EXEC_PREFIX/bin]
 * SBINDIR : user executables [EXEC_PREFIX/sbin]
 * LIBEXECDIR : program executables [EXEC_PREFIX/libexec]
 * SYSCONFDIR : read-only single-machine data [PREFIX/etc]
 * SHAREDSTATEDIR : modifiable architecture-independent data [PREFIX/com]
 * LOCALSTATEDIR : modifiable single-machine data [PREFIX/var]
 * LIBDIR : object code libraries [EXEC_PREFIX/lib]
 * INCLUDEDIR : C header files [PREFIX/include]
 * OLDINCLUDEDIR : C header files for non-gcc [/usr/include]
 * DATAROOTDIR : read-only arch.-independent data root [PREFIX/share]
 * DATADIR : read-only architecture-independent data [DATAROOTDIR]
 * INFODIR : info documentation [DATAROOTDIR/info]
 * LOCALEDIR : locale-dependent data [DATAROOTDIR/locale]
 * MANDIR : man documentation [DATAROOTDIR/man]
 * DOCDIR : documentation root [DATAROOTDIR/doc/telepathy-glib]
 * HTMLDIR : html documentation [DOCDIR]
 * DVIDIR : dvi documentation [DOCDIR]
 * PDFDIR : pdf documentation [DOCDIR]
 * PSDIR : ps documentation [DOCDIR]
"""

import os.path, re
import Params, Utils

APPNAME = Utils.g_module.APPNAME
VERSION = Utils.g_module.VERSION

_options = (
	('bindir', 'user executables', '$(EXEC_PREFIX)/bin'),
	('sbindir', 'system admin executables', '$(EXEC_PREFIX)/sbin'),
	('libexecdir', 'program executables', '$(EXEC_PREFIX)/libexec'),
	('sysconfdir', 'read-only single-machine data', '$(PREFIX)/etc'),
	('sharedstatedir', 'modifiable architecture-independent data', '$(PREFIX)/com'),
	('localstatedir', 'modifiable single-machine data', '$(PREFIX)/var'),
	('libdir', 'object code libraries', '$(EXEC_PREFIX)/lib'),
	('includedir', 'C header files', '$(PREFIX)/include'),
	('oldincludedir', 'C header files for non-gcc', '/usr/include'),
	('datarootdir', 'read-only arch.-independent data root', '$(PREFIX)/share'),
	('datadir', 'read-only architecture-independent data', '$(DATAROOTDIR)'),
	('infodir', 'info documentation', '$(DATAROOTDIR)/info'),
	('localedir', 'locale-dependent data', '$(DATAROOTDIR)/locale'),
	('mandir', 'man documentation', '$(DATAROOTDIR)/man'),
	('docdir', 'documentation root', '$(DATAROOTDIR)/doc/$(PACKAGE)'),
	('htmldir', 'html documentation', '$(DOCDIR)'),
	('dvidir', 'dvi documentation', '$(DOCDIR)'),
	('pdfdir', 'pdf documentation', '$(DOCDIR)'),
	('psdir', 'ps documentation', '$(DOCDIR)'),
)

_varprog = re.compile(r'\$(\w+|\([^)]*\))')
def _substitute_vars(path, vars):
	"""Substitute variables in a path"""
	if '$' not in path:
		return path, 0

	i = 0
	unresolved_count = 0
	while True:
		m = _varprog.search(path, i)
		if m:
			i, j = m.span(0)
			name = m.group(1)
			if name[:1] == '(' and name[-1:] == ')':
				name = name[1:-1]
			if name in vars:
				tail = path[j:]
				path = path[:i] + vars[name]
				i = len(path)
				path = path + tail
			else:
				i = j
				unresolved_count += 1
		else:
			break
	return path, unresolved_count

def detect(conf):
	global _options, APPNAME, VERSION

	def get_param(varname):
		return getattr(Params.g_options, varname, '')

	conf.env['PREFIX'] = os.path.abspath(conf.env['PREFIX'])
	prefix = conf.env['PREFIX']

	eprefix = get_param('EXEC_PREFIX')
	if not eprefix:
		eprefix = prefix
	conf.env['EXEC_PREFIX'] = eprefix

	resolved_dirs_dict = {'PREFIX' : prefix, 'EXEC_PREFIX': eprefix,
		'APPNAME' : APPNAME, 'PACKAGE': APPNAME, 'VERSION' : VERSION}
	unresolved_dirs_dict = {}
	for name, help, default in _options:
		name = name.upper()
		value = get_param(name)
		if value:
			resolved_dirs_dict[name] = value
		else:
			unresolved_dirs_dict[name] = default

	# Resolve cross references between the variables, expanding everything
	while len(unresolved_dirs_dict) > 0:
		for name in unresolved_dirs_dict.keys():
			unresolved_path = unresolved_dirs_dict[name]
			path, count = _substitute_vars(unresolved_path, resolved_dirs_dict)
			if count == 0:
				resolved_dirs_dict[name] = path
				del unresolved_dirs_dict[name]
			else:
				unresolved_dirs_dict[name] = path

	del resolved_dirs_dict['APPNAME']
	del resolved_dirs_dict['PACKAGE']
	del resolved_dirs_dict['VERSION']
	for name, value in resolved_dirs_dict.iteritems():
		conf.env[name] = value

def set_options(opt):

	# copied from multisync-gui-0.2X wscript
	inst_dir = opt.add_option_group("Installation directories",
		'By default, waf install will install all the files in\
 "/usr/local/bin", "/usr/local/lib" etc. An installation prefix other\
 than "/usr/local" can be given using "--prefix",\
 for instance "--prefix=$HOME"')

	#just do some cleanups in the option list
	try:
		prefix_option = opt.parser.get_option("--prefix")
		opt.parser.remove_option("--prefix")
		destdir_option = opt.parser.get_option("--destdir")
		opt.parser.remove_option("--destdir")
		inst_dir.add_option(prefix_option)
		inst_dir.add_option(destdir_option)
	except:
		pass
	# end copy

	inst_dir.add_option('--exec-prefix',
		help="installation prefix [Default: %s]" % 'PREFIX',
		default='',
		dest='EXEC_PREFIX')

	dirs_options = opt.add_option_group("Fine tuning of the installation directories", '')

	global _options
	for name, help, default in _options:
		option_name = '--' + name
		str_default = default.replace('$(', '').replace(')', '')
		str_help = '%s [Default: %s]' % (help, str_default)
		dirs_options.add_option(option_name, help=str_help, default='', dest=name.upper())

