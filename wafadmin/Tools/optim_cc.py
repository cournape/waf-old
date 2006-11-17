
import Action, Object, Task, ccroot

class TaskMaster(Task.Task):
	def __init__(self, action_name, env, priority=5, normal=1, master=None):
		Task.Task.__init__(self, action_name, env, priority, normal)
		self.slaves=[]
		self.m_inputs2=[]
		self.m_outputs2=[]

	def add_slave(self, slave):
		self.slaves.append(slave)
		self.m_run_after.append(slave)

	def may_start(self):
		for t in self.m_run_after:
			if not t.m_hasrun: return 0

		for t in self.slaves:
			self.m_inputs.append(t.m_inputs[0])
			self.m_outputs.append(t.m_outputs[0])
			if t.m_must_run:
				self.m_inputs2.append(t.m_inputs[0])
				self.m_outputs2.append(t.m_outputs[0])
		return 1

	def run(self):
		tmpinputs = self.m_inputs
		self.m_inputs = self.m_inputs2
		tmpoutputs = self.m_outputs
		self.m_outputs = self.m_outputs2

		#env = self.m_env
		self.m_env['OFILES']=[]
		for i in self.m_outputs:
			self.m_env['OFILES'].append(i.m_name)

		ret = self.m_action.run(self)
		self.m_inputs = tmpinputs
		self.m_outputs = tmpoutputs

		return ret

class TaskSlave(Task.Task):
	def __init__(self, action_name, env, priority=5, normal=1, master=None):
		Task.Task.__init__(self, action_name, env, priority, normal)
		self.m_master = master

	def get_display(self):
		self.m_display=""
		return ""

	def update_stat(self):
		self.m_executed=1

	def must_run(self):
		self.m_must_run = Task.Task.must_run(self)
		return self.m_must_run

	def run(self):
		return 0

def create_task_new(self, type, env=None, nice=10):
	if self.m_type == "program" and (type == "cc" or type == "cpp"):

		if env is None: env=self.env
		try:
			mm = self.mastertask
		except AttributeError:
			mm = TaskMaster("all_"+type, env, nice)
			self.mastertask = mm

		task = TaskSlave(type, env, nice, master=mm)
		self.m_tasks.append(task)

		mm.add_slave(task)

		if type == self.m_type_initials:
			self.p_compiletasks.append(task)
		return task

	task = Object.genobj.create_task(self, type, env, nice)
	if type == self.m_type_initials:
		self.p_compiletasks.append(task)
	return task

def detect(conf):
	return 1

def setup(env):
	cc_str = '${CC} ${CCFLAGS} ${CPPFLAGS} ${_CCINCFLAGS} ${_CCDEFFLAGS} -c ${SRC} && mv ${OFILES} ${TGT[0].m_parent.bldpath(env)}'
        Action.simple_action('all_cc', cc_str, 'GREEN')

	cpp_str = '${CXX} ${CXXFLAGS} ${CPPFLAGS} ${_CXXINCFLAGS} ${_CXXDEFFLAGS} -c ${SRC} && mv ${OFILES} ${TGT[0].m_parent.bldpath(env)}'
	Action.simple_action('all_cpp', cpp_str, color='GREEN')

	ccroot.ccroot.create_task = create_task_new


