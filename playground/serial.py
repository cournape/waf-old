
# old code for running tasks sequentially

class Serial(object):
	def __init__(self, bld):
		self.manager = bld.task_manager
		self.outstanding = []

		# progress bar
		self.total = self.manager.total()
		self.processed = 0
		self.error = 0

		self.switchflag = 1 # postpone
		# self.manager.debug()

	# warning, this one is recursive ..
	def get_next(self):
		if self.outstanding:
			t = self.outstanding.pop(0)
			self.processed += 1
			return t

		# handle case where only one wscript exist
		# that only install files
		if not self.manager.groups:
			return None

		(_, self.outstanding) = self.manager.get_next_set()
		if not self.outstanding: return None

		return self.get_next()

	def postpone(self, tsk):
		self.processed -= 1
		self.switchflag *= -1
		# this actually shuffle the list
		if self.switchflag>0: self.outstanding.insert(0, tsk)
		else:                 self.outstanding.append(tsk)

	def start(self):
		global g_quiet
		debug('runner: Serial start called')
		while 1:
			# get next Task
			tsk = self.get_next()
			if tsk is None: break

			if Logs.verbose: debug('runner: retrieving %r' % tsk)

			st = tsk.runnable_status()
			if st == ASK_LATER:
				debug('runner: postponing %r' % tsk)
				self.postpone(tsk)
				#tsk = None
				continue
			# # =======================

			#debug("m_sig is "+str(tsk.sig), 'runner')
			#debug("obj output m_sig is "+str(tsk.outputs[0].get_sig()), 'runner')

			#continue
			if st == SKIP_ME:
				tsk.hasrun = SKIPPED
				self.manager.add_finished(tsk)
				continue

			# display the command that we are about to run
			if not g_quiet:
				tsk.position = (self.processed, self.total)
				printout(tsk.display())

			# run the command
			if tsk.__class__.stat: ret = tsk.__class__.stat(tsk)
			else: ret = tsk.run()
			self.manager.add_finished(tsk)

			# non-zero means something went wrong
			if ret:
				self.error = 1
				tsk.hasrun = CRASHED
				tsk.err_code = ret
				if Options.options.keep: continue
				else: return -1

			try:
				tsk.post_run()
			except OSError:
				self.error = 1
				tsk.hasrun = MISSING
				if Options.options.keep: continue
				else: return -1
			else:
				tsk.hasrun = SUCCESS

		if self.error:
			return -1


