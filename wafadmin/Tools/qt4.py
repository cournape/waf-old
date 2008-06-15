#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"""
Qt4 support

If QT4_ROOT is given (absolute path), the configuration will look in it first

This module also demonstrates how to add tasks dynamically (when the build has started)
"""

try:
	from xml.sax import make_parser
	from xml.sax.handler import ContentHandler
except ImportError:
	has_xml = False
	ContentHandler = object
else:
	has_xml = True

import os, sys
import ccroot, cxx
import Params, TaskGen, Task, Utils, Runner
from TaskGen import taskgen, feature, after, extension
from logging import error, fatal

MOC_H = ['.h', '.hpp', '.hxx', '.hh']
EXT_RCC = ['.qrc']
EXT_UI  = ['.ui']
EXT_QT4 = ['.cpp', '.cc', '.cxx', '.C']

class MTask(Task.Task):
	"A cpp task that may create a moc task dynamically"
	scan = ccroot.scan
	get_signature_queue = ccroot.get_signature_queue

	def __init__(self, env, parent):
		Task.Task.__init__(self, env)
		self.moc_done = 0
		self.parent = parent

	def may_start(self):

		if self.moc_done:
			# if there is a moc task, delay the computation of the file signature
			for t in self.get_run_after():
				if not t.m_hasrun:
					return 0
			# the moc file enters in the dependency calculation
			# so we need to recompute the signature when the moc file is present
			self.signature()
			return Task.Task.may_start(self)
		else:
			self.add_moc_tasks()
			return 0

	def add_moc_tasks(self):

		tree = Params.g_build
		parn = self.parent
		node = self.m_inputs[0]

		# to know if there is a moc file to create
		try:
			self.signature()
		except:
			print "TODO"
		else:
			# remove the signature, it must be recomputed
			delattr(self, 'sign_all')

		moctasks=[]
		mocfiles=[]
		variant = node.variant(parn.env)
		try:
			tmp_lst = tree.raw_deps[variant][node.id]
			tree.raw_deps[variant][node.id] = []
		except KeyError:
			tmp_lst = []
		for d in tmp_lst:
			if not d.endswith('.moc'): continue
			# paranoid check
			if d in mocfiles:
				error("paranoia owns")
				continue
			# process that base.moc only once
			mocfiles.append(d)

			# find the extension - this search is done only once
			ext = ''
			try: ext = Params.g_options.qt_header_ext
			except AttributeError: pass

			if not ext:
				base2 = d[:-4]
				path = node.m_parent.srcpath(parn.env)
				for i in MOC_H:
					try:
						# TODO we could use find_resource
						os.stat(os.path.join(path, base2+i))
					except OSError:
						pass
					else:
						ext = i
						break
				if not ext: fatal("no header found for %s which is a moc file" % str(d))

			# next time we will not search for the extension (look at the 'for' loop below)
			h_node = node.m_parent.find_resource(base2+i)
			m_node = h_node.change_ext('.moc')
			tree.node_deps[variant][m_node.id] = (h_node,)

			# create the task
			task = Task.g_task_types['moc'](parn.env, normal=0)
			task.set_inputs(h_node)
			task.set_outputs(m_node)

			generator = Params.g_build.generator
			generator.outstanding.insert(0, task)
			generator.total += 1

			moctasks.append(task)

		# remove raw deps except the moc files to save space (optimization)
		tmp_lst = tree.raw_deps[variant][node.id] = mocfiles

		# look at the file inputs, it is set right above
		lst = tree.node_deps[variant].get(node.id, ())
		for d in lst:
			name = d.m_name
			if name.endswith('.moc'):
				task = Task.g_task_types['moc'](parn.env, normal=0)
				task.set_inputs(tree.node_deps[variant][d.id][0]) # 1st element in a tuple
				task.set_outputs(d)

				generator = Params.g_build.generator
				generator.outstanding.insert(0, task)
				generator.total += 1

				moctasks.append(task)

		# simple scheduler dependency: run the moc task before others
		self.m_run_after = moctasks
		self.moc_done = 1

	run = Task.g_task_types['cxx'].__dict__["run"]

def translation_update(task):
	outs=[a.abspath(task.env) for a in task.m_outputs]
	outs=" ".join(outs)
	lupdate = task.env['QT_LUPDATE']

	for x in task.m_inputs:
		file = x.abspath(task.env)
		cmd = "%s %s -ts %s" % (lupdate, file, outs)
		Params.pprint('BLUE', cmd)
		Runner.exec_command(cmd)

class XMLHandler(ContentHandler):
	def __init__(self):
		self.buf = []
		self.files = []
	def startElement(self, name, attrs):
		if name == 'file':
			self.buf = []
	def endElement(self, name):
		if name == 'file':
			self.files.append(''.join(self.buf))
	def characters(self, cars):
		self.buf.append(cars)

def scan(self, node):
	"add the dependency on the files referenced in the qrc"
	parser = make_parser()
	curHandler = XMLHandler()
	parser.setContentHandler(curHandler)
	fi = open(self.m_inputs[0].abspath(self.env))
	parser.parse(fi)
	fi.close()

	nodes = []
	names = []
	root = self.m_inputs[0].m_parent
	for x in curHandler.files:
		x = x.encode('utf8')
		nd = root.find_resource(x)
		if nd: nodes.append(nd)
		else: names.append(x)

	return (nodes, names)

@extension(EXT_RCC)
def create_rcc_task(self, node):
	"hook for rcc files"

	rcnode = node.change_ext('_rc.cpp')

	rcctask = self.create_task('rcc', self.env)
	rcctask.m_inputs = [node]
	rcctask.m_outputs = [rcnode]

	cpptask = self.create_task('cxx', self.env)
	cpptask.m_inputs  = [rcnode]
	cpptask.m_outputs = [rcnode.change_ext('.o')]

	self.compiled_tasks.append(cpptask)

	return cpptask

@extension(EXT_UI)
def create_uic_task(self, node):
	"hook for uic tasks"
	uictask = self.create_task('ui4', self.env)
	uictask.m_inputs    = [node]
	uictask.m_outputs   = [node.change_ext('.h')]

class qt4_taskgen(cxx.cxx_taskgen):
	def __init__(self, *kw):
		cxx.cxx_taskgen.__init__(self, *kw)
		self.link_task = None
		self.lang = ''
		self.langname = ''
		self.update = 0
		self.features.append('qt4')

@taskgen
@feature('qt4')
@after('apply_link')
def apply_qt4(self):
	if self.lang:
		lst=[]
		trans=[]
		for l in self.to_list(self.lang):
			t = Task.g_task_types['ts2qm']('ts2qm', self.env)
			t.set_inputs(self.path.find_resource(l+'.ts'))
			t.set_outputs(t.m_inputs[0].change_ext('.qm'))
			lst.append(t.m_outputs[0])

			if self.update:
				trans.append(t.m_inputs[0])

		if self.update and Params.g_options.trans_qt4:
			# we need the cpp files given, except the rcc task we create after
			# FIXME may be broken
			u = Task.TaskCmd(translation_update, self.env, 2)
			u.m_inputs = [a.m_inputs[0] for a in self.compiled_tasks]
			u.m_outputs = trans

		if self.langname:
			t = Task.g_task_types['qm2rcc']('qm2rcc', self.env)
			t.set_inputs(lst)
			t.set_outputs(self.path.find_build(self.langname+'.qrc'))
			t.path = self.path
			k = create_rcc_task(self, t.m_outputs[0])
			self.link_task.m_inputs.append(k.m_outputs[0])

	lst = []
	for flag in self.to_list(self.env['CXXFLAGS']):
		if len(flag) < 2: continue
		if flag[0:2] == '-D' or flag[0:2] == '-I':
			lst.append(flag)
	self.env['MOC_FLAGS'] = lst

def find_sources_in_dirs(self, dirnames, excludes=[], exts=[]):
	"the .ts files are added to self.lang"
	lst=[]
	excludes = self.to_list(excludes)
	#make sure dirnames is a list helps with dirnames with spaces
	dirnames = self.to_list(dirnames)

	ext_lst = exts or self.mappings.keys() + TaskGen.task_gen.mappings.keys()

	for name in dirnames:
		anode = self.path.find_dir(name)
		Params.g_build.rescan(anode)

		for name in Params.g_build.cache_dir_contents[anode.id]:
			(base, ext) = os.path.splitext(name)
			if ext in ext_lst:
				if not name in lst:
					if name in excludes: continue
					lst.append((anode.relpath(self.path) or '.') + '/' + name)
			elif ext == '.ts':
				self.lang += ' '+base

	lst.sort()
	self.source = self.source+' '+(" ".join(lst))
setattr(qt4_taskgen, 'find_sources_in_dirs', find_sources_in_dirs)

@extension(EXT_QT4)
def cxx_hook(self, node):
	# create the compilation task: cpp or cc
	task = MTask('cxx', self.env, self)
	self.m_tasks.append(task)
	try: obj_ext = self.obj_ext
	except AttributeError: obj_ext = '_%d.o' % self.idx

	task.defines  = self.scanner_defines

	task.m_inputs = [node]
	task.m_outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

def process_qm2rcc(task):
	outfile = task.m_outputs[0].abspath(task.env)
	f = open(outfile, 'w')
	f.write('<!DOCTYPE RCC><RCC version="1.0">\n<qresource>\n')
	for k in task.m_inputs:
		f.write(' <file>')
		#f.write(k.m_name)
		f.write(k.relpath(task.path))
		f.write('</file>\n')
	f.write('</qresource>\n</RCC>')
	f.close()

b = Task.simple_task_type
b('moc', '${QT_MOC} ${MOC_FLAGS} ${SRC} ${MOC_ST} ${TGT}', color='BLUE', vars=['QT_MOC', 'MOC_FLAGS'])
cls = b('rcc', '${QT_RCC} -name ${SRC[0].m_name} ${SRC[0].abspath(env)} ${RCC_ST} -o ${TGT}', color='BLUE', before='cxx moc', after="qm2rcc")
cls.scan = scan
b('ui4', '${QT_UIC} ${SRC} -o ${TGT}', color='BLUE', before='cxx moc')
b('ts2qm', '${QT_LRELEASE} ${QT_LRELEASE_FLAGS} ${SRC} -qm ${TGT}', color='BLUE', before='qm2rcc')

Task.task_type_from_func('qm2rcc', vars=[], func=process_qm2rcc, color='BLUE', before='rcc', after='ts2qm')

def detect_qt4(conf):
	env = conf.env
	opt = Params.g_options

	qtlibs = getattr(opt, 'qtlibs', '')
	qtincludes = getattr(opt, 'qtincludes', '')
	qtbin = getattr(opt, 'qtbin', '')
	useframework = getattr(opt, 'use_qt4_osxframework', True)
	qtdir = getattr(opt, 'qtdir', '')

	if not qtdir: qtdir = os.environ.get('QT4_ROOT', '')

	if not qtdir:
		try:
			lst = os.listdir('/usr/local/Trolltech/')
			lst.sort()
			lst.reverse()
			qtdir = '/usr/local/Trolltech/%s/' % lst[0]

		except OSError:
			pass

	if not qtdir:
		try:
			path = os.environ['PATH'].split(':')
			for qmk in ['qmake-qt4', 'qmake4', 'qmake']:
				qmake = conf.find_program(qmk, path)
				if qmake:
					version = os.popen(qmake+" -query QT_VERSION").read().strip().split('.')
					if version[0] == "4":
						qtincludes = os.popen(qmake+" -query QT_INSTALL_HEADERS").read().strip()
						qtdir = os.popen(qmake + " -query QT_INSTALL_PREFIX").read().strip()+"/"
						qtbin = os.popen(qmake + " -query QT_INSTALL_BINS").read().strip()+"/"
						break
		except OSError:
			pass

	# check for the qt includes first
	if not qtincludes: qtincludes = qtdir + 'include/'
	env['QTINCLUDEPATH']=qtincludes

	lst = [qtincludes, '/usr/share/qt4/include/', '/opt/qt4/include']
	test = conf.create_header_enumerator()
	test.name = 'QtGui/QFont'
	test.path = lst
	test.mandatory = 1
	ret = test.run()


	# check for the qtbinaries
	if not qtbin: qtbin = qtdir + 'bin/'

	binpath = [qtbin, '/usr/share/qt4/bin/'] + os.environ['PATH'].split(':')
	def find_bin(lst, var):
		for f in lst:
			ret = conf.find_program(f, path_list=binpath)
			if ret:
				env[var]=ret
				break

	find_bin(['uic-qt3', 'uic3'], 'QT_UIC3')

	find_bin(['uic-qt4', 'uic'], 'QT_UIC')
	version = os.popen(env['QT_UIC'] + " -version 2>&1").read().strip()
	version = version.replace('Qt User Interface Compiler ','')
	version = version.replace('User Interface Compiler for Qt', '')
	if version.find(" 3.") != -1:
		conf.check_message('uic version', '(too old)', 0, option='(%s)'%version)
		sys.exit(1)
	conf.check_message('uic version', '', 1, option='(%s)'%version)

	find_bin(['moc-qt4', 'moc'], 'QT_MOC')
	find_bin(['rcc'], 'QT_RCC')
	find_bin(['lrelease-qt4', 'lrelease'], 'QT_LRELEASE')
	find_bin(['lupdate-qt4', 'lupdate'], 'QT_LUPDATE')

	env['UIC3_ST']= '%s -o %s'
	env['UIC_ST'] = '%s -o %s'
	env['MOC_ST'] = '-o'
	env['QT_LRELEASE_FLAGS'] = ['-silent']

	# check for the qt libraries
	if not qtlibs: qtlibs = qtdir + 'lib'

	vars = "Qt3Support QtCore QtGui QtNetwork QtOpenGL QtSql QtSvg QtTest QtXml QtWebKit".split()

	framework_ok = False
	if sys.platform == "darwin" and useframework:
		for i in vars:
			e = conf.create_framework_configurator()
			e.path = [qtlibs]
			e.name = i
			e.remove_dot_h = 1
			e.run()

			if not i == 'QtCore':
				# strip -F flag so it don't get reduant
				for r in env['CCFLAGS_' + i.upper()]:
					if r.startswith('-F'):
						env['CCFLAGS_' + i.upper()].remove(r)
						break

			incflag = '-I%s' % os.path.join(qtincludes, i)
			if not incflag in env["CCFLAGS_" + i.upper ()]:
				env['CCFLAGS_' + i.upper ()] += [incflag]
			if not incflag in env["CXXFLAGS_" + i.upper ()]:
				env['CXXFLAGS_' + i.upper ()] += [incflag]

		# now we add some static depends.
		if conf.is_defined("HAVE_QTOPENGL"):
			if not '-framework OpenGL' in env["LINKFLAGS_QTOPENGL"]:
				env["LINKFLAGS_QTOPENGL"] += ['-framework OpenGL']

		if conf.is_defined("HAVE_QTGUI"):
			if not '-framework AppKit' in env["LINKFLAGS_QTGUI"]:
				env["LINKFLAGS_QTGUI"] += ['-framework AppKit']
			if not '-framework ApplicationServices' in env["LINKFLAGS_QTGUI"]:
				env["LINKFLAGS_QTGUI"] += ['-framework ApplicationServices']

		framework_ok = True

	if not framework_ok: # framework_ok is false either when the platform isn't OSX, Qt4 shall not be used as framework, or Qt4 could not be found as framework
		vars_debug = [a+'_debug' for a in vars]

		for i in vars_debug+vars:
			#conf.check_pkg(i, pkgpath=qtlibs)
			pkgconf = conf.create_pkgconfig_configurator()
			pkgconf.name = i
			pkgconf.pkgpath = '%s:%s/pkgconfig:/usr/lib/qt4/lib/pkgconfig:/opt/qt4/lib/pkgconfig:/usr/lib/qt4/lib:/opt/qt4/lib' % (qtlibs, qtlibs)
			pkgconf.run()


		# the libpaths are set nicely, unfortunately they make really long command-lines
		# remove the qtcore ones from qtgui, etc
		def process_lib(vars_, coreval):
			for d in vars_:
				var = d.upper()
				if var == 'QTCORE': continue

				value = env['LIBPATH_'+var]
				if value:
					core = env[coreval]
					accu = []
					for lib in value:
						if lib in core: continue
						accu.append(lib)
					env['LIBPATH_'+var] = accu

		process_lib(vars, 'LIBPATH_QTCORE')
		process_lib(vars_debug, 'LIBPATH_QTCORE_DEBUG')

		# rpath if wanted
		if Params.g_options.want_rpath:
			def process_rpath(vars_, coreval):
				for d in vars_:
					var = d.upper()
					value = env['LIBPATH_'+var]
					if value:
						core = env[coreval]
						accu = []
						for lib in value:
							if var != 'QTCORE':
								if lib in core:
									continue
							accu.append('-Wl,--rpath='+lib)
						env['RPATH_'+var] = accu
			process_rpath(vars, 'LIBPATH_QTCORE')
			process_rpath(vars_debug, 'LIBPATH_QTCORE_DEBUG')

	env['QTLOCALE'] = str(env['PREFIX'])+'/share/locale'

def detect(conf):
	if sys.platform=='win32': fatal('Qt4.py will not work on win32 for now - ask the author')
	detect_qt4(conf)

def set_options(opt):
	try: opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except Exception: pass

	opt.add_option('--header-ext',
		type='string',
		default='',
		help='header extension for moc files',
		dest='qt_header_ext')

	for i in "qtdir qtincludes qtlibs qtbin".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

	if sys.platform == "darwin":
		opt.add_option('--no-qt4-framework', action="store_false", help='do not use the framework version of Qt4 in OS X', dest='use_qt4_osxframework',default=True)

	opt.add_option('--translate', action="store_true", help="collect translation strings", dest="trans_qt4", default=False)

