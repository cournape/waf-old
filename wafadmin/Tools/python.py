#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2007 (ita)
# Gustavo Carneiro (gjc), 2007

"Python support"

import os, sys
import Object, Action, Utils, Params, Common, Utils
import pproc as subprocess

class pyobj(Object.genobj):
	s_default_ext = ['.py']
	def __init__(self, env=None):
		Object.genobj.__init__(self, 'other')
		self.pyopts = ''

		self.inst_var = 'PYTHONDIR'
		self.inst_dir = ''
		self.chmod = 0644

		self.env = env
		if not self.env: self.env = Params.g_build.env().copy()
		self.pyc = self.env['PYC']
		self.pyo = self.env['PYO']

	def apply(self):
		find_source_lst = self.path.find_source_lst

		envpyo = self.env.copy()
		envpyo['PYCMD']

		# first create the nodes corresponding to the sources
		for filename in self.to_list(self.source):
			node = find_source_lst(Utils.split_path(filename))
			if node is None:
				Params.fatal("Python source '%s' not found" % filename)

			base, ext = os.path.splitext(filename)
			#node = self.path.find_build(filename)
			if not ext in self.s_default_ext:
				fatal("unknown file "+filename)

			# Extract the extension and look for a handler hook.
			k = max(0, filename.rfind('.'))
			try:
				self.get_hook(filename[k:])(self, node)
				continue
			except TypeError:
				pass

			if self.pyc:
				task = self.create_task('pyc', self.env)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.pyc'))
			if self.pyo:
				task = self.create_task('pyo', self.env)
				task.set_inputs(node)
				task.set_outputs(node.change_ext('.pyo'))

	def install(self):
		for i in self.m_tasks:
			current = Params.g_build.m_curdirnode
			lst=[a.relpath_gen(current) for a in i.m_outputs]
			Common.install_files(self.inst_var, self.inst_dir, lst, chmod=self.chmod, env=self.env)
			lst=[a.relpath_gen(current) for a in i.m_inputs]
			Common.install_files(self.inst_var, self.inst_dir, lst, chmod=self.chmod, env=self.env)
			#self.install_results(self.inst_var, self.inst_dir, i)

def setup(bld):
	Object.register('py', pyobj)
	Action.simple_action('pyc', '${PYTHON} ${PYFLAGS} -c ${PYCMD} ${SRC} ${TGT}', color='BLUE', prio=50)
	Action.simple_action('pyo', '${PYTHON} ${PYFLAGS_OPT} -c ${PYCMD} ${SRC} ${TGT}', color='BLUE', prio=50)

def _get_python_variables(python_exe, variables, imports=['import sys']):
	"""Run a python interpreter and print some variables"""
	program = list(imports)
	program.append('')
	for v in variables:
		program.append("print repr(%s)" % v)
	proc = subprocess.Popen([python_exe, "-c", '\n'.join(program)],
				stdout=subprocess.PIPE)
	output = proc.communicate()[0].split("\n")
	if proc.returncode:
		if Params.g_verbose:
			Params.warning("Python program to extract python configuration variables failed:\n%s"
				       % '\n'.join(["line %03i: %s" % (lineno+1, line) for lineno, line in enumerate(program)]))
		raise ValueError
	return_values = []
	for s in output:
		s = s.strip()
		if not s:
			continue
		if s == 'None':
			return_values.append(None)
		elif s[0] == "'" and s[-1] == "'":
			return_values.append(s[1:-1])
		elif s[0].isdigit():
			return_values.append(int(s))
		else: break
	return return_values

def check_python_headers(conf):
	"""Check for headers and libraries necessary to extend or embed python.

	If successful, xxx_PYEXT and xxx_PYEMBED variables are defined in the
    enviroment (for uselib).  PYEXT should be used for compiling
    python extensions, while PYEMBED should be used by programs that
    need to embed a python interpreter.

	Note: this test requires that check_python_version was previously
	executed and successful."""

	try: import distutils
	except: return 0

	env = conf.env
	python = env['PYTHON']
	assert python, ("python is %r !" % (python,))

	try:
		## Get some python configuration variables using distutils
		v = 'prefix CC SYSLIBS SHLIBS LIBDIR LIBPL INCLUDEPY Py_ENABLE_SHARED'.split()
		(python_prefix, python_CC, python_SYSLIBS, python_SHLIBS,
		 python_LIBDIR, python_LIBPL, INCLUDEPY, Py_ENABLE_SHARED) = \
			_get_python_variables(python, ["get_config_var('%s')" % x for x in v],
					      ['from distutils.sysconfig import get_config_var'])
	except ValueError:
		conf.fatal("Python development headers not found (-v for details).")
	## Check for python libraries for embedding
	if python_SYSLIBS is not None:
		for lib in python_SYSLIBS.split():
			if lib.startswith('-l'):
				lib = lib[2:] # strip '-l'
			env.append_value('LIB_PYEMBED', lib)
	if python_SHLIBS is not None:
		for lib in python_SHLIBS.split():
			if lib.startswith('-l'):
				lib = lib[2:] # strip '-l'
			env.append_value('LIB_PYEMBED', lib)
	lib = conf.create_library_configurator()
	lib.name = 'python' + env['PYTHON_VERSION']
	lib.uselib = 'PYTHON'
	lib.code = '''
#ifdef __cplusplus
extern "C" {
#endif
 void Py_Initialize(void);
 void Py_Finalize(void);
#ifdef __cplusplus
}
#endif
int main(int argc, char *argv[]) { Py_Initialize(); Py_Finalize(); return 0; }
'''
	if python_LIBDIR is not None:
		lib.path = [python_LIBDIR]
		result = lib.run()
	else:
		result = 0

	## try again with -L$python_LIBPL (some systems don't install the python library in $prefix/lib)
	if not result:
		if python_LIBPL is not None:
			lib.path = [python_LIBPL]
			result = lib.run()
		else:
			result = 0

	## try again with -L$prefix/libs, and pythonXY name rather than pythonX.Y (win32)
	if not result:
		lib.path = [os.path.join(python_prefix, "libs")]
		lib.name = 'python' + env['PYTHON_VERSION'].replace('.', '')
		result = lib.run()

	if result:
		env['LIBPATH_PYEMBED'] = lib.path
		env.append_value('LIB_PYEMBED', lib.name)


	if sys.platform == 'win32' or (Py_ENABLE_SHARED is not None
					and sys.platform != 'darwin'):
		env['LIBPATH_PYEXT'] = env['LIBPATH_PYEMBED']
		env['LIB_PYEXT'] = env['LIB_PYEMBED']

	## We check that pythonX.Y-config exists, and if it exists we
	## use it to get only the includes, else fall back to distutils.
	python_config = conf.find_program(
		'python%s-config' % ('.'.join(env['PYTHON_VERSION'].split('.')[:2])),
		var='PYTHON_CONFIG')
	if python_config:
		includes = []
		for incstr in os.popen("%s %s --includes" % (python, python_config)).readline().strip().split():
			## strip the -I or /I
			if (incstr.startswith('-I')
			    or incstr.startswith('/I')):
				incstr = incstr[2:]
			## append include path, unless already given
			if incstr not in includes:
				includes.append(incstr)
		env['CPPPATH_PYEXT'] = list(includes)
		env['CPPPATH_PYEMBED'] = list(includes)
	else:
		env['CPPPATH_PYEXT'] = [INCLUDEPY]
		env['CPPPATH_PYEMBED'] = [INCLUDEPY]

	## Code using the Python API needs to be compiled with -fno-strict-aliasing
	if env['CC']:
		version = os.popen("%s --version" % env['CC']).readline()
		if '(GCC)' in version:
			env.append_value('CCFLAGS_PYEMBED', '-fno-strict-aliasing')
			env.append_value('CCFLAGS_PYEXT', '-fno-strict-aliasing')
	if env['CXX']:
		version = os.popen("%s --version" % env['CXX']).readline()
		if '(GCC)' in version:
			env.append_value('CXXFLAGS_PYEMBED', '-fno-strict-aliasing')
			env.append_value('CXXFLAGS_PYEXT', '-fno-strict-aliasing')

	## Test to see if it compiles
	header = conf.create_header_configurator()
	header.name = 'Python.h'
	header.define = 'HAVE_PYTHON_H'
	header.uselib = 'PYEXT'
	header.code = "#include <Python.h>\nint main(int argc, char *argv[]) { Py_Initialize(); Py_Finalize(); return 0; }"
	result = header.run()
	if not result:
		conf.fatal("Python development headers not found.")



def check_python_version(conf, minver=None):
	"""
	Check if the python interpreter is found matching a given minimum version.
	minver should be a tuple, eg. to check for python >= 2.4.2 pass (2,4,2) as minver.

	If successful, PYTHON_VERSION is defined as 'MAJOR.MINOR'
	(eg. '2.4') of the actual python version found, and PYTHONDIR is
	defined, pointing to the site-packages directory appropriate for
	this python version, where modules/packages/extensions should be
	installed.
	"""
	assert minver is None or isinstance(minver, tuple)
	python = conf.env['PYTHON']
	assert python, ("python is %r !" % (python,))

	## Get python version string
	proc = subprocess.Popen([python, "-c",
				 "import sys\nfor x in sys.version_info: print str(x)"],
				stdout=subprocess.PIPE)
	lines = proc.communicate()[0].split()
	assert len(lines) == 5, "found %i lines, expected 5: %r" % (len(lines), lines)
	pyver_tuple = (int(lines[0]), int(lines[1]), int(lines[2]), lines[3], int(lines[4]))

	## compare python version with the minimum required
	result = (minver is None) or (pyver_tuple >= minver)

	if result:
		## define useful environment variables
		pyver = '.'.join([str(x) for x in pyver_tuple[:2]])
		conf.env['PYTHON_VERSION'] = pyver

		if 'PYTHONDIR' in os.environ:
			pydir = os.environ['PYTHONDIR']
		else:
			if sys.platform == 'win32':
				(python_LIBDEST,) = \
						_get_python_variables(python, ["get_config_var('LIBDEST')"],
						['from distutils.sysconfig import get_config_var'])
			else:
				python_LIBDEST = None
			if python_LIBDEST is None:
				python_LIBDEST = os.path.join(conf.env['PREFIX'], "lib", "python" + pyver)
			pydir = os.path.join(python_LIBDEST, "site-packages")

		conf.define('PYTHONDIR', pydir)
		conf.env['PYTHONDIR'] = pydir

	## Feedback
	pyver_full = '.'.join(map(str, pyver_tuple[:3]))
	if minver is None:
		conf.check_message_custom('Python version', '', pyver_full)
	else:
		minver_str = '.'.join(map(str, minver))
		conf.check_message('Python version', ">= %s" % (minver_str,), result, option=pyver_full)

	if not result:
		conf.fatal("Python too old.")


def check_python_module(conf, module_name):
	"""
	Check if the selected python interpreter can import the given python module.
	"""
	result = not subprocess.Popen([conf.env['PYTHON'], "-c", "import %s" % module_name],
			   stderr=subprocess.PIPE, stdout=subprocess.PIPE).wait()
	conf.check_message('Python module', module_name, result)
	if not result:
		conf.fatal("Python module not found.")


def detect(conf):
	python = conf.find_program('python', var='PYTHON')
	if not python: return

	v = conf.env

	v['PYCMD'] = '"import sys, py_compile;py_compile.compile(sys.argv[1], sys.argv[2])"'
	v['PYFLAGS'] = ''
	v['PYFLAGS_OPT'] = '-O'

	v['PYC'] = getattr(Params.g_options, 'pyc', 1)
	v['PYO'] = getattr(Params.g_options, 'pyo', 1)

	v['pyext_INST_VAR'] = 'PYTHONDIR'
	v['pyext_INST_DIR'] = ''

	v['pyembed_INST_VAR'] = v['program_INST_VAR']
	v['pyembed_INST_DIR'] = v['program_INST_DIR']

	v['pyext_PREFIX'] = ''

	if sys.platform == 'win32':
		v['pyext_SUFFIX'] = '.pyd'

	# now a small difference
	v['pyext_USELIB'] = 'PYTHON PYEXT'
	v['pyembed_USELIB'] = 'PYTHON PYEMBED'

	conf.hook(check_python_version)
	conf.hook(check_python_headers)
	conf.hook(check_python_module)

def set_options(opt):
	opt.add_option('--nopyc', action = 'store_false', default = 1, help = 'no pyc files (configuration)', dest = 'pyc')
	opt.add_option('--nopyo', action = 'store_false', default = 1, help = 'no pyo files (configuration)', dest = 'pyo')

