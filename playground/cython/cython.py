#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2010

"Cython"

import re
import TaskGen

re_cyt = re.compile('import\\s(\\w+)\\s*$', re.M)

def cscan(self):

	txt = self.inputs[0].read(self.env)
	mods = []
	for m in re_cyt.finditer(txt):
		mods.append(m.group(1))

	incs = getattr(self.generator, 'cython_includes', [])
	incs = [self.generator.path.find_dir(x) for x in incs]
	incs.append(self.inputs[0].parent)

	found = []
	missing = []
	for x in mods:
		for y in incs:
			k = y.find_resource(x + '.pxd')
			if k:
				found.append(k)
				break
		else:
			missing.append(x)

	return (found, missing)

TaskGen.declare_chain(name='cython', rule='${CYTHON} ${CYTHONFLAGS} ${SRC} -o ${TGT}', ext_in=['.pyx'], ext_out=['.c'], scan=cscan)

def detect(conf):
	conf.find_program('cython', var='CYTHON', mandatory=True)

