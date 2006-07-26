#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, os.path, types, sys, imp
import Build, Params, Utils, Options, Configure, Environment
from Params import debug, error, trace, fatal
import Utils

try:
	from xml.sax import make_parser 
	from xml.sax.handler import ContentHandler 
except:
	fatal('wscript_xml requires the Python xml modules (sax)!')


def compile(file_path):
	parser = make_parser()
	curHandler = XMLHandler()
	parser.setContentHandler(curHandler)
	fi = open(file_path)
	parser.parse(fi)
	fi.close()

	res = "".join(curHandler.doc)
	module = imp.new_module('wscript')

	print res
	fatal('stop now')

	exec res in module.__dict__

	Utils.g_loaded_modules[file_path[:len(file_path)-4]] = module
	Utils.g_module = module

class XMLHandler(ContentHandler): 
	def __init__(self):
		self.doc = []
		self.buf = []
		self.obj = 0
		self.tmp_lst = []
	def startElement(self, name, attrs):
		if self.obj and name != 'obj':

			if name == 'item':
				self.tmp_lst.append(attrs['value'])
				return

			if 'type' in attrs and attrs['type'] == 'list':
				self.tmp_lst = []
				#setattr(self.obj, name, self.tmp_lst)
				return

			print '\tobj.%s="%s"\n' % (name, attrs['value'])
			#setattr(self.obj, name, attrs['value'])

			return

		if name == 'obj':
			self.doc += '\tobj = bld.createObj("%s")\n' % attrs['type']
			self.obj += 1
			return

		if name == 'document':
			self.buf = []
			return
		if name == 'options':
			self.doc += 'def set_options(opt):\n'
			return
		if name == 'config':
			self.doc += 'def configure(conf):\n'
			return
		if name == 'build':
			self.doc += 'def build(bld):\n'
			return
		if name == 'tool_option':
			self.doc += '\topt.tool_options("%s")\n' % attrs['value']
			return

		if name == 'option':
			self.doc += '\topt.add_option('
			return
		if name == 'optparam':
			if 'name' in attrs:
				self.doc += "%s='%s', " % (attrs['name'], attrs['value'])
			else:
				self.doc += "'%s', " % attrs['value']

		self.buf = []
	def endElement(self, name): 
		buf = "".join(self.buf)

		# object handling
		if self.obj and name != 'obj':
			if self.tmp_lst and name != 'item':
				self.doc += "\tobj.%s = " % name
				self.doc += str(self.tmp_lst) + "\n"
				self.tmp_lst = []
			return
		if name == 'obj':
			self.obj -= 1
			return

		if name == 'version':
			self.doc += 'VERSION = "%s"\n' % buf
			return
		if name == 'appname':
			self.doc += 'APPNAME = "%s"\n' % buf
			return
		if name == 'srcdir':
			self.doc += 'srcdir  = "%s"\n' % buf
			return
		if name == 'blddir':
			self.doc += 'blddir  = "%s"\n' % buf
			return
		if name == 'build':
			self.doc += '\treturn\n'
			return
		if name == 'config':
			self.doc += '\treturn\n'
			return
		if name == 'options':
			self.doc += '\treturn\n'
			return
		if name == 'option':
			self.doc += ')\n'
			return
		if name == 'config-code':
			self.doc += '%s\n\n' % buf
			return


		if name == 'version':
			return
		if name == 'version':
			return
		if name == 'version':
			return
		if name == 'version':
			return
		return

	def characters(self, cars):
		self.buf.append(cars)

