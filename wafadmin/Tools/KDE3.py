#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, sys
import ccroot, cpp
import Action, Common, Object, Task, Params, Runner, Utils, Scan
from Params import debug, error, trace, fatal

# kde .ui file processing
#uic_vardeps = ['UIC', 'UIC_FLAGS', 'UIC_ST']
uic_vardeps = ['UIC', 'QTPLUGINS']
def uic_build(task):
	# outputs : 1. hfile 2. cppfile

	base = task.m_outputs[1].m_name
	base = base[:len(base)-4]

	inc_kde  ='#include <klocale.h>\n#include <kdialog.h>\n'
	inc_moc  ='#include "%s.moc"\n' % base

	ui_path   = task.m_inputs[0].bldpath(task.m_env)
	h_path    = task.m_outputs[0].bldpath(task.m_env)
	cpp_path  = task.m_outputs[1].bldpath(task.m_env)

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
				task.set_inputs(file)
				task.set_outputs(file.change_ext('.gmo'))
				self.m_tasks.append(task)
			except: pass
	def install(self):
		destfilename = self.m_appname+'.mo'

		current = Params.g_build.m_curdirnode
		for file in self.m_current_path.m_files:
			lang, ext = os.path.splitext(file.m_name)
			if ext != '.po': continue

			node = self.m_current_path.find_node( (lang+'.gmo').split('/') )
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
			node = self.m_current_path.find_node( filename.split('/') )

			self.m_files.append(node)
			(base, ext) = os.path.splitext(filename)
			if ext == '.docbook':
				task = self.create_task('meinproc', self.env, 2)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.cache.bz2'))
				self.m_docbooks.append(task)
	def install(self):
		destpath = os.sep.join([self.m_lang, self.m_appname])

		current = Params.g_build.m_curdirnode
		lst = []
		for task in self.m_docbooks:
			lst.append(task.m_outputs[0].abspath(self.env))
		for doc in self.m_files:
			lst.append(doc.abspath(self.env))

		Common.install_files('KDE_DOC', destpath, lst, self.env)

def handler_ui(self, node, base=''):

	cppnode = node.change_ext('.cpp')
	hnode   = node.change_ext('.h')

	uictask = self.create_task('uic', self.env, 2)
	uictask.set_inputs(node)
	uictask.set_outputs([hnode, cppnode])

	moctask = self.create_task('moc', self.env)
	moctask.set_inputs(hnode)
	moctask.set_outputs(node.change_ext('.moc'))

	cpptask = self.create_task('cpp', self.env)
	cpptask.set_inputs(cppnode)
	cpptask.set_outputs(node.change_ext('.o'))
	cpptask.m_run_after = [moctask]

def handler_kcfgc(self, node, base=''):
	tree = Params.g_build
	if tree.needs_rescan(node, self.env):
		Scan.g_kcfg_scanner.do_scan(node, self.env, hashparams=self.dir_lst)

	if node in node.m_parent.m_files: variant = 0
	else: variant = env.variant()

	kcfg_node = tree.m_depends_on[variant][node][0]
	cppnode = node.change_ext('.cpp')

	# run with priority 2
	task = self.create_task('kcfg', nice=2)
	task.set_inputs([kcfg_node, node])
	task.set_outputs([cppnode, node.change_ext('.h')])

	cpptask = self.create_task('cpp', self.env)
	cpptask.set_inputs(cppnode)
	cpptask.set_outputs(node.change_ext('.o'))

def handler_skel_or_stub(obj, base, type):
	if not base in obj.skel_or_stub:
		kidltask = obj.create_task('kidl', obj.env, 2)
		kidltask.set_inputs(obj.file_in(base+'.h'))
		kidltask.set_outputs(obj.file_in(base+'.kidl'))
		obj.skel_or_stub[base] = kidltask

	# this is a cascading builder .h->.kidl->_stub.cpp->_stub.o->link
	# instead of saying "task.run_after(othertask)" we only give priority numbers on tasks

	# the skel or stub (dcopidl2cpp)
	task = obj.create_task(type, obj.env, 4)
	task.set_inputs(obj.skel_or_stub[base].m_outputs)
	task.set_outputs(obj.file_in(''.join([base,'_',type,'.cpp'])))

	# compile the resulting file (g++)
	cpptask = obj.create_task('cpp', obj.env)
	cpptask.set_inputs(task.m_outputs)
	cpptask.set_outputs(obj.file_in(''.join([base,'_',type,'.o'])))

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

	def apply(self):
		trace("apply called for kdeobj")
		if not self.m_type in self.get_valid_types(): fatal('Trying to build a kde file of unknown type')

		self.apply_type_vars()
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
			if not node:
				ext = filename[len(filename)-4:]
				if ext != 'skel' and ext != 'stub':
					fatal("cannot find "+filename+" in "+str(self.m_current_path))
			base, ext = os.path.splitext(filename)

			fun = self.get_hook(ext)
			if fun:
				fun(self, node, base=base)
				continue

			# scan for moc files to produce, create cpp tasks at the same time

			if tree.needs_rescan(node, self.env):
				Scan.g_c_scanner.do_scan(node, self.env, hashparams = self.dir_lst)

			moctasks=[]
			mocfiles=[]

			if node in node.m_parent.m_files: variant = 0
			else: variant = env.variant()

			try: tmp_lst = tree.m_raw_deps[variant][node]
			except: tmp_lst = []
			for d in tmp_lst:
				base2, ext2 = os.path.splitext(d)
				if not ext2 == '.moc': continue
				# paranoid check
				if d in mocfiles:
					error("paranoia owns")
					continue
				# process that base.moc only once
				mocfiles.append(d)

				task = self.create_task('moc', self.env)
				task.set_inputs(node.change_ext('.h'))
				task.set_outputs(node.change_ext('.moc'))
				moctasks.append(task)
			
			# use a cache ?
			for d in tree.m_depends_on[variant][node]:
				name = d.m_name
				if name[len(name)-4:]=='.moc':
					task = self.create_task('moc', self.env)
					task.set_inputs(d.change_ext('.h'))
					task.set_outputs(d)
					moctasks.append(task)
					break

			# create the task for the cpp file
			cpptask = self.create_task('cpp', self.env)

			cpptask.m_scanner = Scan.g_c_scanner
			cpptask.m_scanner_params = self.dir_lst

			cpptask.set_inputs(node)
			cpptask.set_outputs(node.change_ext(obj_ext))
			cpptask.m_run_after = moctasks

		# and after the cpp objects, the remaining is the link step - in a lower priority so it runs alone
		if self.m_type=='staticlib': linktask = self.create_task('cpp_link_static', self.env, ccroot.g_prio_link)
		else:                        linktask = self.create_task('cpp_link', self.env, ccroot.g_prio_link)
		cppoutputs = []
		for t in self.p_compiletasks: cppoutputs.append(t.m_outputs[0])
		linktask.set_inputs(cppoutputs)
		linktask.set_outputs(self.file_in(self.get_target_name()))

		self.m_linktask = linktask

		if self.m_type != 'program' and self.want_libtool:
			latask           = self.create_task('fakelibtool', self.env, 200)
			latask.set_inputs(linktask.m_outputs)
			latask.set_outputs(self.file_in(self.get_target_name('.la')))
			self.m_latask    = latask

		self.apply_lib_vars()
		self.apply_obj_vars()
		self.apply_objdeps()
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

	def exec_and_read(cmd):
		p = os.popen(cmd)
		ret = p.read().strip()
		p.close()
		return ret

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

	if (prefix=='/usr/local' or prefix=='/usr/local/') and not Params.g_options.usrlocal:
		prefix=''

	p=Params.pprint

	if libdir: libdir = libdir+libsuffix

	## Detect the kde libraries
	print "Checking for kde-config            :",
	str="which kde-config 2>/dev/null"
	if kdedir: str="which %s 2>/dev/null" % (kdedir+'/bin/kde-config')
	kde_config = exec_and_read(str)
	if len(kde_config):
		p('GREEN', 'kde-config was found as '+kde_config)
	else:
		if kdedir: p('RED','kde-config was NOT found in the folder given '+kdedir)
		else: p('RED','kde-config was NOT found in your PATH')
		print "Make sure kde is installed properly"
		print "(missing package kdebase-devel?)"
		sys.exit(1)
	if kdedir: env['KDEDIR']=kdedir
	else: env['KDEDIR'] = exec_and_read('%s -prefix' % kde_config)

	print "Checking for kde version           :",
	kde_version = exec_and_read('%s --version|grep KDE' % kde_config).split()[1]
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
			tmplibdir = exec_and_read('%s --expandvars --install lib' % kde_config)
			libkdeuiSO = os.path.join(tmplibdir, getSOfromLA(os.path.join(tmplibdir,'/libkdeui.la')) )
			m = re.search('(.*)/lib/libqt.*', exec_and_read('ldd %s | grep libqt' % libkdeuiSO).split()[2])
		except: m=None
		if m:
			qtdir = m.group(1)
			p('YELLOW',"Qt was found as "+m.group(1))
		else:
			p('RED','Qt was not found')
			p('RED','* Make sure libqt3-dev is installed')
			p('RED','* Set QTDIR (for example, "export QTDIR=/usr/lib/qt3")')
			p('RED','* Try "waf -h" for more options')
			sys.exit(1)
	env['QTDIR'] = qtdir.strip()
	env['LIB_QT'] = 'qt-mt'

	## Find the necessary programs uic and moc
	print "Checking for uic                   :",
	uic = qtdir + "/bin/uic"
	if os.path.isfile(uic):
		p('GREEN',"uic was found as "+uic)
	else:
		uic = exec_and_read("which uic 2>/dev/null")
		if len(uic):
			p('YELLOW',"uic was found as "+uic)
		else:
			uic = exec_and_read("which uic 2>/dev/null")
			if len(uic):
				p('YELLOW',"uic was found as "+uic)
			else:
				p('RED','The program uic was not found')
				p('RED','* Make sure libqt3-dev is installed')
				p('RED','* Set QTDIR or PATH appropriately')
				sys.exit(1)
	env['UIC'] = uic

	print "Checking for moc                   :",
	moc = qtdir + "/bin/moc"
	if os.path.isfile(moc):
		p('GREEN',"moc was found as "+moc)
	else:
		moc = exec_and_read("which moc 2>/dev/null")
		if len(moc):
			p('YELLOW',"moc was found as "+moc)
		elif os.path.isfile("/usr/share/qt3/bin/moc"):
			moc = "/usr/share/qt3/bin/moc"
			p('YELLOW',"moc was found as "+moc)
		else:
			p('RED','The program moc was not found')
			p('RED','* Make sure libqt3-dev is installed')
			p('RED','* Set QTDIR or PATH appropriately')
			sys.exit(1)
	env['MOC'] = moc

	## check for the qt and kde includes
	print "Checking for the Qt includes       :",
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
			p('YELLOW','the Qt headers were found in /usr/include/qt3/')
			qtincludes = "/usr/include/qt3"
		else:
			p('RED','The Qt headers were not found')
			p('RED','* Make sure libqt3-dev is installed')
			p('RED','* Set QTDIR or PATH appropriately')
			sys.exit(1)

	print "Checking for the kde includes      :",
	kdeprefix = exec_and_read('%s --prefix' % kde_config)
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
			p('RED',"* Make sure kdelibs-dev is installed")
			p('RED',"* Try 'waf -h' for more options")
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
			dir = exec_and_read('%s --install %s' % (kde_config, option))
			if var == 'KDE_DOC': dir = debian_fix(dir)
			env[var] = subst_vars(dir)

	else:
		env['PREFIX'] = exec_and_read('%s --expandvars --prefix' % kde_config)
		env['KDE_LIB'] = exec_and_read('%s --expandvars --install lib' % kde_config)
		for (var, option) in kdec_opts.items():
			dir = exec_and_read('%s --expandvars --install %s' % (kde_config, option))
			env[var] = dir

	env['QTPLUGINS']=exec_and_read('%s --expandvars --install qtplugins' % kde_config)

	## kde libs and includes
	env['CPPPATH_KDECORE']=kdeincludes
	if not kdelibs:
		kdelibs=exec_and_read('%s --expandvars --install lib' % kde_config)
	env['LIBPATH_KDECORE']=kdelibs

	## qt libs and includes
	env['CPPPATH_QT']=qtincludes
	if not qtlibs:
		qtlibs=qtdir+"/lib"+libsuffix
	env['LIBPATH_QT']=qtlibs

	# rpath settings
	try:
		if Params.g_options.want_rpath:
			env['RPATH_QT']=['-Wl,--rpath='+qtlibs]
			env['RPATH_KDECORE']=['-Wl,--rpath='+kdelibs]
	except:
		pass

	env['LIB_KDECORE']  = 'kdecore'
        env['LIB_KIO']      = 'kio'
        env['LIB_KMDI']     = 'kmdi'
        env['LIB_KPARTS']   = 'kparts'
        env['LIB_KDEPRINT'] = 'kdeprint'
	env['LIB_KDEGAMES'] = 'kdegames'

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
	Action.simple_action('meinproc', '${MEINPROC} ${MEINPROCFLAGS} --cache ${TGT} ${SRC}', color='BLUE')
	Action.simple_action('po', '${POCOM} ${SRC} ${PO_ST} ${TGT}', color='BLUE')
	Action.simple_action('kidl', '${DCOPIDL} ${SRC} > ${TGT} || (rm -f ${TGT} ; false)', color='BLUE')
	Action.simple_action('skel', 'cd ${SRC[0].bld_dir(env)} && ${DCOPIDL2CPP} --c++-suffix cpp ' \
		'--no-signals --no-stub ${SRC[0].m_name}', color='BLUE')
	Action.simple_action('stub', 'cd ${SRC[0].bld_dir(env)} && ${DCOPIDL2CPP} --c++-suffix cpp ' \
		'--no-signals --no-skel ${SRC[0].m_name}', color='BLUE')
	Action.simple_action('kcfg', '${KCONFIG_COMPILER} -d${SRC[0].bld_dir(env)} ' \
		'${SRC[0].bldpath(env)} ${SRC[1].bldpath(env)}', color='BLUE')
	Action.Action('uic', vars=uic_vardeps, func=uic_build, color='BLUE')

        Object.register('kde_translations', kde_translations)
        Object.register('kde_documentation', kde_documentation)
        Object.register('kde', kdeobj)

	Object.hook('kde', '.ui', handler_ui)
	Object.hook('kde', '.skel', handler_skel)
	Object.hook('kde', '.stub', handler_stub)
	Object.hook('kde', '.kcfgc', handler_kcfgc)


def detect(conf):
	conf.env['KDE_IS_FOUND'] = 0

	detect_kde(conf)

	conf.env['KDE_IS_FOUND'] = 1
	return 0

def set_options(opt):
	try:
		opt.add_option('--want-rpath', type='int', default=1, dest='want_rpath', help='set rpath to 1 or 0 [Default 1]')
	except:
		pass

	opt.add_option('--usrlocal',
		default=False,
		action='store_true',
		help='force prefix=/usr/local/',
		dest='usrlocal')
	for i in "execprefix datadir libdir kdedir kdeincludes kdelibs qtdir qtincludes qtlibs libsuffix".split():
		opt.add_option('--'+i, type='string', default='', dest=i)

