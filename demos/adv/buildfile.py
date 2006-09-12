#! /usr/bin/env python
"""
this is a simple helper file that has to be in inclulde path
"""

def readCodeFromFile(fileName):
	"""opens a textfile and read the complete file
	into code string"""
	f=open(fileName, 'r')
	code = f.read()
	f.close()
	return code

def try_build_file(conf, fileName, msgPrefix="HAVE"):
	"""try to build a file and fill a define value"""
	import os
	try:
		code = readCodeFromFile(fileName)
	except:
		print "file %s not found or could not be opened." % fileName
		return False
	try:
		__msg = msgPrefix + "_" + ((fileName.split(os.sep)[-1]).split('.')[0]).upper()
		if conf.try_build(code, msg = __msg):
			conf.addDefine(__msg, 1)
			return True
		else:
			return False
	except:
		return False
