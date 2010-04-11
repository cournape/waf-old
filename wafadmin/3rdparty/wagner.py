#!/usr/bin/env python
# encoding: utf-8
# ita 2010

import Logs, Utils

def say(txt):
	Logs.warn("^o^: %s" % txt)

Utils.pprint('PINK', r""" _________________________________________
/ hello I am wagner and I will review the \
\ code as the build is being executed     /
 -----------------------------------------
        \
          ^o^
""")


say('you make the errors, we detect them')
