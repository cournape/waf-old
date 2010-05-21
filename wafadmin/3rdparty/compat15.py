#! /usr/bin/env python

import Utils
import ConfigSet
ConfigSet.ConfigSet.copy = ConfigSet.ConfigSet.derive
ConfigSet.ConfigSet.set_variant = Utils.nada

import Build
Build.BuildContext.add_subdirs = Build.BuildContext.recurse

import Configure
Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse
Configure.conftest = Configure.conf

import Options
Options.OptionsContext.sub_options = Options.OptionsContext.recurse

from TaskGen import before, feature

@feature('d')
@before('apply_incpaths')
def old_importpaths(self):
	if getattr(self, 'importpaths', []):
		self.includes = self.importpaths

import Base
eld = Base.load_tool
def load_tool(*k, **kw):
	ret = eld(*k, **kw)
	return ret
	if 'set_options' in ret.__dict__:
		ret.options = ret.set_options
	if 'detect' in ret.__dict__ and not 'configure' in ret.__dict__:
		ret.configure = ret.detect
Base.load_tool = load_tool

rev = Base.load_module
def load_module(file_path):
	ret = rev(file_path)
	if 'set_options' in ret.__dict__:
		ret.options = ret.set_options
	return ret
Base.load_module = load_module

import Scripting
old = Scripting.set_main_module
def set_main_module(f):
	old(f)
	if 'set_options' in Base.g_module.__dict__:
		Base.g_module.options = Base.g_module.set_options
Scripting.set_main_module = set_main_module

import TaskGen
old_apply = TaskGen.task_gen.apply
def apply(self):
	self.features = self.to_list(self.features)
	if 'cstaticlib' in self.features:
		self.features.append('cstlib')
		self.features.remove('cstaticlib')
	old_apply(self)
TaskGen.task_gen.apply = apply

