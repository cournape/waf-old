#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, shutil
import Action, Common, Object, Task, Params, Runner, Scan

def trace(msg):
	Params.trace(msg, 'KDE')
def debug(msg):
	Params.debug(msg, 'KDE')
def error(msg):
	Params.error(msg, 'KDE')

## QT SUPPORT ##

moc_vardeps = ['MOC', 'MOC_FLAGS', 'MOC_ST']
uic_vardeps = ['UIC', 'UIC_FLAGS', 'UIC_ST']
rcc_vardeps = ['RCC', 'RCC_FLAGS', 'RCC_ST']
uic3_vardeps = ['UIC3', 'UIC3_FLAGS', 'UIC3_ST']

Action.GenAction('moc', moc_vardeps)
Action.GenAction('uic', uic_vardeps)
Action.GenAction('uic3', uic3_vardeps)

## for rcc it is a bit particular
def rccbuild(task):
	reldir = reldir = task.m_inputs[0].cd_to()
	name = task.m_inputs[0].m_name
	name = name[:len(name)-4]

	cmd = 'cd %s && %s -name %s %s -o %s' % (reldir, task.m_env['RCC'], name, task.m_inputs[0].m_name, task.m_outputs[0].m_name)
	return Runner.exec_command(cmd)

rccact = Action.GenAction('rcc', rcc_vardeps)
rccact.m_function_to_run = rccbuild

## KDE SUPPORT ##

# kde documentation
meinproc_vardeps = ['MEINPROC', 'MEINPROCFLAGS']
def meinproc_build(task):
	reldir = task.m_inputs[0].cd_to()
	com   = task.m_env['MEINPROC']
	flags = task.m_env['MEINPROCFLAGS']
	srcname = task.m_inputs[0].m_name
	bldname = task.m_outputs[0].m_name

	cmd = 'cd %s && %s %s --cache %s %s' % (reldir, com, flags, bldname, srcname)
	return Runner.exec_command(cmd)
meinprocact = Action.GenAction('meinproc', meinproc_vardeps)
meinprocact.m_function_to_run = meinproc_build

# kde .ui file processing
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

# kde builds
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
				task.m_inputs = [ self.get_mirror_node( self.m_current_path, base+'.po') ]
				task.m_outputs = [ self.get_mirror_node( self.m_current_path, base+'.gmo') ]

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

class kde_documentation(Object.genobj):
	def __init__(self, appname, lang):
		Object.genobj.__init__(self, 'other', 'meinproc')
		self.env = Params.g_default_env
		self.m_docs = ''
		self.m_appname = appname
		self.m_docbooks = []
		self.m_files = []
		self.m_lang = lang
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

				n1 = self.get_mirror_node( self.m_current_path, base+'.docbook')
				n2 = self.get_mirror_node( self.m_current_path, base+'.cache.bz2')

				task.m_inputs  = [n1]
				task.m_outputs = [n2]

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
	
kdefiles = ['.cpp', '.ui', '.kcfgc']

class kdeobj(Common.cppobj):
	def __init__(self, type='program'):
		Common.cppobj.__init__(self, type)
		self.env = Params.g_default_env.copy()
		self.m_linktask = None
		self.m_latask = None

	def find_kde_sources_in_dirs(self, dirnames):
		lst=[]
		for name in dirnames.split():
			node = self.m_current_path.find_node( name.split(os.sep) )
			for file in node.m_files:
				(base, ext) = os.path.splitext(file.m_name)
				if ext in kdefiles:
					lst.append( file.relpath(self.m_current_path)[2:] )
		self.source = " ".join(lst)

	def create_kcfg_task(self, kcfg, kcfgc, base):
		def get_node(a):
			return self.get_mirror_node( self.m_current_path, a)

		cppnode = get_node(base+'.cpp')

		# run with priority 2
		task = self.create_task('kcfg', self.env, 2)

		# the following line is quite silly (name lookups)
		task.m_inputs = [ get_node(kcfg.m_name), get_node(kcfgc.m_name) ]
		task.m_outputs = [ cppnode, get_node(base+'.h') ]

		cpptask = self.create_cpp_task()
		cpptask.m_inputs  = [ cppnode ]
		cpptask.m_outputs = [ get_node(base+'.o') ]

		return cpptask

	def create_moc_task(self, base):
		file_h = base+'.h'
		file_moc = base+'.moc'

		task = self.create_task('moc', self.env)
		task.m_inputs = [ self.get_mirror_node( self.m_current_path, file_h) ]
		task.m_outputs = [ self.get_mirror_node( self.m_current_path, file_moc) ]
		return task

	def create_rcc_task(self, base):
		file_rcc = base+'.qrc'
		file_cpp = base+'_rcc.cpp'
		file_o   = base+'.o'

		# run with highest priority
		rcctask = self.create_task('rcc', self.env, 2)
		rcctask.m_inputs  = [ self.get_mirror_node( self.m_current_path, file_rcc) ]
		rcctask.m_outputs = [ self.get_mirror_node( self.m_current_path, file_cpp) ]

		cpptask = self.create_cpp_task()
		cpptask.m_inputs  = [ self.get_mirror_node( self.m_current_path, file_cpp) ]
		cpptask.m_outputs = [ self.get_mirror_node( self.m_current_path, file_o) ]

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
		uictask.m_inputs  = [ get_node(base+'.ui') ]
		uictask.m_outputs = [ hnode, cppnode ]

		moctask = self.create_task('moc', self.env)
		moctask.m_inputs  = [ hnode ]
		moctask.m_outputs = [ get_node(base+'.moc') ]

		cpptask = self.create_cpp_task()
		cpptask.m_inputs  = [ cppnode ]
		cpptask.m_outputs = [ get_node(base+'.o') ]
		cpptask.m_run_after = [moctask]

		return cpptask

	def apply(self):
		self.apply_env_vars()
		self.apply_lib_vars()
		self.apply_obj_vars()

		self.apply_incpaths()

		# for kde programs we need to know in advance the dependencies
		# so we will scan them right here
		trace("apply called for kdeobj")

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
			elif ext == '.kcfgc':
				node = self.m_current_path.find_node( filename.split(os.sep) )
				if not node: error("kcfgfile not found")
				#print "kcfgc file found", filename
				if tree.needs_rescan(node):
					tree.rescan(node, Scan.kcfg_scanner, dir_lst)
				kcfg_node = tree.m_depends_on[node][0]
				cpptasks.append( self.create_kcfg_task(kcfg_node, node, base) )
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

			cpptask.m_inputs = [ self.get_mirror_node( self.m_current_path, filename) ]
			cpptask.m_outputs = [ self.get_mirror_node( self.m_current_path, base+'.o') ]
			cpptask.m_run_after = moctasks
			cpptasks.append(cpptask)

		# and after the cpp objects, the remaining is the link step - in a lower priority so it runs alone
		linktask = self.create_task('link', self.env, 6)
		cppoutputs = []
		for t in cpptasks: cppoutputs.append(t.m_outputs[0])
		linktask.m_inputs = cppoutputs 
		linktask.m_outputs = [ self.get_mirror_node( self.m_current_path, self.get_target_name()) ]

		self.m_linktask = linktask

		if self.m_type != 'program':	
			latask = self.create_task('fakelibtool', self.env, 7)
			latask.m_inputs = linktask.m_outputs
			latask.m_outputs = [ self.get_mirror_node( self.m_current_path, self.get_target_name('.la')) ]
			self.m_latask = latask

		# all done
	def install(self):
		if self.m_type == 'program':
			self.install_results( 'KDE_BIN', '', self.m_linktask )
		elif self.m_type == 'shlib':
			self.install_results( 'KDE_LIB', '', self.m_linktask )
			self.install_results( 'KDE_LIB', '', self.m_latask )
		elif self.m_type == 'module':
			self.install_results( 'KDE_MODULE', '', self.m_linktask )
			self.install_results( 'KDE_MODULE', '', self.m_latask )


