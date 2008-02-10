#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Gnome support"

import os, re
import Object, Action, Params, Common, Scan, Utils, Runner
import cc
from Params import fatal, error

n1_regexp = re.compile('<refentrytitle>(.*)</refentrytitle>', re.M)
n2_regexp = re.compile('<manvolnum>(.*)</manvolnum>', re.M)

def postinstall_schemas(prog_name):
	if Params.g_commands['install']:
		dir = Common.path_install('PREFIX', 'etc/gconf/schemas/%s.schemas' % prog_name)
		if not Params.g_options.destdir:
			# add the gconf schema
			Params.pprint('YELLOW', "Installing GConf schema.")
			command = 'gconftool-2 --install-schema-file=%s 1> /dev/null' % dir
			ret = Runner.exec_command(command)
		else:
			Params.pprint('YELLOW', "GConf schema not installed. After install, run this:")
			Params.pprint('YELLOW', "gconftool-2 --install-schema-file=%s" % dir)


def postinstall_icons():
	dir = Common.path_install('DATADIR', 'icons/hicolor')
	if Params.g_commands['install']:
		if not Params.g_options.destdir:
			# update the pixmap cache directory
			Params.pprint('YELLOW', "Updating Gtk icon cache.")
			command = 'gtk-update-icon-cache -q -f -t %s' % dir
			ret = Runner.exec_command(command)
		else:
			Params.pprint('YELLOW', "Icon cache not updated. After install, run this:")
			Params.pprint('YELLOW', "gtk-update-icon-cache -q -f -t %s" % dir)

def postinstall_scrollkeeper(prog_name):
	if Params.g_commands['install']:
		# now the scrollkeeper update if we can write to the log file
		if os.path.iswriteable('/var/log/scrollkeeper.log'):
			dir1 = Common.path_install('PREFIX', 'var/scrollkeeper')
			dir2 = Common.path_install('DATADIR', 'omf/%s' % prog_name)
			command = 'scrollkeeper-update -q -p %s -o %s' % (dir1, dir2)
			ret = Runner.exec_command(command)

def postinstall(prog_name='myapp', schemas=1, icons=1, scrollkeeper=1):
	if schemas: postinstall_schemas(prog_name)
	if icons: postinstall_icons()
	if scrollkeeper: postinstall_scrollkeeper(prog_name)

# give specs
class xml_to(Object.genobj):
	def __init__(self):
		Object.genobj(self, 'other')
		self.source = 'xmlfile'
		self.xslt = 'xlsltfile'
		self.target = 'hey'
		self.inst_var = 'PREFIX'
		self.inst_dir = ''
		self.task_created = None
	def apply(self):
		self.env = self.env.copy()
		tree = Params.g_build
		current = tree.m_curdirnode
		xmlfile = self.path.find_source(self.source)
		xsltfile = self.path.find_source(self.xslt)
		task = self.create_task('xmlto', self.env, 6)
		task.set_inputs([xmlfile, xsltfile])
		task.set_outputs(xmlfile.change_ext('html'))
	def install(self):
		current = Params.g_build.m_curdirnode
		for node in task.m_outputs:
			Common.install_files(self.inst_var, self.inst_dir, node.abspath(self.env))

class sgml_man_scanner(Scan.scanner):
	def __init__(self):
		Scan.scanner.__init__(self)
	def scan(self, task, node):
		env = task.env()
		variant = node.variant(env)

		fi = open(node.abspath(env), 'r')
		content = fi.read()
		fi.close()

		name = n1_regexp.findall(content)[0]
		num = n2_regexp.findall(content)[0]

		doc_name = name+'.'+num
		return ([], [doc_name])

	def do_scan(self, task, node):
		Scan.scanner.do_scan(self, task, node)

		variant = node.variant(task.env())
		tmp_lst = Params.g_build.m_raw_deps[variant][node]
		name = tmp_lst[0]
		task.set_outputs(Params.g_build.m_curdirnode.find_build(name))

sgml_scanner = sgml_man_scanner()

class gnome_sgml2man(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other')
		self.m_tasks=[]
		self.m_appname = appname
	def apply(self):
		tree = Params.g_build
		tree.rescan(self.path)
		for node in self.path.files():
			base, ext = os.path.splitext(node.m_name)
			if ext != '.sgml': continue

			task = self.create_task('sgml2man', self.env, 2)
			task.set_inputs(node)
			# no outputs, the scanner does it
			# no caching for now, this is not a time-critical feature
			# in the future the scanner can be used to do more things (find dependencies, etc)
			sgml_scanner.do_scan(task, node)

	def install(self):
		current = Params.g_build.m_curdirnode

		for task in self.m_tasks:
			out = task.m_outputs[0]
			# get the number 1..9
			name = out.m_name
			ext = name[-1]
			# and install the file

			Common.install_files('DATADIR', 'man/man%s/' % ext, out.abspath(self.env), self.env)

class gnomeobj(cc.ccobj):
	def __init__(self, type='program'):
		cc.ccobj.__init__(self, type)
		self.link_task = None
		self.m_latask   = None
		self.want_libtool = -1 # fake libtool here

		self._dbus_lst    = []
		self._marshal_lst = []

	def add_dbus_file(self, filename, prefix, mode):
		self._dbus_lst.append([filename, prefix, mode])

	def add_marshal_file(self, filename, prefix, mode):
		self._marshal_lst.append([filename, prefix, mode])

	def apply_core(self):
		for i in self._marshal_lst:
			node = self.path.find_source(i[0])

			if not node:
				fatal('file not found on gnome obj '+i[0])

			env = self.env.copy()

			if i[2] == '--header':

				env['GGM_PREFIX'] = i[1]
				env['GGM_MODE']   = i[2]

				task = self.create_task('glib_genmarshal', env, 2)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.h'))

			elif i[2] == '--body':
				env['GGM_PREFIX'] = i[1]
				env['GGM_MODE']   = i[2]

				task = self.create_task('glib_genmarshal', env, 2)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.c'))

				# this task is really created with self.env
				ctask = self.create_task('cc', self.env)
				ctask.m_inputs = task.m_outputs
				ctask.set_outputs(node.change_ext('.o'))

			else:
				error("unknown type for marshal "+i[2])


		for i in self._dbus_lst:
			node = self.path.find_source(i[0])

			if not node:
				fatal('file not found on gnome obj '+i[0])

			env = self.env.copy()

			env['DBT_PREFIX'] = i[1]
			env['DBT_MODE']   = i[2]

			task = self.create_task('dbus_binding_tool', env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.h'))

		# after our targets are created, process the .c files, etc
		cc.ccobj.apply_core(self)

def setup(bld):
	Action.simple_action('sgml2man', '${SGML2MAN} -o ${TGT[0].bld_dir(env)} ${SRC}  > /dev/null', color='BLUE')

	Action.simple_action('glib_genmarshal',
		'${GGM} ${SRC} --prefix=${GGM_PREFIX} ${GGM_MODE} > ${TGT}',
		color='BLUE')

	Action.simple_action('dbus_binding_tool',
		'${DBT} --prefix=${DBT_PREFIX} --mode=${DBT_MODE} --output=${TGT} ${SRC}',
		color='BLUE')

	Action.simple_action('xmlto', '${XMLTO} html -m ${SRC[1]} ${SRC[0]}')

	Object.register('gnome_sgml2man', gnome_sgml2man)
	Object.register('gnome', gnomeobj)

def detect(conf):

	conf.check_tool('checks')

	sgml2man = conf.find_program('docbook2man')
	#if not sgml2man:
	#	fatal('The program docbook2man is mandatory!')
	conf.env['SGML2MAN'] = sgml2man

	glib_genmarshal = conf.find_program('glib-genmarshal')
	conf.env['GGM'] = glib_genmarshal

	dbus_binding_tool = conf.find_program('dbus-binding-tool')
	conf.env['DBT'] = dbus_binding_tool

	def getstr(varname):
		return getattr(Params.g_options, varname, '')

	prefix  = conf.env['PREFIX']
	datadir = getstr('datadir')
	libdir  = getstr('libdir')
	sysconfdir  = getstr('sysconfdir')
	localstatedir  = getstr('localstatedir')
	if not datadir: datadir = os.path.join(prefix,'share')
	if not libdir:  libdir  = os.path.join(prefix,'lib')
	if not sysconfdir:
		if os.path.normpath(prefix) ==  '/usr':
			sysconfdir = '/etc'
		else:
			sysconfdir  = os.path.join(prefix, 'etc')
	if not localstatedir:
		if os.path.normpath(prefix) ==  '/usr':
			localstatedir = '/var'
		else:
			localstatedir  = os.path.join(prefix, 'var')

	# addefine also sets the variable to the env
	conf.define('GNOMELOCALEDIR', os.path.join(datadir, 'locale'))
	conf.define('DATADIR', datadir)
	conf.define('LIBDIR', libdir)
	conf.define('SYSCONFDIR', sysconfdir)
	conf.define('LOCALSTATEDIR', localstatedir)

	# TODO: maybe the following checks should be in a more generic module.

	#always defined to indicate that i18n is enabled */
	conf.define('ENABLE_NLS', 1)

	# TODO
	#Define to 1 if you have the `bind_textdomain_codeset' function.
	conf.define('HAVE_BIND_TEXTDOMAIN_CODESET', 1)

	# TODO
	#Define to 1 if you have the `dcgettext' function.
	conf.define('HAVE_DCGETTEXT', 1)

	#Define to 1 if you have the <dlfcn.h> header file.
	conf.check_header('dlfcn.h', 'HAVE_DLFCN_H')

	# TODO
	#Define if the GNU gettext() function is already present or preinstalled.
	conf.define('HAVE_GETTEXT', 1)

	#Define to 1 if you have the <inttypes.h> header file.
	conf.check_header('inttypes.h', 'HAVE_INTTYPES_H')

	# TODO FIXME
	#Define if your <locale.h> file defines LC_MESSAGES.
	#conf.add_define('HAVE_LC_MESSAGES', '1')

	#Define to 1 if you have the <locale.h> header file.
	conf.check_header('locale.h', 'HAVE_LOCALE_H')

	#Define to 1 if you have the <memory.h> header file.
	conf.check_header('memory.h', 'HAVE_MEMORY_H')

	#Define to 1 if you have the <stdint.h> header file.
	conf.check_header('stdint.h', 'HAVE_STDINT_H')

	#Define to 1 if you have the <stdlib.h> header file.
	conf.check_header('stdlib.h', 'HAVE_STDLIB_H')

	#Define to 1 if you have the <strings.h> header file.
	conf.check_header('strings.h', 'HAVE_STRINGS_H')

	#Define to 1 if you have the <string.h> header file.
	conf.check_header('string.h', 'HAVE_STRING_H')

	#Define to 1 if you have the <sys/stat.h> header file.
	conf.check_header('sys/stat.h', 'HAVE_SYS_STAT_H')

	#Define to 1 if you have the <sys/types.h> header file.
	conf.check_header('sys/types.h', 'HAVE_SYS_TYPES_H')

	#Define to 1 if you have the <unistd.h> header file.
	conf.check_header('unistd.h', 'HAVE_UNISTD_H')

def set_options(opt):
	try:
		# we do not know yet
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except Exception:
		pass

	for i in "execprefix datadir libdir sysconfdir localstatedir".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

