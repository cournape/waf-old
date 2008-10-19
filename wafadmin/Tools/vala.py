#!/usr/bin/env python
# encoding: utf-8
# Ali Sabil, 2007

import os.path, shutil
import Task, Runner, Utils, Logs, Build, Node
from TaskGen import extension

EXT_VALA = ['.vala', '.gs']

class valac_task(Task.Task):

	vars = ("VALAFLAGS")
	before = ("cc", "cxx")

	def __init__(self, *args, **kwargs):
		Task.Task.__init__(self, *args, **kwargs)

	def get_str(self):
		src_str = " ".join([a.name for a in self.inputs])
		return "%s: %s\n" % (self.__class__.__name__, src_str)

	def run(self):
		task = self # TODO cleanup
		env = task.env
		inputs = [a.srcpath(env) for a in task.inputs]
		valac = env['VALAC']
		vala_flags = env.get_flat('VALAFLAGS')
		top_src = self.generator.bld.srcnode.abspath()
		top_bld = self.generator.bld.srcnode.abspath(env)

		if env['VALAC_VERSION'] > (0, 1, 6):
			cmd = [valac, '-C', '--quiet', vala_flags]
		else:
			cmd = [valac, '-C', vala_flags]

		if task.threading:
			cmd.append('--thread')

		features = self.generator.features

		if 'cshlib' in features or 'cstaticlib' in features:
			cmd.append('--library ' + task.target)
			cmd.append('--basedir ' + top_src)
			cmd.append('-d ' + top_bld)
		else:
			output_dir = task.outputs[0].bld_dir(env)
			cmd.append('-d %s' % output_dir)

		for vapi_dir in task.vapi_dirs:
			cmd.append('--vapidir=%s' % vapi_dir)

		for package in task.packages:
			cmd.append('--pkg %s' % package)

		cmd.append(" ".join(inputs))
		result = self.generator.bld.exec_command(" ".join(cmd))

		if 'cshlib' in features or 'cstaticlib' in features:
			# generate the .deps file
			if task.packages:
				filename = os.path.join(task.outputs[0].bld_dir(env), "%s.deps" % task.target)
				deps = open(filename, 'w')
				for package in task.packages:
					deps.write(package + '\n')
				deps.close()

			# handle vala 0.1.6 who doesn't honor --directory for the generated .vapi
			try:
				src_vapi = os.path.join(top_bld, "..", "%s.vapi" % task.target)
				dst_vapi = task.outputs[0].bld_dir(env)
				shutil.move(src_vapi, dst_vapi)
			except IOError:
				pass
			# handle vala >= 0.1.7 who has a weid definition for --directory
			try:
				src_vapi = os.path.join(top_bld, "%s.vapi" % task.target)
				dst_vapi = task.outputs[0].bld_dir(env)
				shutil.move(src_vapi, dst_vapi)
			except IOError:
				pass

			# handle vala >= 0.2.0 who doesn't honor --directory for the generated .gidl
			try:
				src_gidl = os.path.join(top_bld, "%s.gidl" % task.target)
				dst_gidl = task.outputs[0].bld_dir(env)
				shutil.move(src_gidl, dst_gidl)
			except IOError:
				pass
			# handle vala >= 0.3.6 who doesn't honor --directory for the generated .gir
			try:
				src_gir = os.path.join(top_bld, "%s.gir" % task.target)
				dst_gir = task.outputs[0].bld_dir(env)
				shutil.move(src_gir, dst_gir)
			except IOError:
				pass
		return result

	def install(self):
		bld = self.generator.bld
		features = self.generator.features

		if self.attr("install_path") and ("cshlib" in features or "cstaticlib" in features):
			headers_list = [o for o in self.outputs if o.suffix() == ".h"]
			vapi_list = [o for o in self.outputs if (o.suffix() in (".vapi", ".deps"))]

			for header in headers_list:
				top_src = self.generator.bld.srcnode
				package = self.env['PACKAGE']
				try:
					api_version = Utils.g_module.API_VERSION
				except AttributeError:
					version = Utils.g_module.VERSION.split(".")
					if version[0] == "0":
						api_version = "0." + version[1]
					else:
						api_version = version[0] + ".0"
				install_path = "${INCLUDEDIR}/%s-%s/%s" % (package, api_version, header.relpath_gen(top_src))
				bld.install_as(install_path, header.abspath(self.env), self.env)
			for vapi in vapi_list:
				bld.install_files("${DATAROOTDIR}/vala/vapi", vapi.abspath(self.env), self.env)

@extension(EXT_VALA)
def vala_file(self, node):
	valatask = getattr(self, "valatask", None)
	# there is only one vala task and it compiles all vala files .. :-/
	if not valatask:
		valatask = self.create_task('valac')
		self.valatask = valatask
		valatask.packages = []
		valatask.vapi_dirs = []
		valatask.target = self.target
		valatask.threading = False
		valatask.install_path = self.install_path

		packages = Utils.to_list(getattr(self, 'packages', []))
		vapi_dirs = Utils.to_list(getattr(self, 'vapi_dirs', []))

		if hasattr(self, 'uselib_local'):
			local_packages = Utils.to_list(self.uselib_local)
			seen = []
			while len(local_packages) > 0:
				package = local_packages.pop()
				if package in seen:
					continue
				seen.append(package)

				# check if the package exists
				package_obj = self.name_to_obj(package)
				if not package_obj:
					raise Utils.WafError("object '%s' was not found in uselib_local (required by '%s')" % (package, self.name))

				package_name = package_obj.target
				package_node = package_obj.path
				package_dir = package_node.relpath_gen(self.path)

				for task in package_obj.tasks:
					for output in task.outputs:
						if output.name == package_name + ".vapi":
							if package_name not in packages:
								packages.append(package_name)
								valatask.set_run_after(task)
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

	env = valatask.env

	output_nodes = []

	c_node = node.change_ext('.c')
	output_nodes.append(c_node)
	self.allnodes.append(c_node)

	output_nodes.append(node.change_ext('.h'))

	if not 'cprogram' in self.features:
		output_nodes.append(self.path.find_or_declare('%s.vapi' % self.target))
		if env['VALAC_VERSION'] > (0, 3, 5):
			output_nodes.append(self.path.find_or_declare('%s.gir' % self.target))
		elif env['VALAC_VERSION'] > (0, 1, 7):
			output_nodes.append(self.path.find_or_declare('%s.gidl' % self.target))
		if valatask.packages:
			output_nodes.append(self.path.find_or_declare('%s.deps' % self.target))

	valatask.inputs.append(node)
	valatask.outputs.extend(output_nodes)

def detect(conf):
	min_version = (0, 1, 6)
	min_version_str = "%d.%d.%d" % min_version

	valac = conf.find_program('valac', var='VALAC')
	if not valac:
		conf.fatal("valac not found")
		return

	if not conf.env["HAVE_GTHREAD"]:
		conf.check_cfg(package='gthread-2.0', uselib_store='GTHREAD', args='--cflags --libs')

	try:
		output = Utils.cmd_output(valac + " --version", silent=True)
		version = output.split(' ', 1)[-1].strip().split(".")
		version = [int(x) for x in version]
		valac_version = tuple(version)
	except Exception:
		valac_version = (0, 0, 0)

	conf.check_message('program version',
			'valac >= ' + min_version_str,
			valac_version >= min_version,
			"%d.%d.%d" % valac_version)

	conf.check_tool('gnu_dirs')

	if valac_version < min_version:
		conf.fatal("valac version too old to be used with this tool")
		return

	conf.env['VALAC_VERSION'] = valac_version
	conf.env['VALAFLAGS'] = ''

