#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

"Environment representation"

import os,types, copy, re
import Params
from Utils import Undefined # needed for Environment.load
from Params import debug, warning
re_imp = re.compile('^(#)*?([^#=]*?)\ =\ (.*?)$', re.M)

g_idx = 0
class Environment(object):
	"""A safe-to-use dictionary, but do not attach functions to it please (break cPickle)
	An environment instance can be stored into a file and loaded easily
	"""
	def __init__(self):
		global g_idx
		self.m_idx = g_idx
		g_idx += 1
		self.m_table={}
		#self.m_parent = None <- set only if necessary

		# set the prefix once and for everybody on creation (configuration)
		self.m_table['PREFIX'] = Params.g_options.prefix

	def __contains__(self, key):
		if key in self.m_table: return True
		try: return self.m_parent.__contains__(key)
		except AttributeError: return False # m_parent may not exist

	def set_variant(self, name):
		self.m_table['_VARIANT_'] = name

	def variant(self):
		env = self
		while 1:
			try:
				return env.m_table['_VARIANT_']
			except KeyError:
				try: env = env.m_parent
				except AttributeError: return 'default'

	def copy(self):
		newenv = Environment()
		newenv.m_parent = self
		return newenv

	def __str__(self):
		return "environment table\n"+str(self.m_table)

	def __getitem__(self, key):
		try:
			return self.m_table[key]
		except KeyError:
			try: return self.m_parent[key]
			except: return []

	def __setitem__(self, key, value):
		self.m_table[key] = value

	def get_flat(self, key):
		s = self[key]
		if not s: return ''
		elif isinstance(s, list): return ' '.join(s)
		else: return s

	def _get_list_value_for_modification(self, key):
		"""Gets a value that must be a list for further modification.  The
		list may be modified inplace and there is no need to
		"self.m_table[var] = value" afterwards.
		"""
		try:
			value = self.m_table[key]
		except KeyError:
			try: value = self.m_parent[key]
			except AttributeError: value = []
			if isinstance(value, list):
				value = copy.copy(value)
			else:
				value = [value]
			self.m_table[key] = value
			return value
		else:
			if isinstance(value, list):
				return value # no need to copy the list, it is not borrowed
			else:
				value = [value]
				self.m_table[key] = value
				return value

	def append_value(self, var, value):
		current_value = self._get_list_value_for_modification(var)

		if isinstance(value, list):
			current_value.extend(value)
		else:
			current_value.append(value)

	def prepend_value(self, var, value):
		current_value = self._get_list_value_for_modification(var)

		if isinstance(value, list):
			current_value = value + current_value
			## this is a new list; need to update the dictionary entry
			self.m_table[var] = current_value
		else:
			current_value.insert(0, value)

	# prepend unique would be ambiguous
	def append_unique(self, var, value):
		current_value = self._get_list_value_for_modification(var)

		if isinstance(value, list):
			for value_item in value:
				if value_item not in current_value:
					current_value.append(value_item)
		else:
			if value not in current_value:
				current_value.append(value)

	def store(self, filename):
		"Write the variables into a file"
		file = open(filename, 'w')

		# compute a merged table
		table_list = []
		env = self
		while 1:
			table_list.insert(0, env.m_table)
			try: env = env.m_parent
			except AttributeError: break
		merged_table = dict()
		for table in table_list:
			merged_table.update(table)

		keys = merged_table.keys()
		keys.sort()
		for k in keys: file.write('%s = %r\n' % (k, merged_table[k]))
		file.close()

	def load(self, filename):
		"Retrieve the variables from a file"
		tbl = self.m_table
		file = open(filename, 'r')
		code = file.read()
		file.close()
		for m in re_imp.finditer(code):
			g = m.group
			tbl[g(2)] = eval(g(3))
		debug(self.m_table, 'env')

	def get_destdir(self):
		"return the destdir, useful for installing"
		if self.__getitem__('NOINSTALL'): return ''
		dst = Params.g_options.destdir
		try: dst = os.path.join(dst, os.sep, self.m_table['SUBDEST'])
		except KeyError: pass
		return dst

