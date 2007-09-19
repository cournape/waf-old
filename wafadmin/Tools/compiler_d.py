#! /usr/bin/env python
# encoding: utf-8
# Carlos Rafael Giani, 2007 (dv)

import os, sys, imp, types
import optparse
import Utils, Action, Params, checks, Configure

def detect(conf):
	if Params.g_options.check_dmd_first:
		test_for_compiler = ['dmd', 'gdc']
	else:
		test_for_compiler = ['gdc', 'dmd']

	for d_compiler in test_for_compiler:
		conf.check_tool(d_compiler)
		if conf.env['D_COMPILER']
			conf.check_message("%s" % d_compiler, '', True)
			return
		conf.check_message("%s" % d_compiler, '', False)

def set_options(opt):
	d_compiler_opts = opt.add_option_group("D Compiler Options")
	try:
		d_compiler_opts.add_option('--check-dmd-first', action = "store_true", help = 'checks for the gdc compiler before dmd (default is the other way round)', dest = 'check_dmd_first',default = False)
	except optparse.OptionConflictError:
		# the g++ tool might have added that option already
		pass

	for d_compiler in ['gdc', 'dmd']:
		opt.tool_options('%s' % d_compiler, option_group=d_compiler_opts)

