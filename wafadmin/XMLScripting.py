#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os, os.path, types, sys, imp
import Build, Params, Utils, Options, Configure, Environment
from Params import debug, error, trace, fatal

try:
	from xml.sax import make_parser 
	from xml.sax.handler import ContentHandler 
except:
	fatal('wscript_xml requires the Python xml modules (sax)!')


def Main(file):
	#fatal('wscript_xml is not implemented yet!')

	parser = make_parser()
	curHandler = XMLHandler()
	parser.setContentHandler(curHandler)
	parser.parse(open(file))

class XMLHandler(ContentHandler): 
	def __init__(self):
		pass
	def startElement(self, name, attrs): 
		print "startelement ", name
		if name == 'icondirent':
			return
		return
	def endElement(self, name): 
		return

