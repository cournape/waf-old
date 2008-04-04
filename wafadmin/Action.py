#! /usr/bin/env python
# encoding: utf-8
# Thomas Nagy, 2005-2008 (ita)

"Actions are used to build the nodes of most tasks"

import re
import Object, Params, Runner
from Params import debug, fatal

g_actions={}
"global actions"

reg_act = re.compile(r"(?P<dollar>\$\$)|(?P<subst>\$\{(?P<var>\w+)(?P<code>.*?)\})", re.M)

class Action(object):
	"Base class for all Actions, an action takes a task and produces its outputs"
	def __init__(self, name, vars=[], func=None, prio=100, color='GREEN'):
		"""If the action is simple, func is not defined, else a function can be attached
		and will be launched instead of running the string generated by 'setstr' see Runner
		for when this is used - a parameter is given, it is the task. Each action must name"""

		self.m_name = name
		# variables triggering a rebuild
		self.m_vars = vars
		self.m_function_to_run = func
		self.m_color = color

		self.prio = prio

		global g_actions
		if name in g_actions: debug('overriding action: %s' % name, 'action')
		g_actions[name] = self
		debug("action added: %s" % name, 'action')

	def __str__(self):
		return self.m_name

	def get_str(self, task):
		"string to display to the user"
		env = task.env()
		src_str = ' '.join([a.nice_path(env) for a in task.m_inputs])
		tgt_str = ' '.join([a.nice_path(env) for a in task.m_outputs])
		return '* %s : %s -> %s\n' % (self.m_name, src_str, tgt_str)

	def run(self, task):
		"run the compilation"
		f = self.m_function_to_run
		if not f: fatal("Action %s has no function!" % self.m_name)
		return f(task)

def funex(c):
	exec(c)
	return f

def simple_action(name, line, color='GREEN', vars=[], prio=100):
	"""Compiles a string (once) into an Action instance, eg:
	simple_action('c++', '${CXX} -o ${TGT[0]} ${SRC} -I ${SRC[0].m_parent.bldpath()}')

	The env variables (CXX, ..) on the task must not hold dicts (order)
	The reserved keywords TGT and SRC represent the task input and output nodes
	"""
	extr = []
	def repl(match):
		g = match.group
		if g('dollar'): return "$"
		elif g('subst'): extr.append((g('var'), g('code'))); return "%s"
		return None

	line = reg_act.sub(repl, line)

	parm = []
	dvars = []
	app = parm.append
	for (var, meth) in extr:
		if var == 'SRC':
			if meth: app('task.m_inputs%s' % meth)
			else: app('" ".join([a.srcpath(env) for a in task.m_inputs])')
		elif var == 'TGT':
			if meth: app('task.m_outputs%s' % meth)
			else: app('" ".join([a.bldpath(env) for a in task.m_outputs])')
		else:
			if not var in dvars: dvars.append(var)
			app("p('%s')" % var)
	if parm: parm = "%% (%s) " % (',\n\t\t'.join(parm))
	else: parm = ''

	c = '''
def f(task):
	env = task.env()
	p = env.get_flat
	try: cmd = "%s" %s
	except Exception: task.debug(); raise
	return Runner.exec_command(cmd)
''' % (line, parm)

	debug(c, 'action')

	act = Action(name, prio=prio, color=color)
	act.m_function_to_run = funex(c)
	act.m_vars = vars or dvars

	return act

