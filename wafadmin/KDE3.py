#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

# found is 1, not found is 0

import os, sys
import Utils, Params


def detect_kde(env):
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

def detect(env):
	env.setValue('KDE_IS_FOUND', 0)

	detect_kde(env)

	env.setValue('KDE_IS_FOUND', 1)
	return 0


