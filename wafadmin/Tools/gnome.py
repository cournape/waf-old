#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

import os
import Object, Action

# translations
class gnome_translations(Object.genobj):
	def __init__(self, appname):
		Object.genobj.__init__(self, 'other')
		self.m_tasks=[]
		self.m_appname = appname
	def apply(self):
		for file in self.m_current_path.m_files:
			try:
				base, ext = os.path.splitext(file.m_name)
				if ext != '.po': continue

				task = self.create_task('po', self.env, 2)
				task.set_inputs(file)
				task.set_outputs(file.change_ext('.gmo'))
				self.m_tasks.append(task)
			except: pass
	def install(self):
		destfilename = self.m_appname+'.mo'

		current = Params.g_build.m_curdirnode
		for file in self.m_current_path.m_files:
			lang, ext = os.path.splitext(file.m_name)
			if ext != '.po': continue

			node = self.m_current_path.find_node( (lang+'.gmo').split('/') )
			orig = node.relpath_gen(current)

			destfile = os.sep.join([lang, 'LC_MESSAGES', destfilename])
			Common.install_as('GNOME_LOCALE', destfile, orig, self.env)


def setup(env):
	Action.simple_action('po', '${POCOM} -o ${TGT} ${SRC}', color='BLUE')
	Object.register('gnome_translations', gnome_translations)

def detect(env):
	# nothing to do yet
	return 1

