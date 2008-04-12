#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)

"Gnome support"

import os, re
import Object, Action, Params, Common, Scan, Utils, Runner
import cc
from Params import fatal, error
from Object import taskgen, before, after, feature

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

class gnome_doc_taskgen(Object.task_gen):
	def __init__(self, *k):
		Object.task_gen.__init__(self, *k)
		self.inst_var = 'PREFIX'
		self.inst_dir = 'share/'

	def apply(self):
		self.env['APPNAME'] = self.doc_module
		lst = self.to_list(self.doc_linguas)
		for x in lst:
			tsk = self.create_task('xml2po', self.env)
			node = self.path.find_source(x+'/'+x+'.po')
			src = self.path.find_source('C/%s.xml' % self.doc_module)
			out = self.path.find_build('%s/%s.xml' % (x, self.doc_module))
			tsk.set_inputs([node, src])
			tsk.set_outputs(out)

			tsk2 = self.create_task('xsltproc2po', self.env)
			out2 = self.path.find_build('%s/%s-%s.omf' % (x, self.doc_module, x))
			tsk2.set_outputs(out2)
			node = self.path.find_source(self.doc_module+".omf.in")
			tsk2.m_inputs = [node, out]

			tsk2.m_run_after.append(tsk)


			if Params.g_install:
				inst_dir = self.inst_dir + 'gnome/help/%s/%s' % (self.doc_module, x)
				Common.install_files(self.inst_var, self.inst_dir + "omf", out2.abspath(self.env))
				for y in self.to_list(self.doc_figures):
					try:
						os.stat(self.path.abspath()+'/'+x+'/'+y)
						Common.install_as(self.inst_var, inst_dir+'/'+y, self.path.abspath()+'/'+x+'/'+y)
					except:
						Common.install_as(self.inst_var, inst_dir+'/'+y, self.path.abspath()+'/C/'+y)
				Common.install_as(self.inst_var, inst_dir + '/%s.xml' % self.doc_module, out.abspath(self.env))

# give specs
class xml_to_taskgen(Object.task_gen):
	def __init__(self):
		Object.task_gen(self)
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
		tsk = self.create_task('xmlto', self.env, 6)
		tsk.set_inputs([xmlfile, xsltfile])
		tsk.set_outputs(xmlfile.change_ext('html'))
		tsk.install = {'var':self.inst_var, 'dir':self.inst_dir}

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
		tmp_lst = Params.g_build.raw_deps[variant][node.id]
		name = tmp_lst[0]
		task.set_outputs(Params.g_build.m_curdirnode.find_build(name))

sgml_scanner = sgml_man_scanner()

class gnome_sgml2man_taskgen(Object.task_gen):
	def __init__(self, *k, **kw):
		Object.task_gen.__init__(self)
		self.m_tasks = []
		self.m_appname = k[0] # the first argument is the appname - will disappear
	def apply(self):

		def install_result(task):
			out = task.m_outputs[0]
			name = out.m_name
			ext = name[-1]
			env = task.env()
			Common.install_files('DATADIR', 'man/man%s/' % ext, out.abspath(env), env)

		tree = Params.g_build
		tree.rescan(self.path)
		for node in self.path.files():
			base, ext = os.path.splitext(node.m_name)
			if ext != '.sgml': continue

			task = self.create_task('sgml2man', self.env, 2)
			task.set_inputs(node)
			if Params.g_install: task.install = install_results
			# no outputs, the scanner does it
			# no caching for now, this is not a time-critical feature
			# in the future the scanner can be used to do more things (find dependencies, etc)
			sgml_scanner.do_scan(task, node)

# Unlike the sgml and doc processing, the dbus and marshal beast
# generate c/c++ code that we want to mix
# here we attach new methods to Object.task_gen

@taskgen
def add_marshal_file(self, filename, prefix, mode):
	if not hasattr(self, 'marshal_lst'): self.marshal_lst = []
	self.meths.add('process_marshal')
	self.marshal_lst.append([filename, prefix, mode])

@taskgen
@before('apply_core')
def process_marshal(self):
	for i in getattr(self, 'marshal_lst', []):
		env = self.env.copy()
		node = self.path.find_source(i[0])

		if not node:
			fatal('file not found on gnome obj '+i[0])

		if i[2] == '--header':

			env['GGM_PREFIX'] = i[1]
			env['GGM_MODE']   = i[2]

			task = self.create_task('glib_genmarshal', env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.h'))

		elif i[2] == '--body':
			env['GGM_PREFIX'] = i[1]
			env['GGM_MODE']   = i[2]

			# the c file generated will be processed too
			outnode = node.change_ext('.c')
			self.allnodes.append(outnode)

			task = self.create_task('glib_genmarshal', env, 2)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.c'))
		else:
			error("unknown type for marshal "+i[2])

@taskgen
def add_dbus_file(self, filename, prefix, mode):
	if not hasattr(self, 'dbus_lst'): self.dbus_lst = []
	self.meths.add('process_dbus')
	self.dbus_lst.append([filename, prefix, mode])

@taskgen
@before('apply_core')
def process_dbus(self):
	for i in getattr(self, 'dbus_lst', []):
		env = self.env.copy()
		node = self.path.find_source(i[0])

		if not node:
			fatal('file not found on gnome obj '+i[0])

		env['DBT_PREFIX'] = i[1]
		env['DBT_MODE']   = i[2]

		task = self.create_task('dbus_binding_tool', env, 2)
		task.set_inputs(node)
		task.set_outputs(node.change_ext('.h'))

@taskgen
@before('apply_core')
def process_enums(self):
	for x in getattr(self, 'mk_enums', []):
		# temporary
		env = self.env.copy()
		task = self.create_task('mk_enums', env)
		inputs = []

		# process the source
		src_lst = self.to_list(x['source'])
		if not src_lst:
			Params.fatal('missing source '+str(x))
		src_lst = [self.path.find_source(k) for k in src_lst]
		inputs += src_lst
		env['MK_SOURCE'] = [k.abspath(env) for k in src_lst]

		# find the target
		if not x['target']:
			Params.fatal('missing target '+str(x))
		tgt_node = self.path.find_build(x['target'], create=1)
		if tgt_node.m_name.endswith('.c'):
			self.allnodes.append(tgt_node)
		env['MK_TARGET'] = tgt_node.abspath(env)

		# template, if provided
		if x['template']:
			template_node = self.path.find_source(x['template'])
			env['MK_TEMPLATE'] = '--template %s' % (template_node.abspath(env))
			inputs.append(template_node)

		# update the task instance
		task.set_inputs(inputs)
		task.set_outputs(tgt_node)

@taskgen
def add_glib_mkenum(self, source='', template='', target=''):
	"just a helper"
	if not hasattr(self, 'mk_enums'): self.mk_enums = []
	self.meths.add('process_enums')
	self.mk_enums.append({'source':source, 'template':template, 'target':target})


Action.simple_action('mk_enums', '${GLIB_MKENUM} ${MK_TEMPLATE} ${MK_SOURCE} > ${MK_TARGET}', 'PINK', prio=30)

Action.simple_action('sgml2man', '${SGML2MAN} -o ${TGT[0].bld_dir(env)} ${SRC}  > /dev/null', color='BLUE')

Action.simple_action('glib_genmarshal',
	'${GGM} ${SRC} --prefix=${GGM_PREFIX} ${GGM_MODE} > ${TGT}',
	color='BLUE')

Action.simple_action('dbus_binding_tool',
	'${DBT} --prefix=${DBT_PREFIX} --mode=${DBT_MODE} --output=${TGT} ${SRC}',
	color='BLUE')

Action.simple_action('xmlto', '${XMLTO} html -m ${SRC[1].abspath(env)} ${SRC[0].abspath(env)}')

Action.simple_action('xml2po', '${XML2PO} ${XML2POFLAGS} ${SRC} > ${TGT}', color='BLUE')

# how do you expect someone to understand this?!
xslt_magic = """${XSLTPROC2PO} -o ${TGT[0].abspath(env)} \
--stringparam db2omf.basename ${APPNAME} \
--stringparam db2omf.format docbook \
--stringparam db2omf.lang C \
--stringparam db2omf.dtd '-//OASIS//DTD DocBook XML V4.3//EN' \
--stringparam db2omf.omf_dir ${PREFIX}/share/omf \
--stringparam db2omf.help_dir ${PREFIX}/share/gnome/help \
--stringparam db2omf.omf_in ${SRC[0].abspath(env)} \
--stringparam db2omf.scrollkeeper_cl ${SCROLLKEEPER_DATADIR}/Templates/C/scrollkeeper_cl.xml \
${DB2OMF} ${SRC[1].abspath(env)}"""

#--stringparam db2omf.dtd '-//OASIS//DTD DocBook XML V4.3//EN' \
Action.simple_action('xsltproc2po', xslt_magic, color='BLUE')

def detect(conf):

	conf.check_tool('checks')

	sgml2man = conf.find_program('docbook2man', var='SGML2MAN')
	glib_genmarshal = conf.find_program('glib-genmarshal', var='GGM')
	dbus_binding_tool = conf.find_program('dbus-binding-tool', var='DBT')
	mk_enums_tool = conf.find_program('glib-mkenums', var='GLIB_MKENUM')

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

	xml2po = conf.find_program('xml2po', var='XML2PO')
	xsltproc2po = conf.find_program('xsltproc', var='XSLTPROC2PO')
	conf.env['XML2POFLAGS'] = '-e -p'
	conf.env['SCROLLKEEPER_DATADIR'] = os.popen("scrollkeeper-config --pkgdatadir").read().strip()
	conf.env['DB2OMF'] = os.popen("/usr/bin/pkg-config --variable db2omf gnome-doc-utils").read().strip()

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

