#!/usr/bin/env python
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

_options = [x.split(", ") for x in '''
bindir, user executables, $(EXEC_PREFIX)/bin
sbindir, system admin executables, $(EXEC_PREFIX)/sbin
libexecdir, program executables, $(EXEC_PREFIX)/libexec
sysconfdir, read-only single-machine data, $(PREFIX)/etc
sharedstatedir, modifiable architecture-independent data, $(PREFIX)/com
localstatedir, modifiable single-machine data, $(PREFIX)/var
libdir, object code libraries, $(EXEC_PREFIX)/lib
includedir, C header files, $(PREFIX)/include
oldincludedir, C header files for non-gcc, /usr/include
datarootdir, read-only arch.-independent data root, $(PREFIX)/share
datadir, read-only architecture-independent data, $(DATAROOTDIR)
infodir, info documentation, $(DATAROOTDIR)/info
localedir, locale-dependent data, $(DATAROOTDIR)/locale
mandir, man documentation, $(DATAROOTDIR)/man
docdir, documentation root, $(DATAROOTDIR)/doc/$(PACKAGE)
htmldir, html documentation, $(DOCDIR)
dvidir, dvi documentation, $(DOCDIR)
pdfdir, pdf documentation, $(DOCDIR)
psdir, ps documentation, $(DOCDIR)
'''.split('\n') if x]

re_var = re.compile(r'\$\(([a-zA-Z0-9_]+)\)')
def subst_vars(foo, vars):
	def repl(m):
		s = m.group(1)
		if s: return vars[s]
		return ''
	return re_var.sub(repl, foo)

def detect(conf):
	global _options, APPNAME, VERSION

	def get_param(varname, default):
		return getattr(Params.g_options, varname, default)

	conf.env['EXEC_PREFIX'] = get_param('EXEC_PREFIX', conf.env['PREFIX'])
	complete = False
	iter = 0
	while not complete and iter < len(_options) + 1:
		iter += 1
		complete = True
		for name, help, default in _options:
			print name, help, default
			name = name.upper()
			if conf.env[name]: continue
			try:
				conf.env[name] = subst_vars(get_param(name, default), conf.env)
			except:
				complete = False
	if not complete:
		fatal("variables are not substituted properly")

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

