#! /usr/bin/env python
# encoding: utf-8

"""
Qt3 support

If QTDIR is given (absolute path), the configuration will look in it first
"""

import os, sys
import ccroot, cpp
import Action, Params, Object, Task, Utils
from Params import error, fatal
from Params import set_globals, globals

set_globals('MOC_H', ['.hpp', '.hxx', '.hh', '.h'])
set_globals('UI_EXT', ['.ui'])

uic_vardeps = ['QT_UIC', 'UIC_FLAGS', 'UIC_ST']

class MTask(Task.Task):
	"A cpp task that may create a moc task dynamically"
	def __init__(self, action_name, env, parent, priority=10):
		Task.Task.__init__(self, action_name, env, priority)
		self.moc_done = 0
		self.parent = parent

	def may_start(self):
		if self.moc_done: return Task.Task.may_start(self)

		tree = Params.g_build
		parn = self.parent
		node = self.m_inputs[0]

		# scan the .cpp files and find if there is a moc file to run
		if tree.needs_rescan(node, parn.env):
			ccroot.g_c_scanner.do_scan(node, parn.env, hashparams = self.m_scanner_params)

		moctasks=[]
		mocfiles=[]
		variant = node.variant(parn.env)
		try:
			tmp_lst = tree.m_raw_deps[variant][node]
		except:
			tmp_lst = []
		for d in tmp_lst:
			base2, ext2 = os.path.splitext(d)
			if not ext2 == '.moc': continue
			# paranoid check
			if d in mocfiles:
				error("paranoia owns")
				continue
			# process that base.moc only once
			mocfiles.append(d)

			# find the extension - this search is done only once
			if Params.g_options.qt_header_ext:
				ext = Params.g_options.qt_header_ext
			else:
				path = node.m_parent.srcpath(parn.env)
				for i in globals('MOC_H'):
					try:
						os.stat(Utils.join_path(path,base2+i))
						ext = i
						break
					except:
						pass
				if not ext: fatal("no header found for %s which is a moc file" % str(d))

			# next time we will not search for the extension (look at the 'for' loop below)
			h_node = node.change_ext(ext)
			m_node = node.change_ext('.moc')
			tree.m_depends_on[variant][m_node] = h_node

			# create the task
			task = parn.create_task('moc_hack', parn.env)
			task.set_inputs(h_node)
			task.set_outputs(m_node)
			moctasks.append(task)
		# look at the file inputs, it is set right above
		for d in tree.m_depends_on[variant][node]:
			deps = tree.m_depends_on[variant]
			name = d.m_name
			if name[-4:]=='.moc':
				task = parn.create_task('moc_hack', parn.env)
				task.set_inputs(tree.m_depends_on[variant][d])
				task.set_outputs(d)
				moctasks.append(task)
				break
		self.m_run_after = moctasks
		self.moc_done = 1
		return Task.Task.may_start(self)

def create_uic_task(self, node):
	"hook for uic tasks"
	uictask = self.create_task('uic3', self.env, 6)
	uictask.m_inputs    = [node]
	uictask.m_outputs   = [node.change_ext('.h')]

class qt3obj(cpp.cppobj):
	def __init__(self, type='program'):
		cpp.cppobj.__init__(self, type)
		self.m_linktask = None
		self.m_latask = None

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib']

	def create_task(self, type, env=None, nice=10):
		"overrides Object.create_task to catch the creation of cpp tasks"

		if env is None: env=self.env
		if type == 'cpp':
			task = MTask(type, env, self, nice)
		elif type == 'cpp_ui':
			task = Task.Task('cpp', env, nice)
		elif type == 'moc_hack': # add a task while the build has started
			task = Task.Task('moc', env, nice, normal=0)
			generator = Params.g_build.m_generator
			#generator.m_outstanding.append(task)
			generator.m_outstanding = [task] + generator.m_outstanding
			generator.m_total += 1
		else:
			task = Task.Task(type, env, nice)

		self.m_tasks.append(task)
		if type == 'cpp': self.p_compiletasks.append(task)
		return task

def setup(env):
	Action.simple_action('moc', '${QT_MOC} ${MOC_FLAGS} ${SRC} ${MOC_ST} ${TGT}', color='BLUE')
	Action.simple_action('uic3', '${QT_UIC} ${SRC} -o ${TGT}', color='BLUE')
	Object.register('qt3', qt3obj)

	try: env.hook('qt3', 'UI_EXT', create_uic_task)
	except: pass

def detect_qt3(conf):

	env = conf.env
	opt = Params.g_options

	try: qtlibs = opt.qtlibs
	except: qtlibs=''

	try: qtincludes = opt.qtincludes
	except: qtincludes=''

	try: qtbin = opt.qtbin
	except: qtbin=''

	# if qtdir is given - helper for finding qtlibs, qtincludes and qtbin
	try: qtdir = opt.qtdir
	except: qtdir=''

	if not qtdir: qtdir = os.environ.get('QTDIR', '')

	# Debian/Ubuntu support ('/usr/share/qt3/')
	# Gentoo support ('/usr/qt/3')
	if not qtdir:
		candidates = ['/usr/share/qt3/', '/usr/qt/3/']

		for candidate in candidates:
			if os.path.exists(candidate):
				qtdir = candidate
				break

	if qtdir and qtdir[len(qtdir)-1] != '/':
		qtdir += '/'

	if qtdir:
		env['QT3_DIR'] = qtdir

	if not qtdir:
		if qtlibs and qtincludes and qtbin:
			Params.pprint("YELLOW", "No valid qtdir found; using the specified qtlibs, qtincludes and qtbin params");
		else:
			fatal("Cannot find a valid qtdir, and not enough parameters are set; either specify a qtdir, or qtlibs, qtincludes and qtbin params")

	# check for the qtbinaries
	if not qtbin: qtbin = qtdir + 'bin/'

	# If a qtbin (or a qtdir) param was given, test the version-neutral names first
	if qtbin:
		moc_candidates = ['moc', 'moc-qt3']
		uic_candidates = ['uic', 'uic3', 'uic-qt3']
	else:
		moc_candidates = ['moc-qt3', 'moc']
		uic_candidates = ['uic-qt3', 'uic3', 'uic']

	binpath = [qtbin] + os.environ['PATH'].split(':')
	def find_bin(lst, var):
		for f in lst:
			ret = conf.find_program(f, path_list=binpath)
			if ret:
				env[var]=ret
				return ret

	if not find_bin(uic_candidates, 'QT_UIC'):
		fatal("uic not found!")
	version = os.popen(env['QT_UIC'] + " -version 2>&1").read().strip()
	version = version.replace('Qt User Interface Compiler ','')
	version = version.replace('User Interface Compiler for Qt', '')
	if version.find(" 3.") == -1:
		conf.check_message('uic version', '(not a 3.x uic)', 0, option='(%s)'%version)
		sys.exit(1)
	conf.check_message('uic version', '', 1, option='%s'%version)

	if not find_bin(moc_candidates, 'QT_MOC'):
		fatal("moc not found!")

	env['UIC_ST'] = '%s -o %s'
	env['MOC_ST'] = '-o'

	if not qtincludes: qtincludes = qtdir + 'include/'
	if not qtlibs: qtlibs = qtdir + 'lib/'

	# check for the qt-mt package
	pkgconf = conf.create_pkgconfig_configurator()
	pkgconf.name = 'qt-mt'
	pkgconf.uselib = 'QT3'
	pkgconf.path = qtlibs
	if not pkgconf.run():
		Params.pprint("YELLOW", "qt-mt package not found - trying to enumerate paths & flags manually");

		# check for the qt includes first
		lst = [qtincludes, '/usr/qt/3/include', '/usr/include/qt3', '/opt/qt3/include', '/usr/local/include', '/usr/include']
		headertest = conf.create_header_enumerator()
		headertest.name = 'qt.h'
		headertest.path = lst
		headertest.mandatory = 1
		ret = headertest.run()
		env['CPPPATH_QT3'] = ret

		# now check for the qt libs
		lst = [qtlibs, '/usr/qt/3/lib', '/usr/lib/qt3', '/opt/qt3/lib', '/usr/local/lib', '/usr/lib']
		libtest = conf.create_library_enumerator()
		libtest.name = 'qt-mt'
		libtest.path = lst
		libtest.mandatory = 1
		ret = libtest.run()
		env['LIBPATH_QT3'] = ret
		env['LIB_QT3'] = 'qt-mt'

	env['QT3_FOUND'] = 1

	# rpath settings
	# TODO Carlos: Check if this works in darwin
	try:
		if Params.g_options.want_rpath:
			env['RPATH_QT3']=['-Wl,--rpath='+qtlibs]
	except:
		pass

def detect(conf):
	if sys.platform=='win32': fatal('Qt3.py will not work on win32 for now - ask the author')
	else: detect_qt3(conf)
	return 0

def set_options(opt):
	try: opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except: pass

	opt.add_option('--header-ext',
		type='string',
		default='',
		help='header extension for moc files',
		dest='qt_header_ext')

	qtparams = {}
	qtparams['qtdir'] = 'manual QTDIR specification (autodetected)'
	qtparams['qtbin'] = 'path to the Qt3 binaries (moc, uic) (autodetected)'
	qtparams['qtincludes'] = 'path to the Qt3 includes (autodetected)'
	qtparams['qtlibs'] = 'path to the Qt3 libraries (autodetected)'
	for name, desc in qtparams.iteritems():
		opt.add_option('--'+name, type='string', default='', help=desc, dest=name)


