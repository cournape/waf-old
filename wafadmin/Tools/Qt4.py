#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, re, types, sys
import Action, Common, Utils, Params, Configure, Scan, Runner, Object
from Params import debug, error, trace, fatal

## QT SUPPORT ##
moc_vardeps = ['QT_MOC', 'MOC_FLAGS', 'MOC_ST']
uic_vardeps = ['QT_UIC', 'UIC_FLAGS', 'UIC_ST']
rcc_vardeps = ['QT_RCC', 'RCC_FLAGS']
uic3_vardeps = ['QT_UIC3', 'UIC3_FLAGS', 'UIC3_ST']

Action.GenAction('moc', moc_vardeps)
Action.GenAction('uic', uic_vardeps)

## for rcc it is a bit particular
def rccbuild(task):
	reldir = reldir = task.m_inputs[0].cd_to()
	name = task.m_inputs[0].m_name
	name = name[:len(name)-4]
	cmd = '%s -name %s %s -o %s' % (task.m_env['QT_RCC'], name, task.m_inputs[0].bldpath(), task.m_outputs[0].bldpath())
	return Runner.exec_command(cmd)

rccact = Action.GenAction('rcc', rcc_vardeps)
rccact.m_function_to_run = rccbuild

# qt .ui3 file processing
uic_vardeps = ['UIC3', 'QTPLUGINS']
def uic3_build(task):
	# outputs : 1. hfile 2. cppfile

	base = task.m_outputs[1].m_name
	base = base[:len(base)-4]

	inc_moc  ='#include "%s.moc"\n' % base

	ui_path   = task.m_inputs[0].bldpath()
	h_path    = task.m_outputs[0].bldpath()
	cpp_path  = task.m_outputs[1].bldpath()

	qtplugins   = task.m_env['QTPLUGINS']
	uic_command = task.m_env['UIC3']

	comp_h   = '%s -L %s -nounload -o %s %s' % (uic_command, qtplugins, h_path, ui_path)
	comp_c   = '%s -L %s -nounload -impl %s %s >> %s' % (uic_command, qtplugins, h_path, ui_path, cpp_path)

	ret = Runner.exec_command( comp_h )
	if ret: return ret

	dest = open( cpp_path, 'w' )
	dest.write(inc_kde)
	dest.close()

	ret = Runner.exec_command( comp_c )
	if ret: return ret

	dest = open( cpp_path, 'a' )
	dest.write(inc_moc)
	dest.close()

	return ret
uic3act = Action.GenAction('uic3', uic_vardeps)
uic3act.m_function_to_run = uic3_build



qt4files = ['.cpp', '.ui', '.rcc']
class qt4obj(Common.cppobj):
	def __init__(self, type='program'):
		Common.cppobj.__init__(self, type)
		self.env = Params.g_default_env.copy()
		self.m_linktask = None
		self.m_latask = None

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib']

	def find_sources_in_dirs(self, dirnames):
		lst=[]
		for name in dirnames.split():
			node = self.m_current_path.find_node( name.split(os.sep) )
			for file in node.m_files:
				(base, ext) = os.path.splitext(file.m_name)
				if ext in qt4files:
					lst.append( file.relpath(self.m_current_path)[2:] )
		self.source = " ".join(lst)

	def create_moc_task(self, base):
		file_h = base+'.h'
		file_moc = base+'.moc'

		task = self.create_task('moc', self.env)
		task.m_inputs = [ self.get_mirror_node( self.m_current_path, file_h) ]
		task.m_outputs = [ self.get_mirror_node( self.m_current_path, file_moc) ]
		return task

	def create_rcc_task(self, base):
		# run rcctask with one of the highest priority
		# TODO add the dependency on the files listed in .qrc
		rcctask = self.create_task('rcc', self.env, 2)
		rcctask.m_inputs  = self.file_in(base+'.qrc')
		rcctask.m_outputs = self.file_in(base+'_rc.cpp')

		cpptask = self.create_cpp_task()
		cpptask.m_inputs  = self.file_in(base+'_rc.cpp')
		cpptask.m_outputs = self.file_in(base+'.o')

		# not mandatory
		cpptask.m_run_after = [rcctask]
		return cpptask

	def create_cpp_task(self):
		return self.create_task('cpp', self.env)

	def create_uic_task(self, base):
		def get_node(a):
			return self.get_mirror_node( self.m_current_path, a)

		cppnode = get_node( base+'.cpp' )
		hnode   = get_node( base+'.h' )

		uictask = self.create_task('uic', self.env, 2)
		uictask.m_inputs    = self.file_in(base+'.ui')
		uictask.m_outputs   = [ hnode, cppnode ]

		moctask = self.create_task('moc', self.env)
		moctask.m_inputs    = [ hnode ]
		moctask.m_outputs   = self.file_in(base+'.moc')

		cpptask = self.create_cpp_task()
		cpptask.m_inputs    = [ cppnode ]
		cpptask.m_outputs   = self.file_in(base+'.o')
		cpptask.m_run_after = [moctask]

		return cpptask

	def apply(self):
		self.apply_type_vars()
		self.apply_lib_vars()
		self.apply_obj_vars()
		self.apply_incpaths()

		# for qt4 programs we need to know in advance the dependencies
		# so we will scan them right here
		trace("apply called for qt4obj")

		try: obj_ext = self.env['obj_ext'][0]
		except: obj_ext = '.os'

		# get the list of folders to use by the scanners
		# all our objects share the same include paths anyway
		tree = Params.g_build.m_tree
		dir_lst = { 'path_lst' : self._incpaths_lst }

		lst = self.source.split()
		cpptasks = []
		for filename in lst:

			node = self.m_current_path.find_node( filename.split(os.sep) )
			if not node: error("source not found "+filename)

			base, ext = os.path.splitext(filename)

			if ext == '.ui':
				node = self.m_current_path.find_node( filename.split(os.sep) )
				cpptasks.append( self.create_uic_task(base) )
				continue
			elif ext == '.qrc':
				cpptasks.append( self.create_rcc_task(base) )
				continue

			# scan for moc files to produce, create cpp tasks at the same time

			if tree.needs_rescan(node):
				tree.rescan(node, Scan.c_scanner, dir_lst)

			names = tree.get_raw_deps(node)

			moctasks=[]
			mocfiles=[]
			for d in names:
				base2, ext2 = os.path.splitext(d)
				if not ext2 == '.moc': continue
				# paranoid check
				if d in mocfiles:
					error("paranoia owns")
					continue
				# process that base.moc only once
				mocfiles.append(d)

				tmptask = self.create_moc_task(base)
				moctasks.append( tmptask )

			# create the task for the cpp file
			cpptask = self.create_cpp_task()

			cpptask.m_scanner = Scan.c_scanner
			cpptask.m_scanner_params = dir_lst

			cpptask.m_inputs    = self.file_in(filename)
			cpptask.m_outputs   = self.file_in(base+obj_ext)
			cpptask.m_run_after = moctasks
			cpptasks.append(cpptask)

		# and after the cpp objects, the remaining is the link step - in a lower priority so it runs alone
		linktask = self.create_task('cpp_link', self.env, 101)
		cppoutputs = []
		for t in cpptasks: cppoutputs.append(t.m_outputs[0])
		linktask.m_inputs  = cppoutputs 
		linktask.m_outputs = self.file_in(self.get_target_name())

		self.m_linktask = linktask

		if self.m_type != 'program':
			latask           = self.create_task('fakelibtool', self.env, 101)
			latask.m_inputs  = linktask.m_outputs
			latask.m_outputs = self.file_in(self.get_target_name('.la'))
			self.m_latask    = latask

		self.apply_libdeps()
		# end posting constraints (apply)

	def install(self):
		if self.m_type == 'program':
			self.install_results( 'PREFIX', 'bin', self.m_linktask )
		elif self.m_type == 'shlib':
			self.install_results( 'PREFIX', 'lib', self.m_linktask )
			self.install_results( 'PREFIX', 'lib', self.m_latask )

def setup(env):
	if not sys.platform == "win32":
		Params.g_colors['moc']='\033[94m'
		Params.g_colors['rcc']='\033[94m'
	Object.register('qt4', qt4obj)

def detect_qt4(conf):
	env = conf.env

	try: qtlibs     = Params.g_options.qtlib
	except:
		qtlibs=''
		pass

	try: qtincludes = Params.g_options.qtincludes
	except:
		qtincludes=''
		pass

	try: qtbin      = Params.g_options.qtbin
	except:
		qtbin=''
		pass

	p=Params.pprint

		# do our best to find the QTDIR (non-Debian systems)
	qtdir = os.getenv('QTDIR')

	# TODO what if there are only static Qt libraries ?
	if qtdir and Configure.find_file('lib/libqt-mt'+str(env['shlib_SUFFIX']), qtdir): qtdir=None
	if not qtdir:
		qtdir=Configure.find_path('include/', [ # lets find the qt include directory
				'/usr/local/Trolltech/Qt-4.2.0/',
				'/usr/local/Trolltech/Qt-4.1.3/',
				'/usr/local/Trolltech/Qt-4.1.2/',
				'/usr/local/Trolltech/Qt-4.1.1/',
				'/usr/local/Trolltech/Qt-4.1.0/',
				'/usr/local/Trolltech/Qt-4.0.3/', # one never knows
				'/usr/local/Trolltech/Qt-4.0.2/',
				'/usr/local/Trolltech/Qt-4.0.1/',
				'/usr/local/Trolltech/Qt-4.0.0/'])
		if qtdir: p('YELLOW', 'The qtdir was found as '+qtdir)
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
		if qtbin: lst = [qtbin]+lst
		#print qtbin
		#print lst
		for prog in progs:
			path=conf.checkProgram(prog, lst)
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
			p('YELLOW','the qt headers were found in /usr/include/qt4/')
			qtincludes = "/usr/include/qt4"
		elif os.path.isfile("/usr/include/QtGui/QFont"):
			# e.g. SUSE 10
			p('YELLOW','the qt headers were found in /usr/include/')
			qtincludes = "/usr/include"
		else:
			p('RED',"the qt headers were not found")
			sys.exit(1)


	#env['QTPLUGINS']=os.popen('kde-config --expandvars --install qtplugins').read().strip()

	## qt libs and includes
	env['QTINCLUDEPATH']=qtincludes
	if not qtlibs: qtlibs=qtdir+'/lib'
	env['QTLIBPATH']=qtlibs

        ########## X11
        env['LIB_X11']             = ['X11']
        env['LIBPATH_X11']         = ['/usr/X11R6/lib/']
        env['LIB_XRENDER']         = ['Xrender']

	# link against libqt_debug when appropriate
	if env['BKS_DEBUG']: debug='_debug'
	else:                debug=''

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
        env['LIB_QTOPENGL']        = ['QtOpenGL'+debug]
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
	
	print env['PREFIX']
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
	p=Params.pprint

		# do our best to find the QTDIR (non-Debian systems)
	qtdir = os.getenv('QTDIR')

	# TODO what if there are only static Qt libraries ?
	if qtdir and Configure.find_file('lib/libqt-mt'+str(env['shlib_SUFFIX']), qtdir): qtdir=None
	if not qtdir:
		qtdir=Configure.find_path('include/', [ # lets find the qt include directory
				'c:\\Programme\\Qt\\4.1.0',
				'c:\\Qt\\4.1.0',
				'f:\\Qt\\4.1.0'])
		if qtdir: p('YELLOW', 'The qtdir was found as '+qtdir)
		else:     p('YELLOW', 'There is no QTDIR set')
	else: env['QTDIR'] = qtdir.strip()

	# if we have the QTDIR, finding the qtlibs and qtincludes is easy
	if qtdir:
		if not qtlibs:     qtlibs     = os.path.join(qtdir, 'lib')
		if not qtincludes: qtincludes = os.path.join(qtdir, 'include')
		#os.putenv('PATH', os.path.join(qtdir , 'bin') + ":" + os.getenv("PATH")) # TODO ita 

	# Check for uic, uic-qt3, moc, rcc, ..
	def find_qt_bin(progs):
		# first use the qtdir
		path=''
		for prog in progs:
			path=conf.checkProgram(prog, [os.path.join(qtdir, 'bin')])
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
			p('YELLOW','the qt headers were found in /usr/include/qt4/')
			qtincludes = "/usr/include/qt4"
		elif os.path.isfile("/usr/include/QtGui/QFont"):
			# e.g. SUSE 10
			p('YELLOW','the qt headers were found in /usr/include/')
			qtincludes = "/usr/include"
		else:
			p('RED',"the qt headers were not found")
			sys.exit(1)


	#env['QTPLUGINS']=os.popen('kde-config --expandvars --install qtplugins').read().strip()

	## qt libs and includes
	env['QTINCLUDEPATH']=qtincludes
	if not qtlibs: qtlibs=qtdir+'/lib'
	env['QTLIBPATH']=qtlibs

        ########## X11
        env['LIB_X11']             = ['X11']
        env['LIBPATH_X11']         = ['/usr/X11R6/lib/']
        env['LIB_XRENDER']         = ['Xrender']

	# link against libqt_debug when appropriate
	if env['BKS_DEBUG']: debug='_debug'
	else:                debug='4'

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


