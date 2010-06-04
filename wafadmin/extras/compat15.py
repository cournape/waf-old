#! /usr/bin/env python
# encoding: utf-8

import sys

from wafadmin import ConfigSet, Logs, Options, Scripting, Task, Build, Configure, Node, Runner, TaskGen, Utils

# the following is to bring some compatibility with waf 1.5 "import wafadmin.Configure → import Configure"
sys.modules['Environment'] = ConfigSet
ConfigSet.Environment = ConfigSet.ConfigSet

sys.modules['Logs'] = Logs
sys.modules['Options'] = Options
sys.modules['Scripting'] = Scripting
sys.modules['Task'] = Task
sys.modules['Build'] = Build
sys.modules['Configure'] = Configure
sys.modules['Node'] = Node
sys.modules['Runner'] = Runner
sys.modules['TaskGen'] = TaskGen
sys.modules['Utils'] = Utils

ConfigSet.ConfigSet.copy = ConfigSet.ConfigSet.derive
ConfigSet.ConfigSet.set_variant = Utils.nada

Build.BuildContext.add_subdirs = Build.BuildContext.recurse
Build.BuildContext.name_to_obj = Build.BuildContext.get_tgen_by_name

Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse
Configure.conftest = Configure.conf

Options.OptionsContext.sub_options = Options.OptionsContext.recurse

Task.simple_task_type = Task.task_type_from_func = Task.task_factory

@TaskGen.feature('d')
@TaskGen.before('apply_incpaths')
def old_importpaths(self):
	if getattr(self, 'importpaths', []):
		self.includes = self.importpaths

from wafadmin import Context
eld = Context.load_tool
def load_tool(*k, **kw):
	ret = eld(*k, **kw)
	return ret
	if 'set_options' in ret.__dict__:
		ret.options = ret.set_options
	if 'detect' in ret.__dict__ and not 'configure' in ret.__dict__:
		ret.configure = ret.detect
Context.load_tool = load_tool

rev = Context.load_module
def load_module(file_path):
	ret = rev(file_path)
	if 'set_options' in ret.__dict__:
		ret.options = ret.set_options
	return ret
Context.load_module = load_module

old = Scripting.set_main_module
def set_main_module(f):
	old(f)
	if 'set_options' in Context.g_module.__dict__:
		Context.g_module.options = Context.g_module.set_options
Scripting.set_main_module = set_main_module

old_apply = TaskGen.task_gen.apply
def apply(self):
	self.features = self.to_list(self.features)
	if 'cstaticlib' in self.features:
		self.features.append('cstlib')
		self.features.remove('cstaticlib')
	old_apply(self)
TaskGen.task_gen.apply = apply

