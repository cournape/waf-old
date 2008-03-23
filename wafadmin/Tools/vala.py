#! /usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

import os.path, shutil
import Action, Object, Runner, Utils, Params, Node
from Object import extension

EXT_VALA = ['.vala']

class ValacAction(Action.Action):
	def __init__(self):
		Action.Action.__init__(self, 'valac', color='GREEN')

	def get_str(self, task):
		"string to display to the user"
		env = task.env()
		src_str = " ".join([a.m_name for a in task.m_inputs])
		return "* %s : %s" % (self.m_name, src_str)

	def run(self, task):
		env = task.env()
		inputs = [a.srcpath(env) for a in task.m_inputs]
		valac = env['VALAC']
		vala_flags = env.get_flat('VALAFLAGS')
		top_src = Params.g_build.m_srcnode.abspath()
		top_bld = Params.g_build.m_srcnode.abspath(env)

		cmd = [valac, '-C', vala_flags]

		if task.threading:
			cmd.append('--thread')

		if task.output_type in ('shlib', 'staticlib', 'plugin'):
			cmd.append('--library ' + task.target)
			cmd.append('--basedir ' + top_src)
			cmd.append('-d ' + top_bld)
			#cmd.append('-d %s' % Params.g_build.m_srcnode.abspath(bld.env()))
			#cmd.append('-d %s' % Params.g_build.m_bldnode.bldpath(env))
		else:
			output_dir = task.m_outputs[0].bld_dir(env)
			cmd.append('-d %s' % output_dir)

		for vapi_dir in task.vapi_dirs:
			cmd.append('--vapidir=%s' % vapi_dir)

		for package in task.packages:
			cmd.append('--pkg %s' % package)

		cmd.append(" ".join(inputs))
		result = Runner.exec_command(" ".join(cmd))

		if task.output_type in ('shlib', 'staticlib', 'plugin'):
			# generate the .deps file
			if task.packages:
				filename = os.path.join(task.m_outputs[0].bld_dir(env), "%s.deps" % task.target)
				deps = open(filename, 'w')
				for package in task.packages:
					deps.write(package + '\n')
				deps.close()

			# handle vala 0.1.6 who doesn't honor --directory for the generated .vapi
			# waf is always run from the build directory
			try:
				src_vapi = os.path.join(top_bld, "..", "%s.vapi" % task.target)
				dst_vapi = task.m_outputs[0].bld_dir(env)
				shutil.move(src_vapi, dst_vapi)
			except IOError:
				pass
		return result

@extension(EXT_VALA)
def vala_file(self, node):
	valatask = self.create_task('valac')
	valatask.output_type = self.m_type
	valatask.packages = []
	valatask.vapi_dirs = []
	valatask.target = self.target
	valatask.threading = False

	if hasattr(self, 'packages'):
		valatask.packages = Utils.to_list(self.packages)

	if hasattr(self, 'vapi_dirs'):
		vapi_dirs = Utils.to_list(self.vapi_dirs)
		for vapi_dir in vapi_dirs:
			valatask.vapi_dirs.append(self.path.find_dir(vapi_dir).abspath())
			valatask.vapi_dirs.append(self.path.find_dir(vapi_dir).abspath(self.env))

	if hasattr(self, 'threading'):
		valatask.threading = self.threading

	input_nodes = []
	for source in self.to_list(self.source):
		if source.endswith(".vala"):
			input_nodes.append(self.path.find_source(source))
	valatask.set_inputs(input_nodes)

	output_nodes = []
	for node in input_nodes:
		output_nodes.append(node.change_ext('.c'))
		output_nodes.append(node.change_ext('.h'))

	if self.m_type != 'program':
		output_nodes.append(self.path.find_build('%s.vapi' % self.target))
		if valatask.packages:
			output_nodes.append(self.path.find_build('%s.deps' % self.target))
	valatask.set_outputs(output_nodes)

	for node in valatask.m_outputs:
		if node.m_name.endswith('.c'):
			self.allnodes.append(node)

# create our action here
ValacAction()

def detect(conf):
	valac = conf.find_program('valac', var='VALAC')
	if not valac: conf.fatal('Could not find the valac compiler anywhere')
	conf.env['VALAC'] = valac
	conf.env['VALAFLAGS'] = ''

