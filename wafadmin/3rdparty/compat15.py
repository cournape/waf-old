#! /usr/bin/env python

import Build
Build.BuildContext.add_subdirs = Build.BuildContext.recurse

import Configure
Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse
Configure.conftest = Configure.conf

from TaskGen import before, feature

@feature('d')
@before('apply_incpaths')
def old_importpaths(self):
	if getattr(self, 'importpaths', []):
		self.includes = self.importpaths

import Base
old = Base.load_tool
def load_tool(*k, **kw):
	ret = old(*k, **kw)
	if 'options' in ret.__dict__:
		ret.set_options = ret.options
Base.load_tool = load_tool

import Scripting
old = Scripting.set_main_module
def set_main_module(f):
	old(f)
	if not 'set_options' in Base.g_module.__dict__:
		Base.g_module.set_options = Base.g_module.options

