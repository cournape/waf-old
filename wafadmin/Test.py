#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005 (ita)

import os, sys

import Build
import Node
import Deptree
import Params
import Environment

def trace(msg):
	Params.trace(msg, 'Test')
def debug(msg):
	Params.debug(msg, 'Test')
def error(msg):
	Params.error(msg, 'Test')

def info(msg):
	Params.pprint('CYAN', msg)

def testname(file):
	return open('test/'+file, 'r')

if __name__ == "__main__":
	
	for i in ['dist','configure','clean','distclean','make','install','doc']:
		Params.g_commands[i]=0

	#exec testname('paths.tst')
	#exec testname('configure.tst')
	#exec testname('environment.tst')
	#exec testname('stress.tst')
	#exec testname('stress2.tst')
	#exec testname('scanner.tst')
	exec testname('scheduler.tst')
	#exec testname('cpptest.tst') # redundant, the demo does it better

