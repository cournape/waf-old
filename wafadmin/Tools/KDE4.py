#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys
import ccroot, cpp
import Action, Common, Object, Task, Params, Runner, Utils, Scan
from Params import debug, error, trace, fatal


set_globals('MOC_H', ['.hh', '.h'])
set_globals('UI_EXT', ['.ui'])
set_globals('SKEL_EXT', ['.skel'])
set_globals('STUB_EXT', ['.stub'])
set_globals('KCFGC_EXT', ['.kcfgc'])

# a helper function
def getSOfromLA(lafile):
	contents = open(lafile, 'r').read()
	match = re.search("^dlname='([^']*)'$", contents, re.M)
	if match: return match.group(1)
	return None

# kde .ui file processing
#uic_vardeps = ['UIC', 'UIC_FLAGS', 'UIC_ST']
uic_vardeps = ['UIC', 'QTPLUGINS']
def uic_build(task):
	# outputs : 1. hfile 2. cppfile

	base = task.m_outputs[1].m_name
	base = base[:len(base)-4]

	inc_kde  ='#include <klocale.h>\n#include <kdialog.h>\n'
	inc_moc  ='#include "%s.moc"\n' % base

	ui_path   = task.m_inputs[0].bldpath()
	h_path    = task.m_outputs[0].bldpath()
	cpp_path  = task.m_outputs[1].bldpath()

	qtplugins   = task.m_env['QTPLUGINS']
	uic_command = task.m_env['UIC']

	comp_h   = '%s -o %s %s' % (uic_command, h_path, ui_path)
	#comp_c   = '%s -tr tr2i18n -impl %s %s >> %s' % (uic_command, h_path, ui_path, cpp_path)

	ret = Runner.exec_command( comp_h )
	if ret: return ret

	dest = open( cpp_path, 'w' )
	dest.write(inc_kde)
	dest.close()

	#ret = Runner.exec_command( comp_c )
	#if ret: return ret

	#dest = open( cpp_path, 'a' )
	#dest.write(inc_moc)
	#dest.close()

	return ret


kidl_vardeps = ['DCOPIDL']
skelstub_vardeps = ['DCOPIDL2CPP']

# translations
class kde_translations(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other')
		self.m_tasks=[]
		self.m_appname = appname
	def apply(self):
		for file in self.m_current_path.m_files:
			try:
				base, ext = os.path.splitext(file.m_name)
				if ext != '.po': continue
				task = self.create_task('po', self.env, 2)
				task.m_inputs  = self.file_in(base+'.po')
				task.m_outputs = self.file_in(base+'.gmo')
				self.m_tasks.append(task)
			except: pass
	def install(self):
		destfilename = self.m_appname+'.mo'

		current = Params.g_build.m_curdirnode
		for file in self.m_current_path.m_files:
			lang, ext = os.path.splitext(file.m_name)
			if ext != '.po': continue

			node = self.get_mirror_node(self.m_current_path, lang+'.gmo')
			orig = node.relpath_gen(current)

			destfile = os.sep.join([lang, 'LC_MESSAGES', destfilename])
			Common.install_as('KDE_LOCALE', destfile, orig, self.env)

# documentation
class kde_documentation(Object.genobj):
	def __init__(self, appname, lang):
		Object.genobj.__init__(self, 'other')
		self.m_docs     = ''
		self.m_appname  = appname
		self.m_docbooks = []
		self.m_files    = []
		self.m_lang     = lang
	def add_docs(self, s):
		self.m_docs = s+" "+self.m_docs
	def apply(self):
		for filename in self.m_docs.split():
			if not filename: continue
			node = self.m_current_path.find_node( filename.split(os.sep) )
			self.m_files.append(node)
			(base, ext) = os.path.splitext(filename)
			if ext == '.docbook':
				task = self.create_task('meinproc', self.env, 2)
				task.m_inputs  = self.file_in(base+'.docbook')
				task.m_outputs = self.file_in(base+'.cache.bz2')
				self.m_docbooks.append(task)
	def install(self):
		destpath = os.sep.join([self.m_appname, self.m_lang])

		current = Params.g_build.m_curdirnode
		lst = []
		for task in self.m_docbooks:
			lst.append(task.m_outputs[0].relpath_gen(current))
		for doc in self.m_files:
			lst.append(doc.srcpath())

		Common.install_files('KDE_DOC', destpath, lst, self.env)

def handler_ui(self, node, base=''):
	cppnode = self.get_node( base+'.cpp' )
	hnode   = self.get_node( base+'.h' )

	uictask = self.create_task('uic', self.env, 2)
	uictask.m_inputs    = self.file_in(base+'.ui')
	uictask.m_outputs   = [ hnode, cppnode ]

	moctask = self.create_task('moc', self.env)
	moctask.m_inputs    = [ hnode ]
	moctask.m_outputs   = self.file_in(base+'.moc')

	cpptask = self.create_task('cpp', self.env)
	cpptask.m_inputs    = [ cppnode ]
	cpptask.m_outputs   = self.file_in(base+'.o')
	cpptask.m_run_after = [moctask]

def handler_kcfgc(self, node, base=''):
	tree = Params.g_build
	if tree.needs_rescan(node, self.env):
		tree.rescan(node, Scan.kcfg_scanner, self.dir_lst)
	kcfg_node = tree.m_depends_on[node][0]
	cppnode = self.get_node(base+'.cpp')

	# run with priority 2
	task = self.create_task('kcfg', self.env, 2)

	task.m_inputs = [ tree.get_mirror_node(kcfg_node), tree.get_mirror_node(node) ]
	task.m_outputs = [ cppnode, self.get_node(base+'.h') ]

	cpptask = self.create_task('cpp', self.env)
	cpptask.m_inputs  = [ cppnode ]
	cpptask.m_outputs = [ self.get_node(base+'.o') ]

def handler_skel_or_stub(obj, base, type):
	if not base in obj.skel_or_stub:
		kidltask = obj.create_task('kidl', obj.env, 2)
		kidltask.m_inputs  = obj.file_in(base+'.h')
		kidltask.m_outputs = obj.file_in(base+'.kidl')
		obj.skel_or_stub[base] = kidltask

	# this is a cascading builder .h->.kidl->_stub.cpp->_stub.o->link
	# instead of saying "task.run_after(othertask)" we only give priority numbers on tasks

	# the skel or stub (dcopidl2cpp)
	task = obj.create_task(type, obj.env, 4)
	task.m_inputs  = obj.skel_or_stub[base].m_outputs
	task.m_outputs = obj.file_in(''.join([base,'_',type,'.cpp']))

	# compile the resulting file (g++)
	cpptask = obj.create_task('cpp', obj.env)
	cpptask.m_inputs  = task.m_outputs
	cpptask.m_outputs = obj.file_in(''.join([base,'_',type,'.o']))

def handler_stub(self, node, base=''):
	handler_skel_or_stub(self, base, 'stub')

def handler_skel(self, node, base=''):
	handler_skel_or_stub(self, base, 'skel')

# kde3 objects
kdefiles = ['.cpp', '.ui', '.kcfgc', '.skel', '.stub']
class kdeobj(cpp.cppobj):
	def __init__(self, type='program'):
		cpp.cppobj.__init__(self, type)
		self.m_linktask = None
		self.m_latask   = None
		self.skel_or_stub = {}
		self.want_libtool = -1 # fake libtool here
		global kdefiles
		self.m_src_file_ext = kdefiles

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib', 'module', 'convenience', 'other']

	def get_node(self, a):
		return self.get_mirror_node(self.m_current_path, a)

	def apply(self):
		trace("apply called for kdeobj")
		if not self.m_type in self.get_valid_types(): fatal('Trying to build a kde file of unknown type')

		self.apply_type_vars()
		self.apply_lib_vars()
		self.apply_obj_vars()
		self.apply_incpaths()

		if self.want_libtool and self.want_libtool>0: self.apply_libtool()

		obj_ext = self.env[self.m_type+'_obj_ext'][0]

		# get the list of folders to use by the scanners
		# all our objects share the same include paths anyway
		tree = Params.g_build
		self.dir_lst = { 'path_lst' : self._incpaths_lst }

		lst = self.source.split()
		for filename in lst:

			node = self.m_current_path.find_node( filename.split(os.sep) )
			if not node: fatal("cannot find "+filename+" in "+str(self.m_current_path))
			base, ext = os.path.splitext(filename)

			fun = self.get_hook(ext)
			if fun:
				fun(self, node, base=base)
				continue


			# scan for moc files to produce, create cpp tasks at the same time
			if tree.needs_rescan(node, self.env):
				tree.rescan(node, Scan.c_scanner, self.dir_lst)

			moctasks=[]
			mocfiles=[]
			try: tmp_lst = tree.m_raw_deps[node]
			except: tmp_lst=[]
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
				if Params.g_options.kde_header_ext:
					ext = Params.g_options.kde_header_ext
				else:
					path = node.m_parent.srcpath(self.env) + os.sep
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
				task = self.create_task('moc', self.env)
				task.set_inputs(h_node)
				task.set_outputs(m_node)
				moctasks.append(task)

			# look at the file inputs, it is set right above
			for d in tree.m_depends_on[variant][node]:
				name = d.m_name
				if name[len(name)-4:]=='.moc':
					task = self.create_task('moc', self.env)
					task.set_inputs(tree.m_depends_on[variant][d])
					task.set_outputs(d)
					moctasks.append(task)
					break


			# create the task for the cpp file
			cpptask = self.create_task('cpp', self.env)

			cpptask.m_scanner = Scan.c_scanner
			cpptask.m_scanner_params = self.dir_lst

			cpptask.m_inputs    = self.file_in(filename)
			cpptask.m_outputs   = self.file_in(base+obj_ext)
			cpptask.m_run_after = moctasks

		# and after the cpp objects, the remaining is the link step - in a lower priority so it runs alone
		if self.m_type=='staticlib': linktask = self.create_task('cpp_link_static', self.env, ccroot.g_prio_link)
		else:                        linktask = self.create_task('cpp_link', self.env, ccroot.g_prio_link)
		cppoutputs = []
		for t in self.p_compiletasks: cppoutputs.append(t.m_outputs[0])
		linktask.m_inputs  = cppoutputs 
		linktask.m_outputs = self.file_in(self.get_target_name())

		self.m_linktask = linktask

		if self.m_type != 'program' and self.want_libtool:
			latask           = self.create_task('fakelibtool', self.env, 200)
			latask.m_inputs  = linktask.m_outputs
			latask.m_outputs = self.file_in(self.get_target_name('.la'))
			self.m_latask    = latask

		self.apply_libdeps()
		# end posting constraints (apply)

	def install(self):
		if self.m_type == 'module':
			self.install_results('KDE_MODULE', '', self.m_linktask)
			if self.want_libtool: self.install_results('KDE_MODULE', '', self.m_latask)
		else:
			ccroot.ccroot.install(self)

def detect_kde(conf):
	env = conf.env
	# Detect the qt and kde environment using kde-config mostly
	def getstr(varname):
		#if env.has_key('ARGS'): return env['ARGS'].get(varname, '')
		v=''
		try: v = getattr(Params.g_options, varname)
		except: return ''
		return v

	def getpath(varname):
		v = getstr(varname)
		#if not env.has_key('ARGS'): return None
		#v=env['ARGS'].get(varname, None)
		if v: v=os.path.abspath(v)
		return v

	prefix      = getpath('prefix')
	execprefix  = getpath('execprefix')
	datadir     = getpath('datadir')
	libdir      = getpath('libdir')

	kdedir      = getstr('kdedir')
	kdeincludes = getpath('kdeincludes')
	kdelibs     = getpath('kdelibs')

	qtdir       = getstr('qtdir')
	qtincludes  = getpath('qtincludes')
	qtlibs      = getpath('qtlibs')
	libsuffix   = getstr('libsuffix')

	p=Params.pprint

	if libdir: libdir = libdir+libsuffix

	## Detect the kde libraries
	print "Checking for kde-config            :",
	str="which kde-config 2>/dev/null"
	if kdedir: str="which %s 2>/dev/null" % (kdedir+'/bin/kde-config')
	kde_config = os.popen(str).read().strip()
	if len(kde_config):
		p('GREEN', 'kde-config was found as '+kde_config)
	else:
		if kdedir: p('RED','kde-config was NOT found in the folder given '+kdedir)
		else: p('RED','kde-config was NOT found in your PATH')
		print "Make sure kde is installed properly"
		print "(missing package kdebase-devel?)"
		sys.exit(1)
	if kdedir: env['KDEDIR']=kdedir
	else: env['KDEDIR'] = os.popen(kde_config+' -prefix').read().strip()

	print "Checking for kde version           :",
	kde_version = os.popen(kde_config+" --version|grep KDE").read().strip().split()[1]
	if int(kde_version[0]) != 3 or int(kde_version[2]) < 2:
		p('RED', kde_version)
		p('RED',"Your kde version can be too old")
		p('RED',"Please make sure kde is at least 3.2")
	else:
		p('GREEN',kde_version)

	## Detect the Qt library
	print "Checking for the Qt library        :",
	if not qtdir: qtdir = os.getenv("QTDIR")
	if qtdir:
		p('GREEN',"Qt is in "+qtdir)
	else:
		try:
			tmplibdir = os.popen(kde_config+' --expandvars --install lib').read().strip()
			libkdeuiSO = os.path.join(tmplibdir, getSOfromLA(os.path.join(tmplibdir,'/libkdeui.la')) )
			m = re.search('(.*)/lib/libqt.*', os.popen('ldd ' + libkdeuiSO + ' | grep libqt').read().strip().split()[2])
		except: m=None
		if m:
			qtdir = m.group(1)
			p('YELLOW',"Qt was found as "+m.group(1))
		else:
			p('RED','Qt was not found')
			p('RED','Please set QTDIR first (/usr/lib/qt3?) or try waf -h for more options')
			sys.exit(1)
	env['QTDIR'] = qtdir.strip()

	## Find the necessary programs uic and moc
	print "Checking for uic                   :",
	uic = qtdir + "/bin/uic"
	if os.path.isfile(uic):
		p('GREEN',"uic was found as "+uic)
	else:
		uic = os.popen("which uic 2>/dev/null").read().strip()
		if len(uic):
			p('YELLOW',"uic was found as "+uic)
		else:
			uic = os.popen("which uic 2>/dev/null").read().strip()
			if len(uic):
				p('YELLOW',"uic was found as "+uic)
			else:
				p('RED',"uic was not found - set QTDIR put it in your PATH ?")
				sys.exit(1)
	env['UIC'] = uic

	print "Checking for moc                   :",
	moc = qtdir + "/bin/moc"
	if os.path.isfile(moc):
		p('GREEN',"moc was found as "+moc)
	else:
		moc = os.popen("which moc 2>/dev/null").read().strip()
		if len(moc):
			p('YELLOW',"moc was found as "+moc)
		elif os.path.isfile("/usr/share/qt3/bin/moc"):
			moc = "/usr/share/qt3/bin/moc"
			p('YELLOW',"moc was found as "+moc)
		else:
			p('RED',"moc was not found - set QTDIR or put it in your PATH ?")
			sys.exit(1)
	env['MOC'] = moc

	## check for the qt and kde includes
	print "Checking for the Qt includes       :",
	if qtincludes and os.path.isfile(qtincludes + "/qlayout.h"):
		# The user told where to look for and it looks valid
		p('GREEN',"ok "+qtincludes)
	else:
		if os.path.isfile(qtdir + "/include/Qt/qlayout.h"):
			# Automatic detection
			p('GREEN',"ok "+qtdir+"/include/")
			qtincludes = qtdir + "/include"
		elif os.path.isfile("/usr/include/qt3/qlayout.h"):
			# Debian probably
			p('YELLOW','the Qt headers were found in /usr/include/qt3/')
			qtincludes = "/usr/include/qt3"
		else:
			p('RED',"the Qt headers were not found")
			sys.exit(1)

	print "Checking for the kde includes      :",
	kdeprefix = os.popen(kde_config+" --prefix").read().strip()
	if not kdeincludes:
		kdeincludes = kdeprefix+"/include/"
	if os.path.isfile(kdeincludes + "/klineedit.h"):
		p('GREEN',"ok "+kdeincludes)
	else:
		if os.path.isfile(kdeprefix+"/include/kde/klineedit.h"):
			# Debian, Fedora probably
			p('YELLOW',"the kde headers were found in %s/include/kde/"%kdeprefix)
			kdeincludes = kdeprefix + "/include/kde/"
		else:
			p('RED',"The kde includes were NOT found")
			sys.exit(1)

	# kde-config options
	kdec_opts = {'KDE_BIN'    : 'exe',     'KDE_APPS'      : 'apps',
		     'KDE_DATA'   : 'data',    'KDE_ICONS'     : 'icon',
		     'KDE_MODULE' : 'module',  'KDE_LOCALE'    : 'locale',
		     'KDE_KCFG'   : 'kcfg',    'KDE_DOC'       : 'html',
		     'KDE_MENU'   : 'apps',    'KDE_XDG'       : 'xdgdata-apps',
		     'KDE_MIME'   : 'mime',    'KDE_XDGDIR'    : 'xdgdata-dirs',
		     'KDE_SERV'   : 'services','KDE_SERVTYPES' : 'servicetypes',
		     'CPPPATH_KDECORE': 'include' }

	if prefix:
		## use the user-specified prefix
		if not execprefix: execprefix=prefix
		if not datadir: datadir=os.path.join(prefix,'share')
		if not libdir: libdir=os.path.join(execprefix, "lib"+libsuffix)

		subst_vars = lambda x: x.replace('${exec_prefix}', execprefix)\
				.replace('${datadir}', datadir)\
				.replace('${libdir}', libdir)\
				.replace('${prefix}', prefix)
		debian_fix = lambda x: x.replace('/usr/share', '${datadir}')
		env['PREFIX'] = prefix
		env['KDE_LIB'] = libdir
		for (var, option) in kdec_opts.items():
			dir = os.popen(kde_config+' --install ' + option).read().strip()
			if var == 'KDE_DOC': dir = debian_fix(dir)
			env[var] = subst_vars(dir)

	else:
		env['PREFIX'] = os.popen(kde_config+' --expandvars --prefix').read().strip()
		env['KDE_LIB'] = os.popen(kde_config+' --expandvars --install lib').read().strip()
		for (var, option) in kdec_opts.items():
			dir = os.popen(kde_config+' --expandvars --install ' + option).read().strip()
			env[var] = dir

	env['QTPLUGINS']=os.popen(kde_config+' --expandvars --install qtplugins').read().strip()

	## kde libs and includes
	env['CPPPATH_KDECORE']=kdeincludes
	if not kdelibs:
		kdelibs=os.popen(kde_config+' --expandvars --install lib').read().strip()
	env['LIBPATH_KDECORE']=kdelibs

	## qt libs and includes
	env['CPPPATH_QT']=qtincludes
	if not qtlibs:
		qtlibs=qtdir+"/lib"+libsuffix
	env['LIBPATH_QT']=qtlibs

	# link against libqt_debug when appropriate
	if env['BKS_DEBUG']: debug='_debug'
	else:                debug=''

        ########## QT
        # QTLIBPATH is a special var used in the qt4 module - has to be changed (ita)
	env['LIB_QT']              = ['QtGui'+debug, ]
        env['CXXFLAGS_QT3SUPPORT'] = ['-DQT3_SUPPORT']
	env['CPPPATH_QT3SUPPORT']  = [ qtincludes+'/Qt3Support' ]
        env['LIB_QT3SUPPORT']      = ['Qt3Support'+debug]

	env['CPPPATH_QTCORE']      = [ qtincludes+'/QtCore' ]
        env['LIB_QTCORE']          = ['QtCore'+debug]

	env['CPPPATH_QTASSISTANT'] = [ qtincludes+'/QtAssistant' ]
	env['LIB_QTASSISTANT']     = ['QtAssistant'+debug]

	env['CPPPATH_QTDESIGNER']  = [ qtincludes+'/QtDesigner' ]
        env['LIB_QTDESIGNER']      = ['QtDesigner'+debug]

	env['CPPPATH_QTNETWORK']   = [ qtincludes+'/QtNetwork' ]
        env['LIB_QTNETWORK']       = ['QtNetwork'+debug]

	env['CPPPATH_QTGUI']       = [ qtincludes+'/QtGui' ]
        env['LIB_QTGUI']           = ['QtCore'+debug, 'QtGui'+debug]

	env['CPPPATH_QTOPENGL']      = [ os.path.join(qtincludes,'QtOpenGL') ]
        env['LIB_QTOPENGL']        = ['QtOpenGL'+debug]

	env['CPPPATH_QTSQL']       = [ qtincludes+'/QtSql' ]
        env['LIB_QTSQL']           = ['QtSql'+debug]

	env['CPPPATH_QTXML']       = [ qtincludes+'/QtXml' ]
        env['LIB_QTXML']           = ['QtXml'+debug]

	env['CPPPATH_QTEST']       = [ qtincludes+'/QtTest' ]
        env['LIB_QTEST']           = ['QtTest'+debug]


	# rpath settings
	try:
		if Params.g_options.want_rpath:
			env['RPATH_QT']=['-Wl,--rpath='+qtlibs]
			env['RPATH_KDECORE']=['-Wl,--rpath='+kdelibs]
	except:
		pass

	env['LIB_KDECORE']  = 'kdecore'
        env['LIB_KIO']      = 'kio'
        env['LIB_KPARTS']   = 'kparts'
        env['LIB_KDEPRINT'] = 'kdeprint'
        env['LIB_KDEGAMES'] = 'kdegames'
      
        env['LIB_KDEUI'] = 'kdeui'
        env['LIB_KDE3SUPPORT'] = 'kde3support'
        env['LIB_KHTML'] = 'khtml'
        env['LIB_KJS'] = 'kjs'
        env['LIB_KWALLETCLIENT'] = 'kwalletclient'
        env['LIB_KDESU'] = 'kdesu'
        env['LIB_DCOP'] = 'dcop'
        env['LIB_KDEFX'] = 'kdefx'


	env['KCONFIG_COMPILER'] = 'kconfig_compiler'

	env['MEINPROC']         = 'meinproc'
	env['MEINPROCFLAGS']    = '--check'
	env['MEINPROC_ST']      = '--cache %s %s'
	
	env['POCOM']            = 'msgfmt'
	env['PO_ST']            = '-o'

	env['MOC_FLAGS']        = ''
	env['MOC_ST']           = '-o'

	env['DCOPIDL']          = 'dcopidl'
	env['DCOPIDL2CPP']      = 'dcopidl2cpp'

	env['module_CXXFLAGS']  = ['-fPIC', '-DPIC']
	env['module_LINKFLAGS'] = ['-shared']
	env['module_obj_ext']   = ['.os']
	env['module_PREFIX']    = 'lib'
	env['module_SUFFIX']    = '.so'

	try: env['module_CXXFLAGS']=env['shlib_CXXFLAGS']
	except: pass

	try: env['module_LINKFLAGS']=env['shlib_LINKFLAGS']
	except: pass

def setup(env):
	Action.simple_action('moc', '${MOC} ${MOC_FLAGS} ${SRC} ${MOC_ST} ${TGT}', color='BLUE')
	Action.simple_action('po', '${POCOM} ${SRC} ${PO_ST} ${TGT}', color='BLUE')
	Action.simple_action('meinproc', '${MEINPROC} ${MEINPROCFLAGS} --cache ${TGT} ${SRC}', color='BLUE')
	Action.simple_action('kidl', '${DCOPIDL} ${SRC} > ${TGT} || (rm -f ${TGT} ; false)', color='BLUE')
	Action.simple_action('skel', 'cd ${SRC[0].bld_dir(env)} && ${DCOPIDL2CPP} --c++-suffix ' \
		'cpp --no-signals --no-stub ${SRC[0].m_name}', color='BLUE')
	Action.simple_action('stub', 'cd ${SRC[0].bld_dir(env)} && ${DCOPIDL2CPP} --c++-suffix ' \
		'cpp --no-signals --no-skel ${SRC[0].m_name}', color='BLUE')
	Action.simple_action('kcfg', '${KCONFIG_COMPILER} -d${SRC[0].bld_dir(env)} ' \
		'${SRC[0].bldpath(env)} ${SRC[1].bldpath(env)}', color='BLUE')

	Action.Action('uic', vars=uic_vardeps, func=uic_build, color='BLUE')

        Object.register('kde_translations', kde_translations)
        Object.register('kde_documentation', kde_documentation)
        Object.register('kde', kdeobj)
        Object.register('kdeinit', kdeinitobj)

	Object.hook('kde', 'UI_EXT', handler_ui)
	Object.hook('kde', 'SKEL_EXT', handler_skel)
	Object.hook('kde', 'STUB_EXT', handler_stub)
	Object.hook('kde', 'KCFGC_EXT', handler_kcfgc)

def detect(conf):
	conf.env['KDE_IS_FOUND'] = 0

	detect_kde(conf)

	conf.env['KDE_IS_FOUND'] = 1
	return 0



class kdeinitobj(kdeobj):
	def __init__(self, senv=None):
		if not self.env: self.env = env
		kdeobj.__init__(self, 'shlib', senv)

		if env['WINDOWS']:
			self.type = 'program'
		else:
			self.binary = kdeobj('program', senv)
			self.binary.libprefix = ''
			self.kdeinitlib = kdeobj('shlib', senv)
			self.kdeinitlib.libprefix = ''

	def execute(self):
		if self.executed: return

		if env['WINDOWS']:
			SConsEnvironment.kdeobj.execute(self)
			return

		# 'dcopserver' is the real one
		self.binary.target   = self.target
		# 'libkdeinit_dcopserver'
		self.kdeinitlib.target = 'libkdeinit_' + self.target
		# 'dcopserver' (lib)

		self.kdeinitlib.libs     = self.libs
		self.kdeinitlib.libpaths = self.libpaths
		self.kdeinitlib.uselib   = self.uselib
		self.kdeinitlib.source   = self.source
		self.kdeinitlib.includes = self.includes
		self.kdeinitlib.execute()

		self.binary.uselib       = self.uselib
		self.binary.libs         = [self.kdeinitlib.target + ".la"] + self.orenv.make_list(self.libs)
		#self.binary.libdirs      = "build/dcop"
		self.binary.libpaths     = self.libpaths
		self.binary.includes     = self.includes
		env.Depends(self.binary.target, self.kdeinitlib.target + ".la")

		self.type = 'module'
		self.libs = [self.kdeinitlib.target + ".la"] + self.orenv.make_list(self.libs)

		myname=None
		myext=None
		for source in self.kdeinitlib.source:
			sext=SCons.Util.splitext(source)
			if sext[0] == self.target or not myname:
				myname = sext[0]
				myext  = sext[1]

		def create_kdeinit_cpp(target, source, env):
			# Creates the dummy kdemain file for the binary
			dest=open(target[0].path, 'w')
			dest.write('extern \"C\" int kdemain(int, char* []);\n')
			dest.write('int main( int argc, char* argv[] ) { return kdemain(argc, argv); }\n')
			dest.close()
		env['BUILDERS']['KdeinitCpp'] = env.Builder(action=env.Action(create_kdeinit_cpp),
					prefix='kdeinit_', suffix='.cpp',
					src_suffix=myext)
		env.KdeinitCpp(myname)
		self.binary.source = "./kdeinit_" + myname + '.cpp'
		self.binary.execute()

		def create_kdeinit_la_cpp(target, source, env):
			""" Creates the dummy kdemain file for the module"""
			dest=open(target[0].path, 'w')
			dest.write('#include <kdemacros.h>\n')
			dest.write('extern \"C\" int kdemain(int, char* []);\n')
			dest.write('extern \"C\" KDE_EXPORT int kdeinitmain( int argc, char* argv[] ) { return kdemain(argc, argv); }\n')
			dest.close()
		env['BUILDERS']['KdeinitLaCpp'] = env.Builder(action=env.Action(create_kdeinit_la_cpp),
			  prefix='kdeinit_', suffix='.la.cpp',
			  src_suffix=myext)
		env.KdeinitLaCpp(myname)
		self.source = 'kdeinit_' + self.target + '.la.cpp'

		kdeobj.execute(self)

