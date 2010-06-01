#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010 (ita)

class WafError(Exception):
	"""Base for all waf errors"""
	def __init__(self, *args):
		self.args = args
		try:
			self.stack = traceback.extract_stack()
		except:
			pass
		Exception.__init__(self, *args)
	def __str__(self):
		return str(len(self.args) == 1 and self.args[0] or self.args)

class WscriptError(WafError):
	"""Waf errors that come from python code"""
	def __init__(self, message, pyfile=None):
		if pyfile:
			self.pyfile = pyfile
			self.pyline = None
		else:
			try:
				(self.pyfile, self.pyline) = self.locate_error()
			except:
				(self.pyfile, self.pyline) = (None, None)

		msg_file_line = ''
		if self.pyfile:
			msg_file_line = "%s:" % self.pyfile
			if self.pyline:
				msg_file_line += "%s:" % self.pyline
		err_message = "%s error: %s" % (msg_file_line, message)
		WafError.__init__(self, err_message)

	def locate_error(self):
		stack = traceback.extract_stack()
		stack.reverse()
		for frame in stack:
			file_name = os.path.basename(frame[0])
			if file_name.find(WSCRIPT_FILE) > -1:
				return (frame[0], frame[1])
		return (None, None)

class BuildError(WafError):
	"""Error raised during the build and install phases"""
	def __init__(self, error_tasks=[]):
		self.tasks = error_tasks
		WafError.__init__(self, self.format_error())

	def format_error(self):
		lst = ['Build failed']
		for tsk in self.tasks:
			txt = tsk.format_error()
			if txt: lst.append(txt)
		return '\n'.join(lst)

class ConfigurationError(WscriptError):
	"""configuration exception"""
	pass

