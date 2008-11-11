#! /usr/bin/env python
# encoding: utf-8
# Peter Soetens, 2006

"docbook processing (may be broken)"

import os, string, re
import TaskGen, Utils, Build, Task
from Logs import debug

xslt_vardeps = ['XSLTPROC', 'XSLTPROC_ST']

# Create .fo or .html from xml file
def xslt_build(task):
	bdir = task.inputs[0].bld_dir(task.env)
	src = task.inputs[0].bldpath(task.env)
	srcdir = os.path.dirname(task.inputs[0].bldpath(task.env))
	tgt = os.path.join(bdir, task.outputs[0].name)
	stylesheet = os.path.join(srcdir,task.env['XSLT_SHEET'])

	task.env['TGT'] = tgt
	task.env['SRC'] = src
	task.env['STYLESHEET'] = stylesheet

	cmd = task.env['XSLTPROC_ST'] % task.env
	debug(cmd)
	return task.generator.bld.exec_command(cmd)

re_xi = re.compile('''<xi:include[^>]+href=['"]([^'">]+)['"][^>]+>''', re.M)
def xmlscan(self):
	p = self.inputs[0].parent
	node_lst = [self.inputs[0]]
	seen = []
	depnodes = []
	while node_lst:
		nd = node_lst.pop(0)
		if nd.id in seen: continue
		seen.append(nd.id)

		code = nd.read(self.env)
		for m in re_xi.finditer(code):
			name = m.group(1)
			k = p.find_resource(name)
			if k: depnodes.append(k)
	return [depnodes, ()]

# Create various file formats from a docbook or sgml file.
db2_vardeps = ['DB2','DB2HTML', 'DB2PDF', 'DB2TXT', 'DB2PS']
def db2_build(task):
	bdir = task.inputs[0].bld_dir(task.env)
	src = task.inputs[0].bldpath(task.env)
	cmd = task.compiler % (bdir, src)
	debug(cmd)
	return Utils.exec_command(cmd)

xslt_vardeps = ['XSLTPROC']

## Given a 'docbook' object and a node to build,
# create the tasks to build the node's target.
def docb_file(obj, node):

	base, ext = os.path.splitext(node.name)

	# Input format is XML
	if ext == '.xml' and not obj.env['XSLTPROC']:
			raise Utils.WafError("Can not process %s: no xml processor detected." % node.name)
	if ext == '.xml' and obj.type == 'pdf':
		xslttask = obj.create_task('xslt')

		xslttask.inputs  = [node]
		xslttask.outputs = [node.change_ext('.fo')]
		if not obj.stylesheet:
			raise Utils.WafError('No stylesheet specified for creating pdf.')

		xslttask.env['XSLT_SHEET'] = obj.stylesheet

		# now we also add the task that creates the pdf file
		foptask = obj.create_task('fop')
		foptask.inputs  = xslttask.outputs
		foptask.outputs = [node.change_ext('.pdf')]

		foptask.set_run_after(xslttask)

	if ext == '.xml' and obj.type == 'html':
		xslttask = obj.create_task('xslt')

		xslttask.inputs  = [node]
		xslttask.outputs = [node.change_ext('.html')]
		if not obj.stylesheet:
			raise Utils.WafError('No stylesheet specified for creating html.')
		xslttask.env['XSLT_SHEET'] = obj.stylesheet

	# Input format is docbook.
	if ext == '.sgml' or ext == '.docbook':
		if not obj.env["DB2%s" % string.upper(obj.type) ]:
			raise Utils.WafError("Can not process %s: no suitable docbook processor detected." %  node.name )
	if ext == '.sgml' or ext == '.docbook':

		xslttask = obj.create_task('db2')

		xslttask.inputs  = [node]
		xslttask.outputs = [node.change_ext('.' + obj.type)]
		xslttask.env = xslttask.env.copy()
		xslttask.env['DBCOMPILER'] = xslttask.env["DB2%s" % string.upper(obj.type)]

	if ext == '.xml':
		if obj.type == 'txt' or obj.type == 'ps':
			raise Utils.WafError("docbook: while processing '%s':\n"
			      'txt and ps output are currently not supported when input format is XML.' % node.name )

# docbook objects
class docbook_taskgen(TaskGen.task_gen):
	def __init__(self, *k, **kw):
		TaskGen.task_gen.__init__(self, *k, **kw)
		self.stylesheet = None

		self.ext = ['html', 'pdf', 'txt', 'ps']

	def apply(self):

		# for each source argument, create a task
		lst = self.source.split()
		for filename in lst:
			node = self.path.find_resource(filename)
			if not node:
				raise Utils.WafError("source not found: "+filename+" in "+str(self.path))

			# create a task to process the source file.
			docb_file(self, node)

	def install(self):
		if not (Options.commands['install'] or Options.commands['uninstall']):
			return

		current = Build.bld.path
		lst = []
		docpath = os.path.join('share', Utils.g_module.APPNAME, 'doc')

		# Install all generated docs
		for task in self.m_tasks:
			base, ext = os.path.splitext(task.outputs[0].name)
			if ext[1:] not in self.ext:
				continue
			self.install_results('PREFIX', docpath, task )


Task.simple_task_type('fop', '${FOP} ${SRC[0].bldpath(env)} ${SRC[0].bldpath(env)[:-3]}.pdf')
cls = Task.simple_task_type('db2', "${DBCOMPILER} ${SRC[0].bld_dir(env)} ${SRC[0].bldpath(env)}")
cls.scan = xmlscan
cls = Task.task_type_from_func('xslt', vars=xslt_vardeps, func=xslt_build, color='BLUE')
cls.scan = xmlscan

## Detect the installed programs: fop, xsltproc, xalan, docbook2xyz
# Favour xsltproc over xalan.
def detect(conf):
	# Detect programs for converting xml -> html/pdf
	fop = conf.find_program('fop', var='FOP')
	if fop:
		conf.env['FOP'] = fop
	xsltproc = conf.find_program('xsltproc', var='XSLTPROC')
	if xsltproc:
		conf.env['XSLTPROC_ST'] = '%(XSLTPROC)s --xinclude %(STYLESHEET)s %(SRC)s > %(TGT)s'
		conf.env['XSLTPROC'] = xsltproc

	xalan = conf.find_program('xalan', var='XALAN')
	if not xsltproc and xalan:
		conf.env['XSLTPROC_ST'] = '%(XSLTPROC)s -xsl %(STYLESHEET)s -in %(SRC)s -out %(TGT)s'
		conf.env['XSLTPROC'] = xalan

	saxon = conf.find_program('saxon', var='SAXON')
	if not xsltproc and not xalan:
		conf.env['XSLTPROC_ST'] = '%(XSLTPROC)s %(SRC)s %(STYLESHEET)s > %(target)s'
		conf.env['XSLTPROC'] = saxon

	# OpenJade conversion tools for converting sgml -> xyz
	jw = conf.find_program('jw', var='JW')
	if jw:
		conf.env['DB2HTML'] = "jw -u -f docbook -b html -o"
		conf.env['DB2PDF']  = "jw -f docbook -b pdf -o"
		conf.env['DB2PS']   = "jw -f docbook -b ps -o"
		conf.env['DB2TXT']  = "jw -f docbook -b txt -o"

