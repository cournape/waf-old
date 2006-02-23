#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2006 (ita)

class kdeinitobj(kdeobj):
	def __init__(self, senv=None):
		if not self.env: self.env = env
		kdeobj.__init__(self, 'shlib', senv)

		if env['WINDOWS']:
			self.type = 'program'
		else:
			self.binary = kdeobj('program', senv)
			self.binary.libprefix = ''
			self.kdeinitlib = kdeobj('shlib', senv)
			self.kdeinitlib.libprefix = ''

	def execute(self):
		if self.executed: return

		if env['WINDOWS']:
			SConsEnvironment.kdeobj.execute(self)
			return

		# 'dcopserver' is the real one
		self.binary.target   = self.target
		# 'libkdeinit_dcopserver'
		self.kdeinitlib.target = 'libkdeinit_' + self.target
		# 'dcopserver' (lib)

		self.kdeinitlib.libs     = self.libs
		self.kdeinitlib.libpaths = self.libpaths
		self.kdeinitlib.uselib   = self.uselib
		self.kdeinitlib.source   = self.source
		self.kdeinitlib.includes = self.includes
		self.kdeinitlib.execute()

		self.binary.uselib       = self.uselib
		self.binary.libs         = [self.kdeinitlib.target + ".la"] + self.orenv.make_list(self.libs)
		#self.binary.libdirs      = "build/dcop"
		self.binary.libpaths     = self.libpaths
		self.binary.includes     = self.includes
		env.Depends(self.binary.target, self.kdeinitlib.target + ".la")

		self.type = 'module'
		self.libs = [self.kdeinitlib.target + ".la"] + self.orenv.make_list(self.libs)

		myname=None
		myext=None
		for source in self.kdeinitlib.source:
			sext=SCons.Util.splitext(source)
			if sext[0] == self.target or not myname:
				myname = sext[0]
				myext  = sext[1]

		def create_kdeinit_cpp(target, source, env):
			# Creates the dummy kdemain file for the binary
			dest=open(target[0].path, 'w')
			dest.write('extern \"C\" int kdemain(int, char* []);\n')
			dest.write('int main( int argc, char* argv[] ) { return kdemain(argc, argv); }\n')
			dest.close()
		env['BUILDERS']['KdeinitCpp'] = env.Builder(action=env.Action(create_kdeinit_cpp),
					prefix='kdeinit_', suffix='.cpp',
					src_suffix=myext)
		env.KdeinitCpp(myname)
			self.binary.source = "./kdeinit_" + myname + '.cpp'
			self.binary.execute()

		def create_kdeinit_la_cpp(target, source, env):
			""" Creates the dummy kdemain file for the module"""
			dest=open(target[0].path, 'w')
			dest.write('#include <kdemacros.h>\n')
			dest.write('extern \"C\" int kdemain(int, char* []);\n')
			dest.write('extern \"C\" KDE_EXPORT int kdeinitmain( int argc, char* argv[] ) { return kdemain(argc, argv); }\n')
			dest.close()
		env['BUILDERS']['KdeinitLaCpp'] = env.Builder(action=env.Action(create_kdeinit_la_cpp),
			  prefix='kdeinit_', suffix='.la.cpp',
			  src_suffix=myext)
		env.KdeinitLaCpp(myname)
		self.source = 'kdeinit_' + self.target + '.la.cpp'

		kdeobj.execute(self)

