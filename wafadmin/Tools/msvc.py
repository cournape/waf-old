#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2006 (dv)
# Visual C support - beta, needs more testing

import os, sys
import re, os.path, string
import optparse
import Utils, Action, Params, Object, Runner
from Params import debug, error, fatal, warning

import ccroot
from ccroot import read_la_file
from os.path import exists

def msvc_linker(task):
	"""special linker for MSVC with support for embedding manifests into DLL's
	and executables compiled by Visual Studio 2005 or probably later. Without
	the accompaniing manifest file, these binaries are unusable.  see:
	http://msdn2.microsoft.com/en-us/library/ms235542(VS.80).aspx Problems with
	this tool: It's allways called whether MSVC creates manifests or not..."""
	e=task.m_env
	linker=e['LINK_CXX']
	srcf=e['CPPLNK_SRC_F']
	trgtf=e['CPPLNK_TGT_F']
	if not linker:
		linker=e['LINK_CC']
		srcf=e['CCLNK_SRC_F']
		trgtf=e['CCLNK_TGT_F']
	linkflags=e.get_flat('LINKFLAGS')
	libdirs=e.get_flat('_LIBDIRFLAGS')
	libs=e.get_flat('_LIBFLAGS')

	outfile=task.m_outputs[0].bldpath(e)
	manifest=outfile+'.manifest'

	objs=" ".join(map(lambda a: "\""+a.abspath(e)+"\"", task.m_inputs))

	cmd="%s %s%s %s%s %s %s %s" % (linker,srcf,objs,trgtf,outfile, linkflags, libdirs,libs)
	ret=Runner.exec_command(cmd)
	if ret: return ret
	if os.path.exists(manifest):
		debug('manifesttool', 'msvc')
		mtool=task.m_env['MT']
		if not mtool:
			return 0
		mode=''
		# embedding mode. Different for EXE's and DLL's.
		# see: http://msdn2.microsoft.com/en-us/library/ms235591(VS.80).aspx
		if task.m_type == 'program':
			mode='1'
		elif task.m_type == 'shlib':
			mode='2'

		debug('embedding manifest','msvcobj')
		flags=task.m_env['MTFLAGS']
		if flags:
			flags=string.join(flags,' ')
		else:
			flags=''

		cmd='"%s" %s -manifest "%s" -outputresource:"%s";#%s' % (mtool, flags,
			manifest, outfile, mode)
		ret=Runner.exec_command(cmd)
	return ret

g_msvc_type_vars=['CCFLAGS', 'CXXFLAGS', 'LINKFLAGS', 'obj_ext']

# importlibs provided by MSVC/Platform SDK. Do NOT search them....
g_msvc_systemlibs={ 'aclui': 1, 'activeds': 1, 'ad1': 1, 'adptif': 1,
'adsiid': 1, 'advapi32': 1, 'asycfilt': 1, 'authz': 1, 'bhsupp': 1, 'bits':
1, 'bufferoverflowu': 1, 'cabinet': 1, 'cap': 1, 'certadm': 1, 'certidl': 1,
'ciuuid': 1, 'clusapi': 1, 'comctl32': 1, 'comdlg32': 1, 'comsupp': 1,
'comsuppd': 1, 'comsuppw': 1, 'comsuppwd': 1, 'comsvcs': 1, 'credui': 1,
'crypt32': 1, 'cryptnet': 1, 'cryptui': 1, 'd3d8thk': 1, 'daouuid': 1,
'dbgeng': 1, 'dbghelp': 1, 'dciman32': 1, 'ddao35': 1, 'ddao35d': 1,
'ddao35u': 1, 'ddao35ud': 1, 'delayimp': 1, 'dhcpcsvc': 1, 'dhcpsapi': 1,
'dlcapi': 1, 'dnsapi': 1, 'dsprop': 1, 'dsuiext': 1, 'dtchelp': 1,
'faultrep': 1, 'fcachdll': 1, 'fci': 1, 'fdi': 1, 'framedyd': 1, 'framedyn':
1, 'gdi32': 1, 'gdiplus': 1, 'glaux': 1, 'glu32': 1, 'gpedit': 1, 'gpmuuid':
1, 'gtrts32w': 1, 'gtrtst32': 1, 'hlink': 1, 'htmlhelp': 1, 'httpapi': 1,
'icm32': 1, 'icmui': 1, 'imagehlp': 1, 'imm32': 1, 'iphlpapi': 1, 'iprop': 1,
'kernel32': 1, 'ksguid': 1, 'ksproxy': 1, 'ksuser': 1, 'libcmt': 1,
'libcmtd': 1, 'libcpmt': 1, 'libcpmtd': 1, 'loadperf': 1, 'lz32': 1, 'mapi':
1, 'mapi32': 1, 'mgmtapi': 1, 'minidump': 1, 'mmc': 1, 'mobsync': 1, 'mpr':
1, 'mprapi': 1, 'mqoa': 1, 'mqrt': 1, 'msacm32': 1, 'mscms': 1, 'mscoree': 1,
'msdasc': 1, 'msimg32': 1, 'msrating': 1, 'mstask': 1, 'msvcmrt': 1,
'msvcmrtd': 1, 'msvcprt': 1, 'msvcprtd': 1, 'msvcrt': 1, 'msvcrtd': 1,
'msvcurt': 1, 'msvcurtd': 1, 'mswsock': 1, 'msxml2': 1, 'mtx': 1, 'mtxdm': 1,
'netapi32': 1, 'nmapi': 1, 'nmsupp': 1, 'npptools': 1, 'ntdsapi': 1,
'ntdsbcli': 1, 'ntmsapi': 1, 'ntquery': 1, 'odbc32': 1, 'odbcbcp': 1,
'odbccp32': 1, 'oldnames': 1, 'ole32': 1, 'oleacc': 1, 'oleaut32': 1,
'oledb': 1, 'oledlg': 1, 'olepro32': 1, 'opends60': 1, 'opengl32': 1,
'osptk': 1, 'parser': 1, 'pdh': 1, 'penter': 1, 'pgobootrun': 1, 'pgort': 1,
'powrprof': 1, 'psapi': 1, 'ptrustm': 1, 'ptrustmd': 1, 'ptrustu': 1,
'ptrustud': 1, 'qosname': 1, 'rasapi32': 1, 'rasdlg': 1, 'rassapi': 1,
'resutils': 1, 'riched20': 1, 'rpcndr': 1, 'rpcns4': 1, 'rpcrt4': 1, 'rtm':
1, 'rtutils': 1, 'runtmchk': 1, 'scarddlg': 1, 'scrnsave': 1, 'scrnsavw': 1,
'secur32': 1, 'sensapi': 1, 'setupapi': 1, 'sfc': 1, 'shell32': 1,
'shfolder': 1, 'shlwapi': 1, 'sisbkup': 1, 'snmpapi': 1, 'sporder': 1,
'srclient': 1, 'sti': 1, 'strsafe': 1, 'svcguid': 1, 'tapi32': 1, 'thunk32':
1, 'traffic': 1, 'unicows': 1, 'url': 1, 'urlmon': 1, 'user32': 1, 'userenv':
1, 'usp10': 1, 'uuid': 1, 'uxtheme': 1, 'vcomp': 1, 'vcompd': 1, 'vdmdbg': 1,
'version': 1, 'vfw32': 1, 'wbemuuid': 1, 'webpost': 1, 'wiaguid': 1,
'wininet': 1, 'winmm': 1, 'winscard': 1, 'winspool': 1, 'winstrm': 1,
'wintrust': 1, 'wldap32': 1, 'wmiutils': 1, 'wow32': 1, 'ws2_32': 1,
'wsnmp32': 1, 'wsock32': 1, 'wst': 1, 'wtsapi32': 1, 'xaswitch': 1, 'xolehlp':1
}

g_msvc_flag_vars = [
'FRAMEWORK', 'FRAMEWORKPATH',
'STATICLIB', 'LIB', 'LIBPATH', 'LINKFLAGS', 'RPATH',
'INCLUDE',
'CXXFLAGS', 'CCFLAGS', 'CPPPATH', 'CPPLAGS', 'CXXDEFINES']
"main msvc variables"

# ezzel meg szopni fogsz
class msvcobj(ccroot.ccroot):
	def __init__(self, type='program', subtype=None):
		ccroot.ccroot.__init__(self, type, subtype)

		self.ccflags=''
		self.cxxflags=''
		self.cppflags=''

		self._incpaths_lst=[]
		self._bld_incpaths_lst=[]

		self.m_linktask=None
		self.m_deps_linktask=[]

		self.m_type_initials = 'cc'

		global g_msvc_flag_vars
		self.p_flag_vars = g_msvc_flag_vars

		global g_msvc_type_vars
		self.p_type_vars = g_msvc_type_vars
		self.libpaths=[]

	def apply(self):
		ccroot.ccroot.apply(self)
		# FIXME: /Wc, and /Wl, handling came here...

	def apply_defines(self):
		tree = Params.g_build
		clst = self.to_list(self.defines)+self.to_list(self.env['CCDEFINES'])
		cpplst = self.to_list(self.defines)+self.to_list(self.env['CXXDEFINES'])
		cmilst = []
		cppmilst = []

		# now process the local defines
		for defi in clst:
			if not defi in cmilst:
				cmilst.append(defi)

		for defi in cpplst:
			if not defi in cppmilst:
				cppmilst.append(defi)

		# CXXDEFINES_USELIB
		libs = self.to_list(self.uselib)
		for l in libs:
			val = self.env['CXXDEFINES_'+l]
			if val: cmilst += self.to_list(val)
			val = self.env['CCDEFINES_'+l]
			if val: cppmilst += val
		self.env['DEFLINES'] = map(lambda x: "define %s"%  ' '.join(x.split('=', 1)), cmilst)
		self.env['DEFLINES'] = self.env['DEFLINES'] + map(lambda x: "define %s"%  ' '.join(x.split('=', 1)), cppmilst)

		y = self.env['CCDEFINES_ST']
		self.env['_CCDEFFLAGS'] = map(lambda x: y%x, cmilst)
		y = self.env['CXXDEFINES_ST']
		self.env['_CXXDEFFLAGS'] = map(lambda x: y%x, cppmilst)

	def is_syslib(self,libname):
		global g_msvc_systemlibs
		if g_msvc_systemlibs.has_key(libname):
			return True
		return False

	def find_lt_names(self,libname,is_static=False):
		"Win32/MSVC specific code to glean out information from libtool la files."
		lt_names=[
			'lib%s.la' % libname,
			'%s.la' % libname,
		]

		for path in self.libpaths:
			for la in lt_names:
				laf=os.path.join(path,la)
				dll=None
				if exists(laf):
					ltdict=read_la_file(laf)
					lt_libdir=None
					if ltdict.has_key('libdir') and ltdict['libdir'] != '':
						lt_libdir=ltdict['libdir']
					if not is_static and ltdict.has_key('library_names') and ltdict['library_names'] != '':
						dllnames=ltdict['library_names'].split()
						dll=dllnames[0].lower()
						dll=re.sub('\.dll$', '', dll)
						return [lt_libdir,dll,False]
					elif ltdict.has_key('old_library') and ltdict['old_library'] != '':
						olib=ltdict['old_library']
						if exists(os.path.join(path,olib)):
							return [path,olib,True]
						elif lt_libdir != '' and exists(os.path.join(lt_libdir,olib)):
							return [lt_libdir,olib,True]
						else:
							return [None,olib,True]
					else:
						fatal('invalid libtool object file: %s' % laf)
		return [None,None,None]

	def getlibname(self,libname,is_static=False):
		lib=libname.lower()
		lib=re.sub('\.lib$','',lib)

		if self.is_syslib(lib):
			return lib+'.lib'

		lib=re.sub('^lib','',lib)

		if lib == 'm':
			return None

		[lt_path,lt_libname,lt_static]=self.find_lt_names(lib,is_static)

		if lt_path != None and lt_libname != None:
			if lt_static == True:
				# file existance check has been made by find_lt_names
				return os.path.join(lt_path,lt_libname)

		if lt_path != None:
			_libpaths=[lt_path] + self.libpaths
		else:
			_libpaths=self.libpaths

		static_libs=[
			'%ss.lib' % lib,
			'lib%ss.lib' % lib,
			'%s.lib' %lib,
			'lib%s.lib' % lib,
			]

		dynamic_libs=[
			'lib%s.dll.lib' % lib,
			'lib%s.dll.a' % lib,
			'%s.dll.lib' % lib,
			'%s.dll.a' % lib,
			'lib%s_d.lib' % lib,
			'%s_d.lib' % lib,
			'%s.lib' %lib,
			]

		libnames=static_libs
		if not is_static:
			libnames=dynamic_libs + static_libs

		for path in _libpaths:
			for libn in libnames:
				if os.path.exists(os.path.join(path,libn)):
					debug('lib found: %s' % os.path.join(path,libn), 'msvc')
					return libn

		return None

	def apply_obj_vars(self):
		debug('apply_obj_vars called for msvcobj', 'msvc')
		env = self.env
		app = env.append_unique

		cpppath_st       = env['CPPPATH_ST']
		lib_st           = env['LIB_ST']
		staticlib_st     = env['STATICLIB_ST']
		libpath_st       = env['LIBPATH_ST']
		staticlibpath_st = env['STATICLIBPATH_ST']

		self.addflags('CCFLAGS', self.ccflags)
		self.addflags('CXXFLAGS', self.cxxflags)
		self.addflags('CPPFLAGS', self.cppflags)

		# local flags come first
		# set the user-defined includes paths
		if not self._incpaths_lst: self.apply_incpaths()
		for i in self._bld_incpaths_lst:
			app('_CCINCFLAGS', cpppath_st % i.bldpath(env))
			app('_CCINCFLAGS', cpppath_st % i.srcpath(env))
			app('_CXXINCFLAGS', cpppath_st % i.bldpath(self.env))
			app('_CXXINCFLAGS', cpppath_st % i.srcpath(self.env))

		# set the library include paths
		for i in env['CPPPATH']:
			app('_CCINCFLAGS', cpppath_st % i)
			app('_CXXINCFLAGS', cpppath_st % i)

		# this is usually a good idea
		app('_CCINCFLAGS', cpppath_st % '.')
		app('_CCINCFLAGS', cpppath_st % env.variant())
		app('_CXXINCFLAGS', cpppath_st % '.')
		app('_CXXINCFLAGS', cpppath_st % self.env.variant())
		try:
			tmpnode = Params.g_build.m_curdirnode
			app('_CCINCFLAGS', cpppath_st % tmpnode.bldpath(env))
			app('_CCINCFLAGS', cpppath_st % tmpnode.srcpath(env))
			app('_CXXINCFLAGS', cpppath_st % tmpnode.bldpath(self.env))
			app('_CXXINCFLAGS', cpppath_st % tmpnode.srcpath(self.env))
		except:
			pass

		for i in env['RPATH']:   app('LINKFLAGS', i)
		for i in env['LIBPATH']:
			app('LINKFLAGS', libpath_st % i)
			if not self.libpaths.count(i):
				self.libpaths.append(i)
		for i in env['LIBPATH']:
			app('LINKFLAGS', staticlibpath_st % i)
			if not self.libpaths.count(i):
				self.libpaths.append(i)

		# i doubt that anyone will make a fully static binary anyway
		if not env['FULLSTATIC']:
			if env['STATICLIB'] or env['LIB']:
				app('LINKFLAGS', env['SHLIB_MARKER'])

		if env['STATICLIB']:
			app('LINKFLAGS', env['STATICLIB_MARKER'])
			for i in env['STATICLIB']:
				debug('libname: %s' % i,'msvc')
				libname=self.getlibname(i,True)
				debug('libnamefixed: %s' % libname,'msvc')
				if libname != None:
					app('LINKFLAGS', libname)

		if self.env['LIB']:
			for i in env['LIB']:
				debug('libname: %s' % i,'msvc')
				libname=self.getlibname(i)
				debug('libnamefixed: %s' % libname,'msvc')
				if libname != None:
					app('LINKFLAGS', libname)

	def apply_core (self):
		ccroot.ccroot.apply_core(self)
		self.m_linktask.m_type=self.m_type

class msvccc(msvcobj):
	def __init__(self, type='program', subtype=None):
		msvcobj.__init__(self, type, subtype)
		self.s_default_ext = ['.c']
		self.m_type_initials = 'cc'

class msvccpp(msvcobj):
	def __init__(self, type='program', subtype=None):
		msvcobj.__init__(self, type, subtype)
		self.m_type_initials = 'cpp'
		self.s_default_ext = ['.cpp', '.cc', '.cxx','.C']

def setup(env):
	static_link_str = '${STLIBLINK_CXX} ${CPPLNK_SRC_F}${SRC} ${CPPLNK_TGT_F}${TGT}'
	cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} ${CC_SRC_F}${SRC} ${CC_TGT_F}${TGT}'
	cc_link_str = '${LINK_CC} ${CCLNK_SRC_F}${SRC} ${CCLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'
	cpp_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_CXXDEFFLAGS} ${CXX_SRC_F}${SRC} ${CXX_TGT_F}${TGT}'
	cpp_link_str = '${LINK_CXX} ${CPPLNK_SRC_F}${SRC} ${CPPLNK_TGT_F}${TGT} ${LINKFLAGS} ${_LIBDIRFLAGS} ${_LIBFLAGS}'

	Action.simple_action('cc', cc_str, color='GREEN')
	Action.simple_action('cpp', cpp_str, color='GREEN')
	Action.simple_action('ar_link_static', static_link_str, color='YELLOW')

	Action.Action('cc_link', vars=['LINK_CC', 'CCLNK_SRC_F', 'CCLNK_TGT_F', 'LINKFLAGS', '_LIBDIRFLAGS', '_LIBFLAGS','MT','MTFLAGS'] , color='YELLOW', func=msvc_linker)
	Action.Action('cpp_link', vars=[ 'LINK_CXX', 'CPPLNK_SRC_F', 'CPPLNK_TGT_F', 'LINKFLAGS', '_LIBDIRFLAGS', '_LIBFLAGS' ] , color='YELLOW', func=msvc_linker)

	Object.register('cc', msvccc)
	Object.register('cpp', msvccpp)

def detect(conf):

	comp = conf.find_program('CL', var='CXX')
	if not comp:
		return 0;

	link = conf.find_program('LINK')
	if not link:
		return 0;

	stliblink = conf.find_program('LIB')
	if not stliblink:
		return 0;

	manifesttool = conf.find_program('MT')

	v = conf.env

	# c/c++ compiler - check for whitespace, and if so, add quotes
	v['CC']                 = (comp.strip().find(' ') > 0 and '"%s"' % comp or comp).replace('""', '"')
	v['CXX']                 = v['CC']

	v['CPPFLAGS']            = ['/W3', '/nologo', '/c', '/EHsc', '/errorReport:prompt']
	v['CCDEFINES']          = ['WIN32'] # command-line defines
	v['CXXDEFINES']          = ['WIN32'] # command-line defines

	v['_CCINCFLAGS']        = []
	v['_CCDEFFLAGS']        = []
	v['_CXXINCFLAGS']        = []
	v['_CXXDEFFLAGS']        = []

	v['CC_SRC_F']           = ''
	v['CC_TGT_F']           = '/Fo'
	v['CXX_SRC_F']           = ''
	v['CXX_TGT_F']           = '/Fo'

	v['CPPPATH_ST']          = '/I%s' # template for adding include paths

	# Subsystem specific flags
	v['CPPFLAGS_CONSOLE']		= ['/SUBSYSTEM:CONSOLE']
	v['CPPFLAGS_NATIVE']		= ['/SUBSYSTEM:NATIVE']
	v['CPPFLAGS_POSIX']			= ['/SUBSYSTEM:POSIX']
	v['CPPFLAGS_WINDOWS']		= ['/SUBSYSTEM:WINDOWS']
	v['CPPFLAGS_WINDOWSCE']	= ['/SUBSYSTEM:WINDOWSCE']

	# CRT specific flags
	v['CPPFLAGS_CRT_MULTITHREADED'] =						['/MT']
	v['CPPFLAGS_CRT_MULTITHREADED_DLL'] =				['/MD']
	v['CPPDEFINES_CRT_MULTITHREADED'] =					['_MT']
	v['CPPDEFINES_CRT_MULTITHREADED_DLL'] =			['_MT', '_DLL']

	v['CPPFLAGS_CRT_MULTITHREADED_DBG'] =				['/MTd']
	v['CPPFLAGS_CRT_MULTITHREADED_DLL_DBG'] =		['/MDd']
	v['CPPDEFINES_CRT_MULTITHREADED_DBG'] =					['_DEBUG', '_MT']
	v['CPPDEFINES_CRT_MULTITHREADED_DLL_DBG'] =			['_DEBUG', '_MT', '_DLL']

	# compiler debug levels
	v['CCFLAGS']            = ['/TC']
	v['CCFLAGS_OPTIMIZED']  = ['/O2', '/DNDEBUG']
	v['CCFLAGS_RELEASE']    = ['/O2', '/DNDEBUG']
	v['CCFLAGS_DEBUG']      = ['/Od', '/RTC1', '/D_DEBUG', '/ZI']
	v['CCFLAGS_ULTRADEBUG'] = ['/Od', '/RTC1', '/D_DEBUG', '/ZI']

	v['CXXFLAGS']            = ['/TP']
	v['CXXFLAGS_OPTIMIZED']  = ['/O2', '/DNDEBUG']
	v['CXXFLAGS_RELEASE']    = ['/O2', '/DNDEBUG']
	v['CXXFLAGS_DEBUG']      = ['/Od', '/RTC1', '/D_DEBUG', '/ZI']
	v['CXXFLAGS_ULTRADEBUG'] = ['/Od', '/RTC1', '/D_DEBUG', '/ZI']


	# linker
	v['STLIBLINK_CXX']       = '\"%s\"' % stliblink
	v['LINK_CXX']            = '\"%s\"' % link
	v['LINK_CC']             = v['LINK_CXX']
	v['LIB']                 = []

	v['CPPLNK_TGT_F']        = '/OUT:'
	v['CCLNK_TGT_F']         = v['CPPLNK_TGT_F']
	v['CPPLNK_SRC_F']        = ' '
	v['CCLNK_SRC_F']         = v['CCLNK_SRC_F']

	v['LIB_ST']              = '%s.lib'	# template for adding libs
	v['LIBPATH_ST']          = '/LIBPATH:%s' # template for adding libpathes
	v['STATICLIB_ST']        = '%s.lib'
	v['STATICLIBPATH_ST']    = '/LIBPATH:%s'
	v['CCDEFINES_ST']       = '/D%s'
	v['CXXDEFINES_ST']       = '/D%s'
	v['_LIBDIRFLAGS']        = ''
	v['_LIBFLAGS']           = ''

	v['SHLIB_MARKER']        = ''
	v['STATICLIB_MARKER']    = ''

	# manifest tool. Not required for VS 2003 and below. Must have for VS 2005
	# and later
	if manifesttool:
		v['MT'] = manifesttool
		v['MTFLAGS']=['/NOLOGO']

	# linker debug levels
	v['LINKFLAGS']           = ['/NOLOGO', '/MACHINE:X86', '/ERRORREPORT:PROMPT']
	v['LINKFLAGS_OPTIMIZED'] = ['']
	v['LINKFLAGS_RELEASE']   = ['/OPT:REF', '/OPT:ICF', '/INCREMENTAL:NO']
	v['LINKFLAGS_DEBUG']     = ['/DEBUG', '/INCREMENTAL','msvcrtd.lib']
	v['LINKFLAGS_ULTRADEBUG'] = ['/DEBUG', '/INCREMENTAL','msvcrtd.lib']

	try:
		debuglevel = Params.g_options.debug_level
	except AttributeError:
		debuglevel = 'DEBUG'
	else:
		debuglevel = debuglevel.upper()
	v['CCFLAGS']   += v['CCFLAGS_'+debuglevel]
	v['CXXFLAGS']  += v['CXXFLAGS_'+debuglevel]
	v['LINKFLAGS'] += v['LINKFLAGS_'+debuglevel]

	def addflags(var):
		try:
			c = os.environ[var]
			if c:
				# stripping leading and trailing and whitespace and ", Windows cmd is a bit stupid ...
				c=c.strip('" ')
				for cv in c.split():
					v[var].append(cv)
		except:
			pass

	addflags('CXXFLAGS')
	addflags('CPPFLAGS')
	addflags('LINKFLAGS')

	if not v['DESTDIR']: v['DESTDIR']=''

	# shared library
	v['shlib_CCFLAGS']    = ['']
	v['shlib_CXXFLAGS']    = ['']
	v['shlib_LINKFLAGS']   = ['/DLL']
	v['shlib_obj_ext']     = ['.obj']
	v['shlib_PREFIX']      = ''
	v['shlib_SUFFIX']      = '.dll'
	v['shlib_IMPLIB_SUFFIX'] = ['.lib']
	v['shlib_INST_VAR'] = 'PREFIX'
	v['shlib_INST_DIR'] = 'lib'

	# static library
	v['staticlib_LINKFLAGS'] = ['']
	v['staticlib_obj_ext'] = ['.obj']
	v['staticlib_PREFIX']  = ''
	v['staticlib_SUFFIX']  = '.lib'
	v['staticlib_INST_VAR'] = 'PREFIX'
	v['staticlib_INST_DIR'] = 'lib'

	# program
	v['program_obj_ext']   = ['.obj']
	v['program_SUFFIX']    = '.exe'
	v['program_INST_VAR'] = 'PREFIX'
	v['program_INST_DIR'] = 'bin'

	return 1

def set_options(opt):
	try:
		opt.add_option('-d', '--debug-level',
		action = 'store',
		default = 'debug',
		help = 'Specify the debug level. [Allowed values: ultradebug, debug, release, optimized]',
		dest = 'debug_level')
	except optparse.OptionConflictError:
		pass

