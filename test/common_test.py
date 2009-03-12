#! /usr/bin/env python
# encoding: utf-8
# Yinon Ehrlich, 2008

"""
Should be serve as common tester for all waf testers.
"""

import os, sys, unittest, shutil, types
import optparse

import Test

# allow importing wafadmin modules
parentdir = os.path.dirname( os.path.dirname( os.path.abspath(__file__) ) )
sys.path.append(os.path.join( parentdir, Test.DIRS.WAFADMIN ) )

import pproc
import Environment
import Configure
import Options
from Constants import *
import Utils
import Logs

# global variable - used to control the output of tests.
verbose = 0

class StartupError(Utils.WafError):
	pass

class CommonTester(unittest.TestCase):

	def __init__(self, methodName):
		self._waf_root_dir=os.getcwd()
		self._waf_exe = os.path.join(self._waf_root_dir, "waf")

		# validate current dir is waf directory
		self.validate_waf_path_exist(self._waf_root_dir)
		self.validate_waf_path_exist("waf-light")
		unittest.TestCase.__init__(self, methodName)

	def validate_waf_path_exist(self, file_or_directory):
		"""
		raise StartupError if specified file_or_directory not exists
		"""
		if not os.path.exists(file_or_directory):
			raise StartupError("cannot find '%s', please run tests from waf root directory." % file_or_directory)

	def _write_file(self, filename, contents):
		try:
			a_file = open( filename, 'w' )
			if contents:
				a_file.write(contents)
			else:
				a_file.write(contents)
		finally:
			a_file.close()

	def _write_wscript(self, contents = '', use_dic=True):
		if not contents:
			contents = wscript_contents
		if use_dic:
			contents = contents % self._test_dic

		self._write_file(self._wscript_file_path, contents)

	def call(self, commands):
		"""
		call: subprocess call method with (by default) silent stdout and stderr,
						test its return value to make sure it succeeded"
		@param commands [list] commands to run.
		@return:
				[tuple] (returncode, stdout, stderr):
		"""
		kwargs = dict()

		cmd = " ".join(commands)

		# Don't show output, run `waf check -vv` when need to check-out what went wrong...
		kwargs['stdout'] = kwargs['stderr'] = pproc.PIPE

		proc = pproc.Popen(cmd, shell=1, **kwargs)
		(stdout, stderr) = proc.communicate()
		if verbose:
 			sys.stdout.write(stdout)
			sys.stderr.write(stderr)

		return (proc.returncode, stdout, stderr)

	def _copy(self, source, target):
		"""
		"generic" way to copy files/directories. Target must not already exist.
		"""
		if os.path.isfile(source):
			shutil.copy2(source, target)
		else:
			# When copying directory to another directory using shutil.copytree, the directory
			# name of the source is NOT created in the target
			src_dirname = os.path.split(source)[-1]
			target_dirname = os.path.split(target)[-1]
			if src_dirname != target_dirname:
				target = os.path.join(target, src_dirname)

			shutil.copytree(source, target)
			
	def _test_configure(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('configure', test_for_success, additionalArgs)

	def _test_build(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('build', test_for_success, additionalArgs)
	
	def _test_clean(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('clean', test_for_success, additionalArgs)

	def _test_distclean(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('distclean', test_for_success, additionalArgs)

	def _test_dist(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('dist', test_for_success, additionalArgs)

	def _test_distcheck(self, test_for_success=True, additionalArgs=[]):
		return self._run_command('distcheck', test_for_success, additionalArgs)

	def _run_command(self, command_name, test_for_success=True, additionalArgs=[]):
		"""
		_run_command - tests for various commands. the specific command to test
		is given by @command_name.

		@param command_name: one of @available_commands below.
		@param test_for_success [boolean]: test for success/failure ?
				for example: to make sure command has failed, pass False.
		@param additionalArgs [list]: optional additional arguments to command.
		@returns [tuple] (stdout, stderr)
		"""

		if not isinstance(additionalArgs, list):
			raise ValueError("additional args must be a list")

		available_commands = 'build configure clean dist distcheck distclean'.split()

		if not command_name in available_commands:
			raise ValueError("The parameter 'command_name' must be on of %s (%s was given)." %
				   (", ".join(available_commands), command_name))

		err_msg = command_name

		if test_for_success:
			test_func = self.assertEquals		   # ret val of 0 is False...
			err_msg += " failed"
		else:
			test_func = self.assertNotEquals   # ret val of NON-Zero is True...
			err_msg += " should fail"

		args_list = [sys.executable, self._waf_exe, command_name]
		if additionalArgs: args_list.extend(list(additionalArgs))
		if verbose > 1: additionalArgs.append('-' + ('v'*(verbose-1)))
		if additionalArgs: args_list.extend(list(additionalArgs))
		(ret_val, stdout, stderr) = self.call(args_list)
		test_func(0, ret_val, err_msg)
		return (stdout, stderr)

	def _test_run(self, commandline):
		"""
		test running the generated executable succeed
		@param commandline [string]: the commandline to run.
		"""
		(ret_val, stdout, stderr) = self.call([commandline])
		self.assertEquals(0, ret_val, "running '%s' failed" % commandline)
		return (stdout, stderr)

	def _same_env(self, expected_env, env_name='default'):
		"""
		All parameters decided upon configure are written to cache, then read on build. 
		This function checks that the written environment has the same values for keys given by expected_env
		@param expected_env [dictionary]: a dictionary that contains
					one or more key-value pairs to compare to stored environment
		@return: True if values the same,
				False otherwise
		"""
		if expected_env is None or not expected_env:
			raise ValueError("env must contains at least one key-value pair")
		else:
			# Environment uses arguments defined by Options
			opt_obj = Options.Handler()
			opt_obj.parse_args()

			stored_env = Environment.Environment()
			stored_env_path = os.path.join(self._blddir, CACHE_DIR, env_name+CACHE_SUFFIX)
			stored_env.load( stored_env_path )
			for key in expected_env:
				# using sort() to ignore differences in order.
				# Not using sets.Set in order to identify redundant flags.
				stored_items = stored_env[key]
				expected_items = expected_env[key]
				stored_items.sort()
				expected_items.sort()
				self.assertEqual( stored_items, expected_items,
								"values of '%s' differ: expected = '%s', stored = '%s'"
								% (key,expected_items, stored_items))

	def _setup_configure(self, blddir='', srcdir=''):
		if not blddir:
			blddir = self._blddir
			if not blddir: raise ValueError('no blddir argument, no self._blddir !')

		if not srcdir:
			blddir = self._test_dir_root
			if not blddir: raise ValueError('no srcdir argument, no self._test_dir_root !')

		# Configure uses arguments defined by Options
		opt_obj = Options.Handler()
		opt_obj.parse_args()
		Options.options.prefix = Options.default_prefix
		os.makedirs(os.path.join(blddir, Options.variant_name))
		return Configure.ConfigurationContext(srcdir=srcdir, blddir=blddir)

def get_args_options(usage=None):
	'''
	Parse arguments passed for the waf tests modules.
	Returns the options class.
	'''
	parser = optparse.OptionParser(usage)
	parser.add_option('-v', '--verbose', action='count', default=0, help='verbosity level -v -vv or -vvv [Default: 0]', dest='verbose')
	(options, args) = parser.parse_args()

	# adjust Waf verbosity to the tests verbosity
	Logs.verbose = options.verbose

	# on -vv show the output of the tests
	global verbose
	verbose= options.verbose

	return options
