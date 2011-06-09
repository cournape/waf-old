#!/usr/bin/env python
# encoding: utf-8
# Laurent Birtz, 2011
# moved the code into a separate tool (ita)

"""
Assumptions:
- configuration options are not always added to the right group (and do not count on the users to do it...)
- the options are persistent between the executions (waf options are NOT persistent by design)

Questions:
  * should the configuration re-use those persistent options too?
  * why should the review command force a reconfiguration?
  * should a few options be non-persistent anyway (-jn, destdir, etc)
"""

import os, types, tempfile, optparse, sys, textwrap, shutil
from waflib import Logs, Utils, Context, ConfigSet, Options, Build

class Odict(dict):
	"""Ordered dictionary"""
	def __init__(self, data=None):
		self._keys = []
		dict.__init__(self)
		if data:
			# we were provided a regular dict
			if isinstance(data, dict):
				self.append_from_dict(data)

			# we were provided a tuple list
			elif type(data) == list:
				self.append_from_plist(data)

			# we were provided invalid input
			else:
				raise Exception("expected a dict or a tuple list")

	def append_from_dict(self, dict):
		map(self.__setitem__, dict.keys(), dict.values())

	def append_from_plist(self, plist):
		for pair in plist:
			if len(pair) != 2:
				raise Exception("invalid pairs list")
		for (k, v) in plist:
			self.__setitem__(k, v)

	def __delitem__(self, key):
		if not key in self._keys:
			raise KeyError, key
		dict.__delitem__(self, key)
		self._keys.remove(key)

	def __setitem__(self, key, item):
		dict.__setitem__(self, key, item)
		if key not in self._keys:
			self._keys.append(key)

	def clear(self):
		dict.clear(self)
		self._keys = []

	def copy(self):
		return odict(self.plist())

	def items(self):
		return zip(self._keys, self.values())

	def keys(self):
		return list(self._keys) # return a copy of the list

	def values(self):
		return map(self.get, self._keys)

	def plist(self):
		p = []
		for k, v in self.items():
			p.append( (k, v) )
		return p

	def __str__(self):
		s = "{"
		l = len(self._keys)
		for k, v in self.items():
			l -= 1
			strkey = str(k)
			if isinstance(k, basestring): strkey = "'"+strkey+"'"
			strval = str(v)
			if isinstance(v, basestring): strval = "'"+strval+"'"
			s += strkey + ":" + strval
			if l > 0: s += ", "
		s += "}"
		return s

review_options = Odict()
"""
Ordered dictionary mapping configuration option names to their optparse option.
"""

review_defaults = {}
"""
Dictionary mapping configuration option names to their default value.
"""

class OptionsReview(Options.OptionsContext):
	def __init__(self, **kw):
		super(self.__class__, self).__init__(**kw)

	def prepare_config_review(self):
		gr = self.get_option_group('configure options')
		for opt in gr.option_list:
			if opt.action != 'store' or opt.dest in ("out", "top"):
				continue
			review_options[opt.dest] = opt
			review_defaults[opt.dest] = opt.default
			if gr.defaults.has_key(opt.dest):
				del gr.defaults[opt.dest]
			opt.default = None

	def put_the_default_options_back(self):
		gr = self.get_option_group('configure options')
		for opt in gr.option_list:
			if opt.action != 'store' or opt.dest in ("out", "top"):
				continue
			if opt.dest in review_defaults and opt.default is None:
				opt.default = review_defaults[opt.dest]
			if not getattr(Options.options, opt.dest, None):
				setattr(Options.options, opt.dest, opt.default)

	def add_configuration_options(self):
		#if 'configure' in Options.commands: # <- TODO to decide
		#	return

		path = Context.run_dir + os.sep + Options.lockfile
		env = ConfigSet.ConfigSet()
		try:
			env.load(path)
		except:
			return
		gr = self.get_option_group('configure options')
		for opt in gr.option_list:
			if opt.action != 'store' or opt.dest in ("out", "top"):
				continue
			if opt.dest in review_defaults and opt.default is None:
				opt.default = env.options.get(opt.dest, None)
			if not getattr(Options.options, opt.dest, None):
				#print "setting %r to %r" % (opt.dest, opt.default)
				setattr(Options.options, opt.dest, opt.default)

	def parse_args(self):
		self.prepare_config_review()
		self.parser.get_option('--prefix').help = 'installation prefix'
		super(OptionsReview, self).parse_args()
		self.add_configuration_options()
		self.put_the_default_options_back()

class ReviewContext(Context.Context):
	'''reviews the configuration values'''

	cmd = 'review'

	def __init__(self, **kw):
		super(self.__class__, self).__init__(**kw)

		out = Options.options.out
		if not out:
			out = getattr(Context.g_module, Context.OUT, None)
		if not out:
			out = Options.lockfile.replace('.lock-waf', '')
		self.build_path = (os.path.isabs(out) and self.root or self.path).make_node(out).abspath()
		"""Path to the build directory"""

		self.cache_path = os.path.join(self.build_path, Build.CACHE_DIR)
		"""Path to the cache directory"""

		self.review_path = os.path.join(self.cache_path, 'review.cache')
		"""Path to the review cache file"""

	def execute(self):
		"""
		Load the previous review set, update the review set with the options
		specified on the command line, import the option values in the option
		dictionary, store the review set on disk and display the review set.
		The configuration cache is invalidated if the reviewable options have
		changed.
		"""
		(old_set, new_set) = self.refresh_review_set()
		print(self.display_review_set(new_set))

		# TODO uh, why removing that?
		#if not self.compare_review_set(old_set, new_set):
		#	self.delete_cache()

	def refresh_review_set(self, store=True):
		"""
		Load the previous review set, update the review set with the options
		specified on the command line, import the option values in the option
		dictionary and store the review set on disk if requested. Return a
		tuple containing the previous and the current review sets.
		"""
		old_set = self.load_review_set()
		new_set = self.update_review_set(old_set)
		self.import_review_set(new_set)
		if store:
			self.store_review_set(new_set)
		return (old_set, new_set)

	def load_review_set(self):
		"""
		Load and return the review set from the cache if it exists.
		Otherwise, return an empty set.
		"""
		if os.path.isfile(self.review_path):
			return ConfigSet.ConfigSet(self.review_path)
		return ConfigSet.ConfigSet()

	def store_review_set(self, review_set):
		"""
		Store the review set specified in the cache.
		"""
		if not os.path.isdir(self.build_path):
			os.makedirs(self.build_path)
		review_set.store(self.review_path)

	def update_review_set(self, old_set):
		"""
		Merge the options passed on the command line with those imported
		from the previous review set and return the corresponding
		preview set.
		"""
		def val_to_str(val):
			if val == None or val == '':
				return ''
			return str(val)

		new_set = ConfigSet.ConfigSet()
		opt_dict = Options.options.__dict__

		for name in review_options.keys():
			# the option is specified explicitly on the command line
			if name in opt_dict:
				# if the option is the default, pretend it was never specified
				if val_to_str(opt_dict[name]) != val_to_str(review_defaults[name]):
					new_set[name] = opt_dict[name]
			# the option was explicitly specified in a previous command
			elif name in old_set:
				new_set[name] = old_set[name]

		return new_set

	def import_review_set(self, review_set):
		"""
		Import the actual value of the reviewable options in the option
		dictionary, given the current review set.
		"""
		for name in review_options.keys():
			if name in review_set:
				value = review_set[name]
			else:
				value = review_defaults[name]
			setattr(Options.options, name, value)

	def compare_review_set(self, set1, set2):
		"""
		Return true if the review sets specified are equal.
		"""
		if len(set1.table) != len(set2.table): return False
		for key in set1.table:
			if not key in set2 or set1[key] != set2[key]:
				return False
		return True

	def delete_cache(self):
		"""
		Delete the build cache directory, if any.
		"""
		if os.path.isdir(self.cache_path):
			shutil.rmtree(self.cache_path)

	def display_review_set(self, review_set):
		"""
		Return the string representing the review set specified.
		"""
		term_width = Logs.get_term_cols()
		lines = []
		for dest in review_options.keys():
			opt = review_options[dest]
			name = ", ".join(opt._short_opts + opt._long_opts)
			help = opt.help
			actual = None
			if dest in review_set: actual = review_set[dest]
			default = review_defaults[dest]
			lines.append(self.format_option(name, help, actual, default, term_width))
		return "Configuration:\n\n" + "\n\n".join(lines) + "\n"

	def format_option(self, name, help, actual, default, term_width):
		"""
		Return the string representing the option specified.
		"""
		def val_to_str(val):
			if val == None or val == '':
				return "(void)"
			return str(val)

		max_name_len = 20
		sep_len = 2

		w = textwrap.TextWrapper()
		w.width = term_width - 1
		if w.width < 60: w.width = 60

		out = ""

		# format the help
		out += w.fill(help) + "\n"

		# format the name
		name_len = len(name)
		out += Logs.colors.CYAN + name + Logs.colors.NORMAL

		# set the indentation used when the value wraps to the next line
		w.subsequent_indent = " ".rjust(max_name_len + sep_len)
		w.width -= (max_name_len + sep_len)

		# the name string is too long, switch to the next line
		if name_len > max_name_len:
			out += "\n" + w.subsequent_indent

		# fill the remaining of the line with spaces
		else:
			out += " ".rjust(max_name_len + sep_len - name_len)

		# format the actual value, if there is one
		if actual != None:
			out += Logs.colors.BOLD + w.fill(val_to_str(actual)) + Logs.colors.NORMAL + "\n" + w.subsequent_indent

		# format the default value
		default_fmt = val_to_str(default)
		if actual != None:
			default_fmt = "default: " + default_fmt
		out += Logs.colors.NORMAL + w.fill(default_fmt) + Logs.colors.NORMAL

		return out

