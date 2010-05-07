#! /usr/bin/env python

import Build
Build.BuildContext.add_subdirs = Build.BuildContext.recurse

import Configure
Configure.ConfigurationContext.sub_config = Configure.ConfigurationContext.recurse



