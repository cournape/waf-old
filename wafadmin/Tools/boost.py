#!/usr/bin/env python
# encoding: utf-8
#
# written by Ruediger Sonderfeld <ruediger@c-plusplus.de>, 2008
# modified by Bjoern Michaelsen, 2008
#
# partially based on boost.py written by Gernot Vormayr

"""
Boost Configurator:

written by Ruediger Sonderfeld <ruediger@c-plusplus.de>, 2008
modified by Bjoern Michaelsen, 2008
partially based on boost.py written by Gernot Vormayr

Usage:
## wscript
# ...

def set_options(opt):
	opt.tool_options('boost2')
	# ...

def configure(conf):
	# ... (e.g. conf.check_tool('g++'))
	conf.check_tool('boost2)'

	boostconf = conf.create_boost_configurator()
	boostconf.lib = ['iostream', 'filesystem']
	# we dont care about other tags, but version has to be explicitly tagged
	boostconf.min_score = 1000
	boostconf.tagscores['version'] = (1000,-1000)
	# we want a static lib
	boostconf.static = boostconf.STATIC_ONLYSTATIC
	boostconf.run()

ISSUES:
 * find_includes should be called only once!

TODO:
 * run_cache
 * support mandatory
 * ...

"""

import os, os.path, glob, types, re
import Params, Configure, config_c
from logging import fatal, warn
from Configure import conf

class boost_configurator(config_c.configurator_base):
	"""
	- min_version
	- max_version
	- version
	- include_path
	- lib_path
	- lib
	- toolsettag	 - None or a regexp
	- threadingtag	 - None or a regexp
	- abitag		 - None or a regexp
	- versiontag	 - WARNING: you should rather use version or min_version/max_version
	- static		 - look for static libs (values:
						  'nostatic'   or STATIC_NOSTATIC   - ignore static libs (default)
						  'both'       or STATIC_BOTH       - find static libs, too
						  'onlystatic' or STATIC_ONLYSTATIC - find only static libs
	- tagscores['version']
	- tagscores['abi']
	- tagscores['threading']
	- tagscores['toolset']
					 - the tagscores are tuples (match_score, nomatch_score)
						  match_score is the added to the score if the tag is matched
						  nomatch_score is added when a tag is found and does not match
	- min_score
	"""
	## __metaclass__ = config_c.attached_conf ## autohook
	STATIC_NOSTATIC = 'nostatic'
	STATIC_BOTH = 'both'
	STATIC_ONLYSTATIC = 'onlystatic'
	def __init__(self, conf):
		config_c.configurator_base.__init__(self, conf)

		(self.min_version, self.max_version, self.version) = ('','','')
		self.lib_path = ['/usr/lib', '/usr/local/lib', '/opt/local/lib', '/sw/lib', '/lib']
		self.include_path = ['/usr/include', '/usr/local/include', '/opt/local/include', '/sw/include']
		self.lib = ''
		(self.threadingtag, self.abitag, self.versiontag, self.toolsettag) = (None, '^[^d]*$', None, None)
		self.tagscores = {
			'threading': (10,-10),
			'abi': (10,-10),
			'toolset': (1,-1),
			'version': (100,-100) }
		self.min_score = 0
		self.static = boost_configurator.STATIC_NOSTATIC

		self.conf = conf
		self.found_includes = 0

	def run_cache(self, retval): pass # todo

	def validate(self):
		if self.version:
			self.min_version = self.max_version = self.version

	def get_boost_version_number(self, dir):
		test_obj = Configure.check_data()
		test_obj.code = '''
#include <iostream>
#include <boost/version.hpp>
int main() { std::cout << BOOST_VERSION << std::endl; }
'''
		test_obj.env = self.conf.env
		backup = test_obj.env['CPPPATH']
		test_obj.env['CPPPATH'] = [dir]
		test_obj.execute = 1
		test_obj.force_compiler = 'cxx'
		ret = self.conf.run_check(test_obj)
		test_obj.env['CPPPATH'] = backup
		if ret:
			return int(ret['result'])
		else:
			return -1

	def string_to_version(str):
		version = str.split('.')
		return int(version[0])*100000 + int(version[1])*100 + int(version[2])

	def version_string(self, version):
		major = version / 100000
		minor = version / 100 % 1000
		minor_minor = version % 100
		if minor_minor == 0:
			return "%d_%d" % (major, minor)
		else:
			return "%d_%d_%d" % (major, minor, minor_minor)

	def find_includes(self):
		"""
		find_includes checks every path in self.include_path for subdir
		that either starts with boost- or is named boost.

		Than the version is checked and selected accordingly to
		min_version/max_version. The highest possible version number is
		selected!

		If no versiontag is set the versiontag is set accordingly to the
		selected library and CPPPATH_BOOST is set.
		"""
		env = self.conf.env
		guess = []
		include_paths = [getattr(Params.g_options, 'boostincludes', '')]
		if not include_paths[0]:
			if self.include_path is types.StringType:
				include_paths = [self.include_path]
			else:
				include_paths = self.include_path

		min_version = 0
		if self.min_version:
			min_version = string_to_version(self.min_version)
		max_version = 0xFFFFFFFFFFFFFFFF
		if self.max_version:
			max_version = string_to_version(self.max_version)

		version = 0
		boost_path = ''
		for include_path in include_paths:
			boost_paths = glob.glob(include_path + '/boost*')
			for path in boost_paths:
				pathname = path[len(include_path)+1:]
				ret = -1
				if pathname == 'boost':
					path = include_path
					ret = self.get_boost_version_number(path)
				elif pathname.startswith('boost-'):
					ret = self.get_boost_version_number(path)

				if ret != -1 and ret >= min_version and ret <= max_version and ret > version:
					boost_path = path
					version = ret

		if version == 0 or len(boost_path) == 0:
			fatal('boost headers not found! (required version min: %s max: %s)'
				  % (self.min_version, self.max_version))
			return 0

		found_version = self.version_string(version)
		versiontag = '^' + found_version + '$'
		if self.versiontag is None:
			self.versiontag = versiontag
		elif self.versiontag != versiontag:
			warn('boost header version and versiontag do _not_ match!')
		self.conf.check_message('header', 'boost', 1, 'Version ' + found_version +
								' (' + boost_path + ')')
		env['CPPPATH_BOOST'] = boost_path
		env['BOOST_VERSION'] = found_version
		self.found_includes = 1

	def get_toolset(self):
		v = self.conf.env
		toolset = v['CXX_NAME']
		if v['CXX_VERSION']:
			version_no = v['CXX_VERSION'].split('.')
			toolset += version_no[0]
			if len(version_no) > 1:
				toolset += version_no[1]
		return toolset

	def tags_score(self, tags):
		"""
		checks library tags

		see http://www.boost.org/doc/libs/1_35_0/more/getting_started/unix-variants.html 6.1

		"""
		is_versiontag = re.compile('^\d+_\d+_?\d*$')
		is_threadingtag = re.compile('^mt$')
		is_abitag = re.compile('^[sgydpn]+$')
		is_toolsettag = re.compile('^(acc|borland|como|cw|dmc|darwin|gcc|hp_cxx|intel|kylix|msvc|qcc|sun|vacpp)\d*$')
		score = 0
		needed_tags = {
			'threading': self.threadingtag,
			'abi': self.abitag,
			'toolset': self.toolsettag,
			'version': self.versiontag }
		if self.toolsettag is None:
			needed_tags['toolset'] = self.get_toolset()
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

	def libfiles(self, lib, pattern, lib_paths):
		result = []
		for lib_path in lib_paths:
			libname = pattern % ('boost_' + lib + '*')
			result += glob.glob(lib_path + '/' + libname)
		return result

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
		lib_paths = [getattr(Params.g_options, 'boostlibs', '')]
		if not lib_paths[0]:
			if self.lib_path is types.StringType:
				lib_paths = [self.lib_path]
			else:
				lib_paths = self.lib_path
		(libname, file) = (None, None)
		if self.static in [boost_configurator.STATIC_NOSTATIC, boost_configurator.STATIC_BOTH]:
			st_env_prefix = 'LIB'
			files = self.libfiles(lib, self.conf.env['shlib_PATTERN'], lib_paths)
			(libname, file) = self.find_library_from_list(lib, files)
		if libname is None and self.static in [boost_configurator.STATIC_ONLYSTATIC, boost_configurator.STATIC_BOTH]:
			st_env_prefix = 'STATICLIB'
			files = self.libfiles(lib, self.conf.env['staticlib_PATTERN'], lib_paths)
			(libname, file) = self.find_library_from_list(lib, files)
		if libname is not None:
			self.conf.check_message('library', 'boost_'+lib, 1, file)
			self.conf.env['LIBPATH_BOOST_' + lib.upper()] = os.path.split(file)[0]
			self.conf.env[st_env_prefix + '_BOOST_' + lib.upper()] = 'boost_'+libname
			return
		fatal('lib boost_' + lib + ' not found!')

	def find_libraries(self):
		libs_to_find = self.lib
		if self.lib is types.StringType: libs_to_find = [self.lib]
		for lib in libs_to_find:
			self.find_library(lib)

	def run_test(self):
		if not self.found_includes:
			self.find_includes()
		self.find_libraries()

def detect(conf):
	def create_boost_configurator(self):
		return boost_configurator(conf)
	conf.hook(create_boost_configurator)

def set_options(opt):
	opt.add_option('--boost-includes', type='string', default='', dest='boostincludes', help='path to the boost directory where the includes are e.g. /usr/local/include/boost-1_35')
	opt.add_option('--boost-libs', type='string', default='', dest='boostlibs', help='path to the directory where the boost libs are e.g. /usr/local/lib')
