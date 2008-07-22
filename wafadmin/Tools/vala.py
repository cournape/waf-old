#! /usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

import os.path, shutil
import Task, TaskGen, Runner, Utils, Params
from Params import error, debug, fatal, warning
from TaskGen import extension

from pproc import Popen, PIPE

EXT_VALA = ['.vala', '.gs']

class valac(Task.Task):
	def __init__(self, *args, **kwargs):
		Task.Task.__init__(self, *args, **kwargs)
		self.prio = 80

	def get_str(self):
		"string to display to the user"
		env = self.env()
		src_str = " ".join([a.nice_path(env) for a in self.m_inputs])
		return "%s: %s\n" % (self.__class__.__name__, src_str)

	def run(self):
		task = self # TODO cleanup
		env = task.env()
		inputs = [a.srcpath(env) for a in task.m_inputs]
		valac = env['VALAC']
		vala_flags = env.get_flat('VALAFLAGS')
		top_src = Params.g_build.m_srcnode.abspath()
		top_bld = Params.g_build.m_srcnode.abspath(env)

		if env['VALAC_VERSION'] > (0, 1, 6):
			cmd = [valac, '-C', '--quiet', vala_flags]
		else:
			cmd = [valac, '-C', vala_flags]

		if task.threading:
			cmd.append('--thread')

		if task.output_type in ('shlib', 'staticlib'):
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

		if task.output_type in ('shlib', 'staticlib'):
			# generate the .deps file
			if task.packages:
				filename = os.path.join(task.m_outputs[0].bld_dir(env), "%s.deps" % task.target)
				deps = open(filename, 'w')
				for package in task.packages:
					deps.write(package + '\n')
				deps.close()

			# handle vala 0.1.6 who doesn't honor --directory for the generated .vapi
			try:
				src_vapi = os.path.join(top_bld, "..", "%s.vapi" % task.target)
				dst_vapi = task.m_outputs[0].bld_dir(env)
				shutil.move(src_vapi, dst_vapi)
			except IOError:
				pass
			# handle vala >= 0.1.7 who has a weid definition for --directory
			try:
				src_vapi = os.path.join(top_bld, "%s.vapi" % task.target)
				dst_vapi = task.m_outputs[0].bld_dir(env)
				shutil.move(src_vapi, dst_vapi)
			except IOError:
				pass

			# handle vala >= 0.2.0 who doesn't honor --directory for the generated .gidl
			try:
				src_gidl = os.path.join(top_bld, "%s.gidl" % task.target)
				dst_gidl = task.m_outputs[0].bld_dir(env)
				shutil.move(src_gidl, dst_gidl)
			except IOError:
				pass
		return result
Task.g_task_types["valac"] = valac

@extension(EXT_VALA)
def vala_file(self, node):
	valatask = getattr(self, "valatask", None)
	# there is only one vala task and it compiles all vala files .. :-/
	if not valatask:
		valatask = self.create_task('valac')
		self.valatask = valatask
		valatask.output_type = self.m_type
		valatask.packages = []
		valatask.vapi_dirs = []
		valatask.target = self.target
		valatask.threading = False

		packages = Utils.to_list(getattr(self, 'packages', []))
		vapi_dirs = Utils.to_list(getattr(self, 'vapi_dirs', []))

		if hasattr(self, 'uselib_local'):
			local_packages = self.to_list(self.uselib_local)
			seen = []
			while local_packages:
				package = local_packages.pop()
				if package in seen:
					continue
				seen.append(package)

				# check if the package exists
				package_obj = TaskGen.name_to_obj(package)
				if not package_obj:
					fatal('object not found in uselib_local: obj %s package %s' % (self.name, package))

				package_name = package_obj.target
				package_node = package_obj.path
				package_dir = package_node.relpath_gen(self.path)

				for task in package_obj.m_tasks:
					for output in task.m_outputs:
						if output.m_name == package_name + ".vapi":
							if package_name not in packages:
								packages.append(package_name)
								valatask.m_deps_nodes.append(output)
							if package_dir not in vapi_dirs:
								vapi_dirs.append(package_dir)

				if hasattr(package_obj, 'uselib_local'):
					lst = self.to_list(package_obj.uselib_local)
					lst.reverse()
					local_packages = [pkg for pkg in lst if pkg not in seen] + local_packages

		valatask.packages = packages
		for vapi_dir in vapi_dirs:
			try:
				valatask.vapi_dirs.append(self.path.find_dir(vapi_dir).abspath())
				valatask.vapi_dirs.append(self.path.find_dir(vapi_dir).abspath(self.env))
			except AttributeError:
				Params.warning("Unable to locate Vala API directory: '%s'" % vapi_dir)

		if hasattr(self, 'threading'):
			valatask.threading = self.threading
			self.uselib = self.to_list(self.uselib)
			if not 'GTHREAD' in self.uselib:
				self.uselib.append('GTHREAD')

	env = valatask.env()

	output_nodes = []
	output_nodes.append(node.change_ext('.c'))
	output_nodes.append(node.change_ext('.h'))
	if self.m_type != 'program':
		output_nodes.append(self.path.find_build('%s.vapi' % self.target))
		if env['VALAC_VERSION'] > (0, 1, 7):
			output_nodes.append(self.path.find_build('%s.gidl' % self.target))
		if valatask.packages:
			output_nodes.append(self.path.find_build('%s.deps' % self.target))

	valatask.m_inputs.append(node)
	valatask.m_outputs.extend(output_nodes)
	self.allnodes.append(node.change_ext('.c'))

def detect(conf):
	min_version = (0, 1, 6)
	min_version_str = "%d.%d.%d" % min_version

	valac = conf.find_program('valac', var='VALAC')
	if not valac:
		conf.fatal("valac not found")
		return

	if not conf.env["HAVE_GTHREAD"]:
		conf.check_pkg('gthread-2.0', destvar='GTHREAD', mandatory=False)

	try:
		output = Popen([valac, "--version"], stdout=PIPE).communicate()[0]
		version = output.split(' ', 1)[-1].strip().split(".")
		version = [int(atom) for atom in version]
		valac_version = tuple(version)
	except Exception:
		valac_version = (0, 0, 0)

	conf.check_message('program version',
			'valac >= ' + min_version_str,
			valac_version >= min_version,
			"%d.%d.%d" % valac_version)

	if valac_version < min_version:
		conf.fatal("valac version too old to be used with this tool")
		return

	conf.env['VALAC_VERSION'] = valac_version
	conf.env['VALAFLAGS'] = ''
