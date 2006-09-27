#! /usr/bin/env python
# encoding: utf-8
# Oscar Blumberg 2006 (nael)
# Matthias Jahn <jahn.matthias@freenet.de>

"""Depends on python gamin and on gamin demon"""

import os, sys, select, errno
try:
	import gamin
	support = True
except:
	support = False

class GaminAdaptor:
	def __init__( self, eventHandler ):
		""" """
		self.__gamin = gamin.WatchMonitor()
		self.__eventHandler = eventHandler # callBack function
		self.__watchHandler = {} # {name : famId}
	
	def __del__( self ):
		""""""
		if self.__gamin:
			for handle in self.__watchHandler.keys():
				self.stop_watch( handle )
			self.__gamin.disconnect() 
			self.__gamin = None
	
	def __check_gamin(self):
		if self.__gamin == None:
			raise "gamin not init"		
	
	def watch_directory( self, name, idxName ):
		""""""
		self.__check_gamin()
		if self.__watchHandler.has_key( name ):
			raise "dir allready watched"
		# set famId
		self.__watchHandler[name] = self.__gamin.watch_directory( name, self.__eventHandler, idxName )
		return(self.__watchHandler[name])
	
	def watch_file( self, name, idxName ):
		""""""
		self.__check_gamin()
		if self.__watchHandler.has_key( name ):
			raise "file allready watched"
		# set famId
		self.__watchHandler[name] = self.__gamin.watch_directory( name, self.__eventHandler, idxName )
		return(self.__watchHandler[name])
	
	def stop_watch( self, name ):
		""""""
		self.__check_gamin()
		if self.__watchHandler.has_key( name ):
			self.__gamin.stop_watch(name)
			del self.__watchHandler[name]
		return None
			
	def wait_for_event( self ):
		""""""
		self.__check_gamin()
		try:
			select.select( [self.__gamin.get_fd()], [], [] )
		except select.error, er:
			errnumber, strerr = er
			if errnumber != errno.EINTR:
				raise strerr
	
	def event_pending( self ):
		""""""
		self.__check_gamin()
		return self.__gamin.event_pending()
	
	def handle_events( self ):
		""""""
		self.__check_gamin()
		self.__gamin.handle_events()

