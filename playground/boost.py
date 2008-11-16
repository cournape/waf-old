#!/usr/bin/env python
# encoding: utf-8
#
# partially based on boost.py written by Gernot Vormayr
# written by Ruediger Sonderfeld <ruediger@c-plusplus.de>, 2008
# modified by Bjoern Michaelsen, 2008
# modified by Luca Fossati, 2008
# rewritten for waf 1.5.1
#
#def set_options(opt):
#	opt.tool_options('boost')
#	# ...
#
#def configure(conf):
#	# ... (e.g. conf.check_tool('g++'))
#	conf.check_tool('boost')
#
#   conf.check_boost(lib='iostream filesystem', kind=STATIC_ONLYSTATIC,
#      tag_version=(-1000, 1000), tag_minscore= 1000)
#
#	boostconf = conf.create_boost_configurator()
#	boostconf.lib = ['iostream', 'filesystem']
#	# we dont care about other tags, but version has to be explicitly tagged
#	boostconf.min_score = 1000
#	boostconf.tagscores['version'] = (1000,-1000)
#	# we want a static lib
#	boostconf.static = boostconf.STATIC_ONLYSTATIC
#	boostconf.run()
#
#ISSUES:
# * find_includes should be called only once!
# * support mandatory


boost_code = '''
#include <iostream>
#include <boost/version.hpp>
int main() { std::cout << BOOST_VERSION << std::endl; }'''

boost_libpath = ['/usr/lib', '/usr/local/lib', '/opt/local/lib', '/sw/lib', '/lib']
boost_cpppath = ['/usr/include', '/usr/local/include', '/opt/local/include', '/sw/include']

is_versiontag = re.compile('^\d+_\d+_?\d*$')
is_threadingtag = re.compile('^mt$')
is_abitag = re.compile('^[sgydpn]+$')
is_toolsettag = re.compile('^(acc|borland|como|cw|dmc|darwin|gcc|hp_cxx|intel|kylix|msvc|qcc|sun|vacpp)\d*$')

STATIC_NOSTATIC = 'nostatic'
STATIC_BOTH = 'both'
STATIC_ONLYSTATIC = 'onlystatic'


import os.path, glob, types, re, sys
import Configure, config_c, Options, Utils
from Logs import warn
from Configure import conf

def set_options(opt):
	opt.add_option('--boost-includes', type='string', default='', dest='boostincludes', help='path to the boost directory where the includes are e.g. /usr/local/include/boost-1_35')
	opt.add_option('--boost-libs', type='string', default='', dest='boostlibs', help='path to the directory where the boost libs are e.g. /usr/local/lib')

def string_to_version(s):
	version = s.split('.')
	return int(version[0])*100000 + int(version[1])*100 + int(version[2])

def version_string(version):
	major = version / 100000
	minor = version / 100 % 1000
	minor_minor = version % 100
	if minor_minor == 0:
		return "%d_%d" % (major, minor)
	else:
		return "%d_%d_%d" % (major, minor, minor_minor)

def libfiles(lib, pattern, lib_paths):
	result = []
	for lib_path in lib_paths:
		libname = pattern % ('boost_' + lib + '*')
		result += glob.glob(lib_path + '/' + libname)
	return result

@conf
def get_boost_version_number(self, dir):
	"""silently retrieve the boost version number"""
	try:
		return self.run_c_code(compiler='cxx', code=boost_code, cpppath=dir, execute=1, env=self.env.copy(), type='cprogram')
	except Configure.ConfigurationError, e:
		return -1

def set_default(kw, var, val):
	if not var in kw:
		kw[var] = val

@conf
def validate_boost(self, *k, **kw):
	ver = kw.get('version', '')
	for x in 'min_version max_version version'.split():
		set_default(kw, x, ver)

	set_default(kw, 'lib', '')
	kw['lib'] = Utils.to_list(kw['lib'])

	set_default(kw, 'libpath', boost_libpath)
	set_default(kw, 'cpppath', boost_cpppath)
	for x in 'tag_threading tag_abi tag_toolset'.split():
		set_default(kw, x, None)
	set_default(kw, 'tag_version', '^[^d]*$')

	set_default(kw, 'score_threading', (10, -10))
	set_default(kw, 'score_abi', (10, -10))
	set_default(kw, 'score_toolset', (1, -1))
	set_default(kw, 'score_version', (100, -100))

	set_default(kw, 'score_min', 0)
	set_default(kw, 'static', STATIC_NOSTATIC)
	set_default(kw, 'found_includes', False)

@conf
def find_boost_includes(self, kw):
	"""
	check every path in kw['cpppath'] for subdir
	that either starts with boost- or is named boost.

	Then the version is checked and selected accordingly to
	min_version/max_version. The highest possible version number is
	selected!

	If no versiontag is set the versiontag is set accordingly to the
	selected library and CPPPATH_BOOST is set.
	"""
	boostPath = getattr(Options.options, 'boostincludes', '')
	if boostPath:
		boostPath = [os.path.normpath(os.path.expandvars(os.path.expanduser(boostPath)))]
	else:
		boostPath = Utils.to_list(kw['cpppath'])

	min_version = string_to_version(kw.get('min_version', '0'))
	min_version = string_to_version(kw.get('max_version', '0')) or sys.maxint

	version = 0
	for include_path in include_paths:
		boost_paths = glob.glob(os.path.join(include_path, 'boost*'))
		for path in boost_paths:
			pathname = os.path.split(path)[-1]
			ret = -1
			if pathname == 'boost':
				path = include_path
				ret = self.get_boost_version_number(path)
			elif pathname.startswith('boost-'):
				ret = self.get_boost_version_number(path)

			if ret != -1 and ret >= min_version and ret <= max_version and ret > version:
				boost_path = path
				version = ret
				break
	else:
		conf.fatal('boost headers not found! (required version min: %s max: %s)'
			  % (kw['min_version'], kw['self.max_version']))
		return False

	found_version = version_string(version)
	versiontag = '^' + found_version + '$'
	if kw['tag_version'] is None:
		kw['tag_version'] = versiontag
	elif kw['tag_version'] != versiontag:
		warn('boost header version and tag_version do not match!')
	self.conf.check_message('header', 'boost', 1, 'Version ' + found_version +
							' (' + boost_path + ')')
	env = self.env
	env['CPPPATH_BOOST'] = boost_path
	env['BOOST_VERSION'] = found_version
	self.found_includes = 1

def get_toolset(env):
	v = env
	toolset = v['CXX_NAME']
	if v['CXX_VERSION']:
		version_no = v['CXX_VERSION'].split('.')
		toolset += version_no[0]
		if len(version_no) > 1:
			toolset += version_no[1]
	return toolset

@conf
def exec_boost(self, *k, **kw):
	if not self.found_includes:
		self.find_includes()
	for lib in kw['lib']:
		self.find_library(lib)

@conf
def check_boost(self, *k, **kw):
	self.validate_boost(kw)
	if 'msg' in kw:
		self.check_message_1(kw['msg'])
	ret = None
	try:
		ret = self.exec_boost(kw)
	except Configure.ConfigurationError, e:
		if 'errmsg' in kw:
			self.check_message_2(kw['errmsg'], 'YELLOW')
		if 'mandatory' in kw:
			if Logs.verbose > 1:
				raise
			else:
				self.fatal('the configuration failed (see config.log)')
	else:
		if 'okmsg' in kw:
			self.check_message_2(kw['okmsg'])

	return ret

####### old code below #########


class boost_configurator(Configure.ConfigurationContext):
#
#	- min_version
#	- max_version
#	- version
#	- include_path
#	- lib_path
#	- lib
#	- toolsettag	 - None or a regexp
#	- threadingtag	 - None or a regexp
#	- abitag		 - None or a regexp
#	- versiontag	 - WARNING: you should rather use version or min_version/max_version
#	- static		 - look for static libs (values:
#						  'nostatic'   or STATIC_NOSTATIC   - ignore static libs (default)
#						  'both'       or STATIC_BOTH       - find static libs, too
#						  'onlystatic' or STATIC_ONLYSTATIC - find only static libs
#	- tagscores['version']
#	- tagscores['abi']
#	- tagscores['threading']
#	- tagscores['toolset']
#					 - the tagscores are tuples (match_score, nomatch_score)
#						  match_score is the added to the score if the tag is matched
#						  nomatch_score is added when a tag is found and does not match
#	- min_score
#
#	## __metaclass__ = config_c.attached_conf ## autohook
#	def __init__(self, conf):
#		config_c.configurator_base.__init__(self, conf)
#
#		(self.min_version, self.max_version, self.version) = ('','','')
#		self.lib_path = boost_libpath
#		self.include_path = boost_cpppath
#		self.lib = ''
#		(self.threadingtag, self.abitag, self.versiontag, self.toolsettag) = (None, '^[^d]*$', None, None)
#		self.tagscores = {
#			'threading': (10,-10),
#			'abi': (10,-10),
#			'toolset': (1,-1),
#			'version': (100,-100) }
#		self.min_score = 0
#		self.static = STATIC_NOSTATIC
#
#		self.conf = conf
#		self.found_includes = 0
#
#
#	def validate(self):
#		if self.version:
#			self.min_version = self.max_version = self.version
#
	def tags_score(self, tags):
		"""
		checks library tags

		see http://www.boost.org/doc/libs/1_35_0/more/getting_started/unix-variants.html 6.1

		"""
		score = 0
		needed_tags = {
			'threading': self.threadingtag,
			'abi': self.abitag,
			'toolset': self.toolsettag,
			'version': self.versiontag }
		if self.toolsettag is None:
			needed_tags['toolset'] = get_toolset(self.conf.env)
		found_tags = {}
		for tag in tags:
			if is_versiontag.match(tag): found_tags['version'] = tag
			if is_threadingtag.match(tag): found_tags['threading'] = tag
			if is_abitag.match(tag): found_tags['abi'] = tag
			if is_toolsettag.match(tag): found_tags['toolset'] = tag
		for tagname in needed_tags.iterkeys():
			if needed_tags[tagname] is not None and found_tags.has_key(tagname):
				if re.compile(needed_tags[tagname]).match(found_tags[tagname]):
					score += self.tagscores[tagname][0]
				else:
					score += self.tagscores[tagname][1]
		return score

	def find_library_from_list(self, lib, files):
		lib_pattern = re.compile('.*boost_(.*?)\..*')
		result = (None, None)
		resultscore = self.min_score-1
		for file in files:
			m = lib_pattern.search(file, 1)
			if m:
				libname = m.group(1)
				libtags = libname.split('-')[1:]
				currentscore = self.tags_score(libtags)
				if currentscore > resultscore:
					result = (libname, file)
					resultscore = currentscore
		return result

	def find_library(self, lib):
		"""
		searches library paths for lib.
		"""
		boostPath = getattr(Options.options, 'boostlibs', '')
		if not boostPath:
			if self.lib_path is types.StringType:
				lib_paths = [self.lib_path]
			else:
				lib_paths = self.lib_path
		else:
			lib_paths = [os.path.normpath(os.path.expandvars(os.path.expanduser(boostPath)))]
		(libname, file) = (None, None)
		if self.static in [STATIC_NOSTATIC, STATIC_BOTH]:
			st_env_prefix = 'LIB'
			files = libfiles(lib, self.conf.env['shlib_PATTERN'], lib_paths)
			(libname, file) = self.find_library_from_list(lib, files)
		if libname is None and self.static in [STATIC_ONLYSTATIC, STATIC_BOTH]:
			st_env_prefix = 'STATICLIB'
			files = libfiles(lib, self.conf.env['staticlib_PATTERN'], lib_paths)
			(libname, file) = self.find_library_from_list(lib, files)
		if libname is not None:
			self.conf.check_message('library', 'boost_'+lib, 1, file)
			self.conf.env['LIBPATH_BOOST_' + lib.upper()] = os.path.split(file)[0]
			self.conf.env[st_env_prefix + '_BOOST_' + lib.upper()] = 'boost_'+libname
			return
		conf.fatal('lib boost_' + lib + ' not found!')

	def find_libraries(self):
		#libs_to_find = self.lib
		#if self.lib is types.StringType: libs_to_find = [self.lib]

