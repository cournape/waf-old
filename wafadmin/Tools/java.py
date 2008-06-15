#!/usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006-2008 (ita)

"""
Java support

Javac is one of the few compilers that behaves very badly:
* it outputs files where it wants to (-d is only for the package root)
* it recompiles files silently behind your back
* it outputs an undefined amount of files (inner classes)

Fortunately, the convention makes it possible to use th build dir without
too many problems for the moment

Inner classes must be located and cleaned when a problem arise,
for the moment waf does not track the production of inner classes.

Adding all the files to a task and executing it if any of the input files
change is only annoying for the compilation times
"""

import os, re
from Configure import conf
import TaskGen, Task, Utils, Params

class java_taskgen(TaskGen.task_gen):
	s_default_ext = ['.java']
	def __init__(self, *k):
		TaskGen.task_gen.__init__(self, *k)

		self.jarname = ''
		self.jaropts = ''
		self.classpath = ''
		self.source_root = '.'

		# Jar manifest attributes
		# TODO: Add manifest creation
		self.jar_mf_attributes = {}
		self.jar_mf_classpath = []

	def apply(self):
		nodes_lst = []

		if not self.classpath:
			if not self.env['CLASSPATH']:
				self.env['CLASSPATH'] = '..' + os.pathsep + '.'
		else:
			self.env['CLASSPATH'] = self.classpath

		find_resource_lst = self.path.find_resource_lst

		re_foo = re.compile(self.source)

		source_root_node = self.path.find_dir(self.source_root)

		src_nodes = []
		bld_nodes = []

		prefix_path = source_root_node.abspath()
		for (root, dirs, filenames) in os.walk(source_root_node.abspath()):
			for x in filenames:
				file = root + '/' + x
				file = file.replace(prefix_path, '')
				if file.startswith('/'):
					file = file[1:]

				if re_foo.search(file) > -1:
					node = source_root_node.find_resource(file)
					src_nodes.append(node)

					node2 = node.change_ext(".class")
					bld_nodes.append(node2)

		self.env['OUTDIR'] = source_root_node.abspath(self.env)

		tsk = self.create_task('javac', self.env)
		tsk.set_inputs(src_nodes)
		tsk.set_outputs(bld_nodes)

		if self.jarname:
			tsk = self.create_task('jar_create', self.env)
			tsk.set_inputs(bld_nodes)
			tsk.set_outputs(self.path.find_build_lst(Utils.split_path(self.jarname)))

			if not self.env['JAROPTS']:
				if self.jaropts:
					self.env['JAROPTS'] = self.jaropts
				else:
					dirs = '/'
					self.env['JAROPTS'] = '-C %s %s' % (self.env['OUTDIR'], dirs)

Task.simple_task_type('javac', '${JAVAC} -classpath ${CLASSPATH} -d ${OUTDIR} ${SRC}', color='BLUE', before="jar_create")
Task.simple_task_type('jar_create', '${JAR} ${JARCREATE} ${TGT} ${JAROPTS}', color='GREEN')

def detect(conf):
	# If JAVA_PATH is set, we prepend it to the path list
	java_path = os.environ['PATH'].split(os.pathsep)
	v = conf.env

	if os.environ.has_key('JAVA_HOME'):
		java_path = [os.path.join(os.environ['JAVA_HOME'], 'bin')] + java_path
		conf.env['JAVA_HOME'] = os.environ['JAVA_HOME']

	conf.find_program('javac', var='JAVAC', path_list=java_path)
	conf.find_program('java', var='JAVA', path_list=java_path)
	conf.find_program('jar', var='JAR', path_list=java_path)
	v['JAVA_EXT'] = ['.java']

	if os.environ.has_key('CLASSPATH'):
		v['CLASSPATH'] = os.environ['CLASSPATH']

	if not v['JAR']: conf.fatal('jar is required for making java packages')
	if not v['JAVAC']: conf.fatal('javac is required for compiling java classes')
	v['JARCREATE'] = 'cf' # can use cvf

@conf
def check_java_class(conf, classname, with_classpath=None):
	"""
	Check if specified java class is installed.
	"""

	class_check_source = """
public class Test {
	public static void main(String[] argv) {
		Class lib;
		if (argv.length < 1) {
			System.err.println("Missing argument");
			System.exit(77);
		}
		try {
			lib = Class.forName(argv[0]);
		} catch (ClassNotFoundException e) {
			System.err.println("ClassNotFoundException");
			System.exit(1);
		}
		lib = null;
		System.exit(0);
	}
}
"""
	import shutil

	javatestdir = '.waf-javatest'

	classpath = javatestdir
	if conf.env['CLASSPATH']:
		classpath += os.pathsep + conf.env['CLASSPATH']
	if isinstance(with_classpath, str):
		classpath += os.pathsep + with_classpath

	shutil.rmtree(javatestdir, True)
	os.mkdir(javatestdir)

	java_file = open(os.path.join(javatestdir, 'Test.java'), 'w')
	java_file.write(class_check_source)
	java_file.close()

	# Compile the source
	os.popen(conf.env['JAVAC'] + ' ' + os.path.join(javatestdir, 'Test.java'))

	(jstdin, jstdout, jstderr) = os.popen3(conf.env['JAVA'] + ' -cp ' + classpath + ' Test ' + classname)

	found = not bool(jstderr.read())
	conf.check_message('Java class %s' % classname, "", found)

	shutil.rmtree(javatestdir, True)

	return found

