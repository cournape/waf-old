#! /usr/bin/env python

import Build
Build.BuildContext.add_subdirs = Build.BuildContext.recurse

import Configure
Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse
Configure.conftest = Configure.conf

from TaskGen import before, feature

@feature('d')
@before('apply_incpaths')
def old_importpaths(self):
	if getattr(self, 'importpaths', []):
		self.includes = self.importpaths

