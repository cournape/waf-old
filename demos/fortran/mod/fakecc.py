#! /usr/bin/env python
# encoding: utf-8
# DC 2008
# Thomas Nagy 2010 (ita)

import re

from waflib import Utils, Task, TaskGen, Logs
from TaskGen import feature, before, after, extension

IS_MODULE_R = re.compile('module ([a-z]*)')
USE_MODULE_R = re.compile('use ([a-z]*)')

@extension('.a')
def hook(self, node):
	self.create_compiled_task('fakecc', node)

def ismodule(file):
    deps = []
    a = open(file, 'r')
    try:
        for l in a.readlines():
            m = IS_MODULE_R.match(l)
            if m:
                deps.append(m.group(1) + '.mod')
    finally:
        a.close()

    return deps

def usemodule(file):
    deps = []
    a = open(file, 'r')
    try:
        for l in a.readlines():
            m = USE_MODULE_R.match(l)
            if m:
                deps.append(m.group(1) + '.mod')
    finally:
        a.close()

    return deps

def compile(src, tgt):
    t = open(tgt, 'w')
    try:
        t.write('compiled')
    finally:
        t.close()

    m = ismodule(src)
    if m:
	print "%s declares module %s" % (src, m[0])
        t2 = open(m[0], 'w')
        try:
            t2.write('module compiled')
        finally:
            t2.close()

class fakecc(Task.Task):
	color = 'YELLOW'
	def yo(task):
		env = task.env
		cmd = []
		if not len(task.outputs) == len(task.inputs) == 1:
			pass

		src = task.inputs[0].srcpath(env)
		tgt = task.outputs[0].bldpath(env)

		bnodes = task.outputs
		m = usemodule(src)
		if m:
			print "%s requires module %s" % (src, m[0])
			print task.inputs[0].parent.exclusive_build_node(m[0])
			#bnodes.append(task.generator.bld.bldnode.exclusive_build_node(m[0]))

		compile(src, tgt)

