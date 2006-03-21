#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, shutil, sys
import Action, Common, Object, Task, Params, Runner, Utils, Scan

def trace(msg):
	Params.trace(msg, 'KDE3')
def debug(msg):
	Params.debug(msg, 'KDE3')
def error(msg):
	Params.error(msg, 'KDE3')

def setup():
	pass

# kde moc file processing
moc_vardeps = ['MOC', 'MOC_FLAGS', 'MOC_ST']
Action.GenAction('moc', moc_vardeps)

# kde documentation
meinproc_vardeps = ['MEINPROC', 'MEINPROCFLAGS']
def meinproc_build(task):
	reldir = task.m_inputs[0].cd_to()
	com   = task.m_env['MEINPROC']
	flags = task.m_env['MEINPROCFLAGS']
	#srcname = task.m_inputs[0].m_name
	#bldname = task.m_outputs[0].m_name
	cmd = '%s %s --cache %s %s' % (com, flags, task.m_outputs[0].bldpath(), task.m_inputs[0].bldpath())
	return Runner.exec_command(cmd)
meinprocact = Action.GenAction('meinproc', meinproc_vardeps)
meinprocact.m_function_to_run = meinproc_build

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

	comp_h   = '%s -L %s -nounload -o %s %s' % (uic_command, qtplugins, h_path, ui_path)
	comp_c   = '%s -L %s -nounload -tr tr2i18n -impl %s %s >> %s' % (uic_command, qtplugins, h_path, ui_path, cpp_path)

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
uicact = Action.GenAction('uic', uic_vardeps)
uicact.m_function_to_run = uic_build

kidl_vardeps = ['DCOPIDL']
skelstub_vardeps = ['DCOPIDL2CPP']

def kidl_build(task):
	reldir = task.m_inputs[0].cd_to()
	#src = task.m_inputs[0].m_name
	src = task.m_inputs[0].bldpath()
	tgt = src[:len(src)-2]+'.kidl'
	cmd = '%s %s > %s || (rm -f %s ; false)' % (task.m_env['DCOPIDL'], src, os.path.join(reldir, tgt), os.path.join(reldir, tgt))
	return Runner.exec_command(cmd)
kidlact = Action.GenAction('kidl', kidl_vardeps)
kidlact.m_function_to_run = kidl_build

def skel_build(task):
	reldir = task.m_inputs[0].cd_to()
	#if Params.g_mode!='nocopy':
	src = task.m_inputs[0].m_name
	#else:
	#	mir_node = task.m_inputs[0]
	#	src_node = mir_node.

	cmd = 'cd %s && %s --c++-suffix cpp --no-signals --no-stub %s' % (reldir, task.m_env['DCOPIDL2CPP'], src)
	return Runner.exec_command(cmd)
skelact = Action.GenAction('skel', skelstub_vardeps)
skelact.m_function_to_run = skel_build

def stub_build(task):
	reldir = task.m_inputs[0].cd_to()
	src = task.m_inputs[0].m_name
	cmd = 'cd %s && %s --c++-suffix cpp --no-signals --no-skel %s' % (reldir, task.m_env['DCOPIDL2CPP'], src)
	return Runner.exec_command(cmd)
stubact = Action.GenAction('stub', skelstub_vardeps)
stubact.m_function_to_run = stub_build

# kconfig_compiler
kcfg_vardeps = ['KCONFIG_COMPILER']
def kcfg_build(task):
	com = task.m_env['KCONFIG_COMPILER']
	reldir = task.m_inputs[0].cd_to()
	kcfg1 = task.m_inputs[0].bldpath()
	kcfg2 = task.m_inputs[1].bldpath()
	cmd = '%s -d%s %s %s' % (com, reldir, kcfg1, kcfg2)
	return Runner.exec_command(cmd)
kcfgact = Action.GenAction('kcfg', kcfg_vardeps)
kcfgact.m_function_to_run = kcfg_build

# translations
po_vardeps = ['POCOM', 'PO_ST']
Action.GenAction('po', po_vardeps)
class kde_translations(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other', 'po')
		self.env = Params.g_default_env
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
		destfile = self.m_appname+'.gmo'

		destpath = self.env['KDE_LOCALE']
		destdir  = self.env['DESTDIR']

		if destdir:
			destpath = destdir+destpath

		for file in self.m_current_path.m_files:
			lang, ext = os.path.splitext(file.m_name)
			if ext != '.po': continue

			node = self.get_mirror_node( self.m_current_path, lang+'.gmo')

			dir = os.sep.join( [destpath, lang ] )
			f = os.sep.join( [destpath, lang, destfile] )

			try: os.stat(dir)
			except: os.makedirs(dir)

			print "* installing %s to %s" % (node.bldpath(), f)
			shutil.copy2(node.abspath(), f)
			#except: pass

# documentation
class kde_documentation(Object.genobj):
	def __init__(self, appname, lang):
		Object.genobj.__init__(self, 'other', 'meinproc')
		self.env        = Params.g_default_env
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

		destpath = self.env['KDE_DOC']
		destdir  = self.env['DESTDIR']

		if destdir: destpath = destdir+destpath
		destpath = os.path.join(destpath, self.m_appname+os.sep+self.m_lang)

		try: os.stat(destpath)
		except: os.makedirs(destpath)
		for task in self.m_docbooks:
			print "* installing %s to %s" % (task.m_outputs[0].bldpath(), destpath)
			shutil.copy2(task.m_outputs[0].abspath(), destpath)
		for doc in self.m_files:
			print "* installing %s to %s" % (doc.srcpath(), destpath)
			shutil.copy2(doc.srcpath(), destpath)

# kde3 objects
kdefiles = ['.cpp', '.ui', '.kcfgc', '.skel', '.stub']
class kdeobj(Common.cppobj):
	def __init__(self, type='program'):
		Common.cppobj.__init__(self, type)
		self.env = Params.g_default_env.copy()
		self.m_linktask = None
		self.m_latask = None

	def get_valid_types(self):
		return ['program', 'shlib', 'staticlib', 'module', 'convenience', 'other']

	def find_kde_sources_in_dirs(self, dirnames):
		lst=[]
		for name in dirnames.split():
			node = self.m_current_path.find_node( name.split(os.sep) )
			for file in node.m_files:
				(base, ext) = os.path.splitext(file.m_name)
				if ext in kdefiles:
					lst.append( file.relpath(self.m_current_path)[2:] )
		self.source = self.source+(" ".join(lst))

	def create_kcfg_task(self, kcfg, kcfgc, base):
		def get_node(a):
			return self.get_mirror_node( self.m_current_path, a)

		cppnode = get_node(base+'.cpp')

		# run with priority 2
		task = self.create_task('kcfg', self.env, 2)

		tree = Params.g_build.m_tree
		task.m_inputs = [ tree.get_mirror_node(kcfg), tree.get_mirror_node(kcfgc) ]
		task.m_outputs = [ cppnode, get_node(base+'.h') ]

		cpptask = self.create_cpp_task()
		cpptask.m_inputs  = [ cppnode ]
		cpptask.m_outputs = [ get_node(base+'.o') ]

		return cpptask

	def create_moc_task(self, base):
		task = self.create_task('moc', self.env)
		task.m_inputs  = self.file_in(base+'.h')
		task.m_outputs = self.file_in(base+'.moc')
		return task

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

		# for kde programs we need to know in advance the dependencies
		# so we will scan them right here
		trace("apply called for kdeobj")

		try: obj_ext = self.env['obj_ext'][0]
		except: obj_ext = '.os'

		# get the list of folders to use by the scanners
		# all our objects share the same include paths anyway
		tree = Params.g_build.m_tree
		dir_lst = { 'path_lst' : self._incpaths_lst }

		lst = self.source.split()
		cpptasks = []
		skel_or_stub = {}
		for filename in lst:

			node = self.m_current_path.find_node( filename.split(os.sep) )
			if not node: error("source not found "+filename)

			base, ext = os.path.splitext(filename)

			if ext == '.ui':
				node = self.m_current_path.find_node( filename.split(os.sep) )
				cpptasks.append( self.create_uic_task(base) )
				continue
			#elif ext == '.qrc':
			#	cpptasks.append( self.create_rcc_task(base) )
			#	continue
			elif ext == '.kcfgc':
				node = self.m_current_path.find_node( filename.split(os.sep) )
				if not node: error("kcfgfile not found")
				#print "kcfgc file found", filename
				if tree.needs_rescan(node):
					tree.rescan(node, Scan.kcfg_scanner, dir_lst)
				kcfg_node = tree.m_depends_on[node][0]
				cpptasks.append( self.create_kcfg_task(kcfg_node, node, base) )
				continue
			elif ext == '.skel' or ext == '.stub':
				if not base in skel_or_stub:
					kidltask = self.create_task('kidl', self.env, 2)
					kidltask.m_inputs  = self.file_in(base+'.h')
					kidltask.m_outputs = self.file_in(base+'.kidl')
					skel_or_stub[base] = kidltask

				# stub or skel ? (remove the dot '.stub' -> 'stub')
				type = ext[1:]

				# this is a cascading builder .h->.kidl->_stub.cpp->_stub.o->link
				# instead of saying "task.run_after(othertask)" we only give priority numbers on tasks

				# the skel or stub (dcopidl2cpp)
				task = self.create_task(type, self.env, 3)
				task.m_inputs  = skel_or_stub[base].m_outputs
				task.m_outputs = self.file_in(''.join([base,'_',type,'.cpp']))

				# compile the resulting file (g++)
				cpptask = self.create_cpp_task()
				cpptask.m_inputs  = task.m_outputs
				cpptask.m_outputs = self.file_in(''.join([base,'_',type,'.o']))

				cpptasks.append( cpptask )
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
		if self.m_type=='staticlib': linktask = self.create_task('arlink', self.env, 6)
		else:                        linktask = self.create_task('link', self.env, 6)
		cppoutputs = []
		for t in cpptasks: cppoutputs.append(t.m_outputs[0])
		linktask.m_inputs  = cppoutputs 
		linktask.m_outputs = self.file_in(self.get_target_name())

		self.m_linktask = linktask

		if self.m_type != 'program':
			latask           = self.create_task('fakelibtool', self.env, 7)
			latask.m_inputs  = linktask.m_outputs
			latask.m_outputs = self.file_in(self.get_target_name('.la'))
			self.m_latask    = latask

		# end posting constraints (apply)

	def install(self):
		if self.m_type == 'program':
			self.install_results( 'KDE_BIN', '', self.m_linktask )
		elif self.m_type == 'shlib':
			self.install_results( 'KDE_LIB', '', self.m_linktask )
			self.install_results( 'KDE_LIB', '', self.m_latask )
		elif self.m_type == 'module':
			self.install_results( 'KDE_MODULE', '', self.m_linktask )
			self.install_results( 'KDE_MODULE', '', self.m_latask )

def setup(env):
	Object.register('kde', kdeobj)

def detect_kde(conf):
	env = conf.env
	# Detect the qt and kde environment using kde-config mostly
	def getpath(varname):
		#if not env.has_key('ARGS'): return None
		#v=env['ARGS'].get(varname, None)
		#if v: v=os.path.abspath(v)
		#return v
		return None

	def getstr(varname):
		#if env.has_key('ARGS'): return env['ARGS'].get(varname, '')
		return ''

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
	print "Checking for kde-config           : ",
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
		env.Exit(1)
	if kdedir: env['KDEDIR']=kdedir
	else: env['KDEDIR'] = os.popen(kde_config+' -prefix').read().strip()

	print "Checking for kde version          : ",
	kde_version = os.popen(kde_config+" --version|grep KDE").read().strip().split()[1]
	if int(kde_version[0]) != 3 or int(kde_version[2]) < 2:
		p('RED', kde_version)
		p('RED',"Your kde version can be too old")
		p('RED',"Please make sure kde is at least 3.2")
	else:
		p('GREEN',kde_version)

	## Detect the qt library
	print "Checking for the qt library       : ",
	if not qtdir: qtdir = os.getenv("QTDIR")
	if qtdir:
		p('GREEN',"qt is in "+qtdir)
	else:
		try:
			tmplibdir = os.popen(kde_config+' --expandvars --install lib').read().strip()
			libkdeuiSO = env.join(tmplibdir, getSOfromLA(env.join(tmplibdir,'/libkdeui.la')) )
			m = re.search('(.*)/lib/libqt.*', os.popen('ldd ' + libkdeuiSO + ' | grep libqt').read().strip().split()[2])
		except: m=None
		if m:
			qtdir = m.group(1)
			p('YELLOW',"qt was found as "+m.group(1))
		else:
			p('RED','Qt was not found')
			p('RED','Please set QTDIR first (/usr/lib/qt3?) or try scons -h for more options')
			env.Exit(1)
	env['QTDIR'] = qtdir.strip()
	env['LIB_QT'] = 'qt-mt'

	## Find the necessary programs uic and moc
	print "Checking for uic                  : ",
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
				env.Exit(1)
	env['UIC'] = uic

	print "Checking for moc                  : ",
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
			env.Exit(1)
	env['MOC'] = moc

	## check for the qt and kde includes
	print "Checking for the Qt includes      : ",
	if qtincludes and os.path.isfile(qtincludes + "/qlayout.h"):
		# The user told where to look for and it looks valid
		p('GREEN',"ok "+qtincludes)
	else:
		if os.path.isfile(qtdir + "/include/qlayout.h"):
			# Automatic detection
			p('GREEN',"ok "+qtdir+"/include/")
			qtincludes = qtdir + "/include/"
		elif os.path.isfile("/usr/include/qt3/qlayout.h"):
			# Debian probably
			p('YELLOW','the qt headers were found in /usr/include/qt3/')
			qtincludes = "/usr/include/qt3"
		else:
			p('RED',"the qt headers were not found")
			env.Exit(1)

	print "Checking for the kde includes     : ",
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
			env.Exit(1)

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
		if not datadir: datadir=env.join(prefix,'share')
		if not libdir: libdir=env.join(execprefix, "lib"+libsuffix)

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


        #env.setValue('LIBPATH_KDECORE','/opt/kde3/lib')
        #env.setValue('CPPPATH_KDECORE','/opt/kde3/include')

	env['LIB_KDECORE']  = 'kdecore'
        env['LIB_KIO']      = 'kio'
        env['LIB_KMDI']     = 'kmdi'
        env['LIB_KPARTS']   = 'kparts'
        env['LIB_KDEPRINT'] = 'kdeprint'

	env['KCONFIG_COMPILER'] = 'kconfig_compiler'

	env['MEINPROC']         = 'meinproc'
	env['MEINPROCFLAGS']    = '--check'
	env['MEINPROC_ST']      = '--cache %s %s'

	env['POCOM']            = 'msgfmt'
	env['PO_ST']            = '%s -o %s'

	env['MOC_FLAGS']        = ''
	env['MOC_ST']           = '%s -o %s'

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

def detect(conf):
	conf.env['KDE_IS_FOUND'] = 0

	detect_kde(conf)

	conf.env['KDE_IS_FOUND'] = 1
	return 0


