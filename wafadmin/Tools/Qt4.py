#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Qt4 support"

import os, sys, string
import ccroot, cpp
import Action, Params, Configure, Scan, Runner, Object, Task
from Params import error, trace, fatal
from Params import set_globals, globals

set_globals('MOC_H', ['.hh', '.h'])
set_globals('RCC_EXT', ['.qrc'])
set_globals('UI_EXT', ['.ui'])

uic_vardeps = ['QT_UIC', 'UIC_FLAGS', 'UIC_ST']
rcc_vardeps = ['QT_RCC', 'RCC_FLAGS']

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
				path = node.m_parent.srcpath(parn.env) + os.sep
				for i in globals('MOC_H'):
					try:
						os.stat(path+base2+i)
						ext = i
						break
					except:
						pass
				if not ext: fatal("no header found for %s which is a moc file" % filename)

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

def create_rcc_task(self, node):
	"hook for rcc files"
	# run rcctask with one of the highest priority
	# TODO add the dependency on the files listed in .qrc
	rcnode = node.change_ext('_rc.cpp')

	rcctask = self.create_task('rcc', self.env, 6)
	rcctask.m_inputs = [node]
	rcctask.m_outputs = [rcnode]

	cpptask = self.create_task('cpp', self.env)
	cpptask.m_inputs  = [rcnode]
	cpptask.m_outputs = [node.change_ext('.o')]

def create_uic_task(self, node):
	"hook for uic tasks"
	uictask = self.create_task('uic4', self.env, 6)
	uictask.m_inputs    = [node]
	uictask.m_outputs   = [node.change_ext('.h')]

class qt4obj(cpp.cppobj):
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
	Action.simple_action('rcc', '${QT_RCC} -name ${SRC[0].m_name} ${SRC} ${RCC_ST} -o ${TGT}', color='BLUE')
	Action.simple_action('uic4', '${QT_UIC} ${SRC} -o ${TGT}', color='BLUE')
	Object.register('qt4', qt4obj)

	try: env.hook('qt4', 'UI_EXT', create_uic_task)
	except: pass

	try: env.hook('qt4', 'RCC_EXT', create_rcc_task)
	except: pass

def detect_qt4(conf):
	env = conf.env

	try:
		qtlibs     = Params.g_options.qtlib
	except:
		qtlibs=''
		pass

	try:
		qtincludes = Params.g_options.qtincludes
	except:
		qtincludes=''
		pass

	try:
		qtbin      = Params.g_options.qtbin
	except:
		qtbin=''
		pass

	try:
		qtdir      = Params.g_options.qtdir
	except:
		qtbin = ''
		pass


	p=Params.pprint

	# do our best to find the QTDIR (non-Debian systems)
	if not qtdir:
		qtdir = os.getenv('QTDIR')

	# TODO what if there are only static Qt libraries ?
	if qtdir:
		if Configure.find_file('lib/libqt-mt'+str(env['shlib_SUFFIX']), [qtdir]):
			p('YELLOW', 'The QTDIR %s is for Qt3, we need to find something else' % qtdir)
			qtdir=None
	if not qtdir:
		qtdir=Configure.find_path('include/', [ # lets find the Qt include directory
				'/usr/local/Trolltech/Qt-4.2.4/',
				'/usr/local/Trolltech/Qt-4.2.3/',
				'/usr/local/Trolltech/Qt-4.2.2/',
				'/usr/local/Trolltech/Qt-4.2.1/',
				'/usr/local/Trolltech/Qt-4.2.0/',
				'/usr/local/Trolltech/Qt-4.1.3/',
				'/usr/local/Trolltech/Qt-4.1.2/',
				'/usr/local/Trolltech/Qt-4.1.1/',
				'/usr/local/Trolltech/Qt-4.1.0/',
				'/usr/local/Trolltech/Qt-4.0.3/',
				'/usr/local/Trolltech/Qt-4.0.2/',
				'/usr/local/Trolltech/Qt-4.0.1/',
				'/usr/local/Trolltech/Qt-4.0.0/',
				'/usr/share/qt4' ]) # Ubuntu/Debian default
		if qtdir: p('YELLOW', 'The QTDIR was found as '+qtdir)
		else:     p('YELLOW', 'There is no QTDIR set')
	else: env['QTDIR'] = qtdir.strip()

	# if we have the QTDIR, finding the qtlibs and qtincludes is easy
	if qtdir:
		if not qtlibs:     qtlibs     = os.path.join(qtdir, 'lib')
		if not qtincludes: qtincludes = os.path.join(qtdir, 'include')
		if not qtbin:      qtbin      = os.path.join(qtdir, 'bin')
		#os.putenv('PATH', os.path.join(qtdir , 'bin') + ":" + os.getenv("PATH")) # TODO ita

	# Check for uic, uic-qt3, moc, rcc, ..
	def find_qt_bin(progs):
		# first use the qtdir
		path=''
		lst = [os.path.join(qtdir, 'bin')]
		if qtbin: lst = [qtbin]+lst+os.environ['PATH'].split(':')
		#print qtbin
		#print lst
		for prog in progs:
			path=conf.find_program(prog, path_list=lst, var=string.upper(prog))
			if path: return path

		# everything failed
		p('RED',"%s was not found - make sure Qt4-devel is installed, or set $QTDIR or $PATH" % prog)
		sys.exit(1)

	env['QT_UIC3']= find_qt_bin(['uic-qt3', 'uic3'])
	env['UIC3_ST']= '%s -o %s'

	env['QT_UIC'] = find_qt_bin(['uic-qt4', 'uic'])
	env['UIC_ST'] = '%s -o %s'

	env['QT_MOC'] = find_qt_bin(['moc-qt4', 'moc'])
	env['MOC_ST'] = '-o'

	env['QT_RCC'] = find_qt_bin(['rcc'])

	# TODO is this really needed now ?
	print "Checking for uic3 version               :",
	version = os.popen(env['QT_UIC'] + " -version 2>&1").read().strip()
	if version.find(" 3.") != -1:
		version = version.replace('Qt user interface compiler','')
		version = version.replace('User Interface Compiler for Qt', '')
		p('RED', version + " (too old)")
		sys.exit(1)
	p('GREEN', "fine - %s" % version)

	#if os.environ.has_key('PKG_CONFIG_PATH'):
	#	os.environ['PKG_CONFIG_PATH'] = os.environ['PKG_CONFIG_PATH'] + ':' + qtlibs
	#else:
	#	os.environ['PKG_CONFIG_PATH'] = qtlibs

	## check for the Qt4 includes
	print "Checking for the Qt4 includes           :",
	if qtincludes and os.path.isfile(qtincludes + "/QtGui/QFont"):
		# The user told where to look for and it looks valid
		p('GREEN','ok '+qtincludes)
	else:
		if os.path.isfile(qtdir+'/include/QtGui/QFont'):
			# Automatic detection
			p('GREEN','ok '+qtdir+"/include/")
			qtincludes = qtdir + "/include/"
		elif os.path.isfile("/usr/include/qt4/QtGui/QFont"):
			# Debian probably
			p('YELLOW','the Qt headers were found in /usr/include/qt4/')
			qtincludes = "/usr/include/qt4"
		elif os.path.isfile("/usr/include/QtGui/QFont"):
			# e.g. SUSE 10
			p('YELLOW','the Qt headers were found in /usr/include/')
			qtincludes = "/usr/include"
		else:
			p('RED',"the Qt headers were not found")
			sys.exit(1)


	#env['QTPLUGINS']=os.popen('kde-config --expandvars --install qtplugins').read().strip()

	## Qt libs and includes
	env['QTINCLUDEPATH']=qtincludes
	if not qtlibs: qtlibs=qtdir+'/lib'
	env['QTLIBPATH']=qtlibs

	# now that we have qtlibs ..
	vars = '''
Qt3Support_debug
Qt3Support
QtCore_debug
QtCore
QtGui_debug
QtGui
QtNetwork_debug
QtNetwork
QtOpenGL_debug
QtOpenGL
QtSql_debug
QtSql
QtSvg_debug
QtSvg
QtTest_debug
QtTest
QtXml_debug
QtXml
'''

	for i in vars.split():
		#conf.check_pkg(i, pkgpath=qtlibs)
		pkgconf = conf.create_pkgconfig_configurator()
		pkgconf.name = i
		pkgconf.path = qtlibs
		pkgconf.run()

	## link against libqt_debug when appropriate
	#if env['BKS_DEBUG']: debug='_debug'
	#else:                debug=''

	# TODO
	"""
	# rpath settings
	try:
		if Params.g_options.want_rpath:

			lst = ['-Wl,--rpath='+env['QTLIBPATH']]
			for d in env['LIBPATH_X11']:
				lst.append('-Wl,--rpath='+d)

			env['RPATH_QT']         = lst
			env['RPATH_QT3SUPPORT'] = env['RPATH_QT']
			env['RPATH_QTCORE']     = env['RPATH_QT']
			env['RPATH_QTNETWORK']  = env['RPATH_QT']
			env['RPATH_QTGUI']      = env['RPATH_QT']
			env['RPATH_QTOPENGL']   = env['RPATH_QT']
			env['RPATH_QTSQL']      = env['RPATH_QT']
			env['RPATH_QTXML']      = env['RPATH_QT']
			env['RPATH_QTEST']      = env['RPATH_QT']
	except:
		pass
	"""

	env['QTLOCALE']            = str(env['PREFIX'])+'/share/locale'

def detect_qt4_win32(conf):
	print "win32 code"
	env = conf.env

	#def getpath(varname):
	#	if not env.has_key('ARGS'): return None
	#	v=env['ARGS'].get(varname, None)
	#	if v : v=os.path.abspath(v)
	#	return v
	#qtincludes	= getpath('qtincludes')
	#qtlibs		= getpath('qtlibs')
	qtlibs     = ''
	qtincludes = ''
	p = Params.pprint

		# do our best to find the QTDIR (non-Debian systems)
	qtdir = os.getenv('QTDIR')

	# TODO what if there are only static Qt libraries ?
	if qtdir and Configure.find_file('lib/libqt-mt' + str(env['shlib_SUFFIX']), qtdir): 
		qtdir = None
	if not qtdir:
		qtdir = Configure.find_path('include/', [ # lets find the Qt include directory
				'c:\\Programme\\Qt\\4.1.0',
				'c:\\Qt\\4.1.0',
				'f:\\Qt\\4.1.0'])
		if qtdir: p('YELLOW', 'The qtdir was found as '+qtdir)
		else:     p('YELLOW', 'There is no QTDIR set')
	else: env['QTDIR'] = qtdir.strip()

	# if we have the QTDIR, finding the qtlibs and qtincludes is easy
	if qtdir:
		if not qtlibs:
			qtlibs     = os.path.join(qtdir, 'lib')
		if not qtincludes: 
			qtincludes = os.path.join(qtdir, 'include')
		#os.putenv('PATH', os.path.join(qtdir , 'bin') + ":" + os.getenv("PATH")) # TODO ita

	# Check for uic, uic-qt3, moc, rcc, ..
	def find_qt_bin(progs):
		# first use the qtdir
		path=''
		for prog in progs:
			lst = [os.path.join(qtdir, 'bin')] + os.environ['PATH'].split(':')
			path=conf.find_program(prog, path_list=lst, var=string.upper(prog))
			if path: 
				return path

		# everything failed
		p('RED',"%s was not found - make sure Qt4-devel is installed, or set $QTDIR or $PATH" % prog)
		sys.exit(1)

	env['QT_UIC3']= find_qt_bin(['uic-qt3', 'uic3'])
	env['UIC3_ST']= '%s -o %s'

	env['QT_UIC'] = find_qt_bin(['uic-qt4', 'uic'])
	env['UIC_ST'] = '%s -o %s'

	env['QT_MOC'] = find_qt_bin(['moc-qt4', 'moc'])
	env['MOC_ST'] = '%s -o %s'

	env['QT_RCC'] = find_qt_bin(['rcc'])

	# TODO is this really needed now ?
	print "Checking for uic3 version      :",
	version = os.popen(env['QT_UIC'] + " -version 2>&1").read().strip()
	if version.find(" 3.") != -1:
		version = version.replace('Qt user interface compiler','')
		version = version.replace('User Interface Compiler for Qt', '')
		p('RED', version + " (too old)")
		sys.exit(1)
	p('GREEN', "fine - %s" % version)

	#if os.environ.has_key('PKG_CONFIG_PATH'):
	#	os.environ['PKG_CONFIG_PATH'] = os.environ['PKG_CONFIG_PATH'] + ':' + qtlibs
	#else:
	#	os.environ['PKG_CONFIG_PATH'] = qtlibs

	## check for the Qt4 includes
	print "Checking for the Qt4 includes  :",
	if qtincludes and os.path.isfile(qtincludes + "/QtGui/QFont"):
		# The user told where to look for and it looks valid
		p('GREEN','ok '+qtincludes)
	else:
		if os.path.isfile(qtdir+'/include/QtGui/QFont'):
			# Automatic detection
			p('GREEN','ok '+qtdir+"/include/")
			qtincludes = qtdir + "/include/"
		elif os.path.isfile("/usr/include/qt4/QtGui/QFont"):
			# Debian probably
			p('YELLOW','the Qt headers were found in /usr/include/qt4/')
			qtincludes = "/usr/include/qt4"
		elif os.path.isfile("/usr/include/QtGui/QFont"):
			# e.g. SUSE 10
			p('YELLOW','the Qt headers were found in /usr/include/')
			qtincludes = "/usr/include"
		else:
			p('RED',"the Qt headers were not found")
			sys.exit(1)


	#env['QTPLUGINS']=os.popen('kde-config --expandvars --install qtplugins').read().strip()

	## Qt libs and includes
	env['QTINCLUDEPATH']=qtincludes
	if not qtlibs: 
		qtlibs=qtdir+'/lib'
	env['QTLIBPATH']=qtlibs

	########## X11
	env['LIB_X11']             = ['X11']
	env['LIBPATH_X11']         = ['/usr/X11R6/lib/']
	env['LIB_XRENDER']         = ['Xrender']

	# link against libqt_debug when appropriate
	if env['BKS_DEBUG']: 
		debug='_debug'
	else:
		debug = '4'

	if not env['LIB_Z']:
		env['LIB_Z']         = ['z']
		env['LIB_PNG']       = ['png', 'm'] + env['LIB_Z']
		env['LIB_SM']        = ['SM', 'ICE']

	########## QT
	# QTLIBPATH is a special var used in the qt4 module - has to be changed (ita)
	env['CPPPATH_QT']          = [ env['QTINCLUDEPATH']+'/Qt', env['QTINCLUDEPATH'] ] # TODO QTINCLUDEPATH (ita)
	env['LIBPATH_QT']          = env['LIBPATH_X11']+[env['QTLIBPATH']]
#    env['LIB_QT']              = ['QtGui4'+debug, 'pthread', 'Xext']+env['LIB_Z']+env['LIB_PNG']+env['LIB_X11']+env['LIB_SM']
	env['LIB_QT']              = ['QtGui'+debug, ]
	env['RPATH_QT']            = env['LIBPATH_X11']+[env['QTLIBPATH']]

	env['CXXFLAGS_QT3SUPPORT'] = ['-DQT3_SUPPORT']
	env['CPPPATH_QT3SUPPORT']  = [ env['QTINCLUDEPATH']+'/Qt3Support' ]
	env['LIB_QT3SUPPORT']      = ['Qt3Support'+debug]
	env['RPATH_QT3SUPPORT']    = env['RPATH_QT']

	env['CPPPATH_QTCORE']      = [ env['QTINCLUDEPATH']+'/QtCore' ]
	env['LIB_QTCORE']          = ['QtCore'+debug]
	env['RPATH_QTCORE']        = env['RPATH_QT']

	env['CPPPATH_QTASSISTANT'] = [ env['QTINCLUDEPATH']+'/QtAssistant' ]
	env['LIB_QTASSISTANT']     = ['QtAssistant'+debug]

	env['CPPPATH_QTDESIGNER']  = [ env['QTINCLUDEPATH']+'/QtDesigner' ]
	env['LIB_QTDESIGNER']      = ['QtDesigner'+debug]

	env['CPPPATH_QTNETWORK']   = [ env['QTINCLUDEPATH']+'/QtNetwork' ]
	env['LIB_QTNETWORK']       = ['QtNetwork'+debug]
	env['RPATH_QTNETWORK']     = env['RPATH_QT']

	env['CPPPATH_QTGUI']       = [ env['QTINCLUDEPATH']+'/QtGui' ]
	env['LIB_QTGUI']           = ['QtCore'+debug, 'QtGui'+debug]
	env['RPATH_QTGUI']         = env['RPATH_QT']

	env['CPPPATH_QTOPENGL']      = [ os.path.join(env['QTINCLUDEPATH'],'QtOpenGL') ]
	env['LIB_QTOPENGL']        = ['QtOpenGL'+debug,'opengl32']
	env['RPATH_QTOPENGL']      = env['RPATH_QT']

	env['CPPPATH_QTSQL']       = [ env['QTINCLUDEPATH']+'/QtSql' ]
	env['LIB_QTSQL']           = ['QtSql'+debug]
	env['RPATH_QTSQL']         = env['RPATH_QT']

	env['CPPPATH_QTXML']       = [ env['QTINCLUDEPATH']+'/QtXml' ]
	env['LIB_QTXML']           = ['QtXml'+debug]
	env['RPATH_QTXML']         = env['RPATH_QT']

	env['CPPPATH_QTEST']       = [ env['QTINCLUDEPATH']+'/QtTest' ]
	env['LIB_QTEST']           = ['QtTest'+debug]
	env['RPATH_QTEST']         = env['RPATH_QT']

	env['QTLOCALE']            = str(env['PREFIX'])+'/share/locale'

def detect(conf):
	if conf.env['WINDOWS']:
		detect_qt4_win32(conf)
	else:
		detect_qt4(conf)
	return 0

def set_options(opt):
	try:
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except:
		pass

	opt.add_option('--header-ext',
		type='string',
		default='',
		help='header extension for moc files',
		dest='qt_header_ext')

	for i in "qtdir qtincludes qtlibs qtbin".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

