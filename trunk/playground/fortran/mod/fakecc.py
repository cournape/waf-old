#! /usr/bin/env python
# encoding: utf-8
import re

import Utils, Task, TaskGen, Logs
from TaskGen import feature, before, after, extension
from Configure import conftest, conf
import Build

EXT = ".a"
IS_MODULE_R = re.compile('module ([a-z]*)')
USE_MODULE_R = re.compile('use ([a-z]*)')

@feature('fakecc')
def init(self):
	Utils.def_attrs(self, compiled_tasks=[])#inputs=[], outputs=[])

@extension(EXT)
def hook(self, node):
	task = self.create_task("fakecc")
	obj_ext = '_%d.o' % self.idx

	task.inputs = [node]
	task.outputs = [node.change_ext(obj_ext)]
	self.compiled_tasks.append(task)

	return task

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

Task.task_type_from_func('fakecc', func=yo,
	color='YELLOW', ext_in=EXT)

def detect(conf):
	pass

def set_options(opt):
	pass
