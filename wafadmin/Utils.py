#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import imp, types
import Params

g_trace=0
g_debug=0
g_error=0

def waf_version(mini="0.0.1", maxi="100.0.0"):
	"throws an exception if the waf version is not the one desired"
	min_lst = map(int, mini.split('.'))
	max_lst = map(int, maxi.split('.'))
	waf_lst = map(int, Params.g_version.split('.'))

	mm = min(len(min_lst), len(waf_lst))
	for (a, b) in zip(min_lst[:mm], waf_lst[:mm]):
		if a<b:
			break
		if a>b:
			Params.fatal("waf version should be at least %s (%s found)" % (mini, Params.g_version))

	mm = min(len(max_lst), len(waf_lst))
	for (a, b) in zip(max_lst[:mm], waf_lst[:mm]):
		if a>b:
			break
		if a<b:
			Params.fatal("waf version should be at most %s (%s found)" % (maxi, Params.g_version))

def error(msg):
	Params.niceprint(msg, 'ERROR', 'Configuration')

def reset():
	import Params, Task, preproc, Scripting, Object
	Params.g_build = None
	Task.g_tasks = Task.TaskManager()
	preproc.parse_cache = {}
	Scripting.g_inroot = 1
	Object.g_allobjs = []

def to_list(sth):
	if type(sth) is types.ListType: return sth
	else: return [sth]

def options(**kwargs):
	pass

g_loaded_modules={}
"index modules by absolute path"

g_module=None
"the main module is special"

def load_module(file_path, name='wscript'):
	"this function requires an absolute path"
	try: return g_loaded_modules[file_path]
	except: pass

	module = imp.new_module(name)

	try:
		file = open(file_path, 'r')
	except:
		Params.fatal('The file %s could not be opened!' % file_path)

	exec file in module.__dict__
	if file: file.close()

	g_loaded_modules[file_path] = module

	return module

def set_main_module(file_path):
	"Load custom options, if defined"
	global g_module
	g_module = load_module(file_path, 'wscript_main')

	# remark: to register the module globally, use the following:
	# sys.modules['wscript_main'] = g_module

def fetch_options(file_path):
	"Load custom options, if defined"
	import Options
	file = open(file_path, 'r')
	name = 'wscript'
	desc = ('', 'U', 1)

	module = imp.load_module(file_path, file, name, desc)
	try:
		Options.g_custom_options.append(module.set_options)
	finally:
		if file: file.close()

def to_hashtable(s):
	tbl = {}
	lst = s.split('\n')
	for line in lst:
		if not line: continue
		mems = line.split('=')
		tbl[mems[0]] = mems[1]
	return tbl

def copyobj(obj):
	cp = obj.__class__()
	for at in obj.__dict__.keys():
		setattr(cp, at, getattr(obj, at))
	return cp

