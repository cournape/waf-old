#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

"Java support"

import os
import Object, Action, Utils

class javaobj(Object.genobj):
	s_default_ext = ['.java']
	def __init__(self):
		Object.genobj.__init__(self, 'other')

		self.jarname = ''
		self.jaropts = ''
		self.classpath = ''

	def apply(self):
		nodes_lst = []

		if not self.classpath:
			self.classpath = self.env['CLASSPATH'] =  '..' + os.pathsep + '.'
		else:
			self.env['CLASSPATH'] = self.classpath


		find_source_lst = self.path.find_source_lst

		# first create the nodes corresponding to the sources
		for filename in self.to_list(self.source):

			node = find_source_lst(Utils.split_path(filename))

			base, ext = os.path.splitext(filename)
			#node = self.path.find_build(filename)
			if not ext in self.s_default_ext:
				fatal("unknown file "+filename)

			task = self.create_task('javac', self.env, 10)
			task.set_inputs(node)
			task.set_outputs(node.change_ext('.class'))

			nodes_lst.append(task.m_outputs[0])

		if self.jarname:
			task = self.create_task('jar_create', self.env, 50)
			task.set_inputs(nodes_lst)
			task.set_outputs(self.path.find_build_lst(Utils.split_path(self.jarname)))

			if not self.env['JAROPTS']:
				if self.jaropts:
					self.env['JAROPTS'] = self.jaropts
				else:
					self.env.append_unique('JAROPTS', '-C %s .' % self.path.bldpath(self.env))

def setup(env):
	Object.register('java', javaobj)
	Action.simple_action('javac', '${JAVAC} -classpath ${CLASSPATH} -d ${TGT[0].bld_dir(env)} ${SRC}', color='BLUE')
	Action.simple_action('jar_create', '${JAR} cvf ${TGT} ${JAROPTS}', color='GREEN')

def detect(conf):
	# If JAVA_PATH is set, we prepend it to the path list
	java_path = os.environ['PATH'].split(os.pathsep)
	if os.environ.has_key('JAVA_HOME'):
		java_path = [os.path.join(os.environ['JAVA_HOME'], 'bin')] + java_path
		conf.env['JAVA_HOME'] = os.environ['JAVA_HOME']

	conf.find_program('javac', var='JAVAC', path_list=java_path)
	conf.find_program('java', var='JAVA', path_list=java_path)
	conf.find_program('jar', var='JAR', path_list=java_path)
	conf.env['JAVA_EXT'] = ['.java']

	conf.hook(check_java_class)

def check_java_class(conf, classname):
	"""
	Check if specified java class is installed.
	"""

	class_check_source = """
public class Test
{
        public static void main( String[] argv ) {
                Class lib;
                if (argv.length < 1) {
                        System.err.println ("Missing argument");
                        System.exit (77);
                } try {
                        lib = Class.forName (argv[0]);
                } catch (ClassNotFoundException e) {
			System.err.println ("ClassNotFoundException");
                        System.exit (1);
                }
                lib = null;
                System.exit (0);
        }
}"""
	import shutil

	javatestdir = '.waf-javatest'

	shutil.rmtree(javatestdir, True)
	os.mkdir(javatestdir)

	java_file = open(os.path.join(javatestdir, 'Test.java'), 'w')
	java_file.write(class_check_source)
	java_file.close()

	classpath = javatestdir
	if conf.env['CLASSPATH']:
		classpath += os.pathsep + conf.env['CLASSPATH']

	os.popen(conf.env['JAVAC'] + ' ' + os.path.join(javatestdir, 'Test.java'))
	(jstdin, jstdout, jstderr) = os.popen3(conf.env['JAVA'] + ' -cp ' + classpath + ' Test ' + classname)

	found = not bool(jstderr.read())
	conf.check_message('Java class %s' % classname, "", found)

	shutil.rmtree(javatestdir, True)
