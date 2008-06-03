#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"""
Actions (Scons design) were used to separate the code to execute from the Task objects
This had no clear justification (extra level of indirection when a factory
is just fine) and is removed in Waf 1.5
"""

#import warnings
#warnings.warn("The WAF module 'Action' is being deprecated! :-)", DeprecationWarning, stacklevel=2)
#del warnings

import Task
Action = Task.task_type_from_func
simple_action = Task.simple_task_type

