from Configure import conftest
import Utils
import Task
from TaskGen import taskgen, feature, before, after, extension

EXT_FC = ".f"
EXT_OBJ = ".o"

@conftest
def find_gfortran(conf):
    v = conf.env
    fc = conf.find_program('gfortran', var='FC')
    if not fc:
        conf.fatal('gfortran not found')

    v['FC'] = fc
    v['FCFLAGS'] = ''

@feature('fortran')
def default_fc(self):
    Utils.def_attrs(self,
        linktasks = [],
        compiled_tasks = [],)

@extension(EXT_FC)
def fortran_hook(self, node):
    task = self.create_task('fortran')
    task.inputs = [node]
    task.outputs = [node.change_ext(EXT_OBJ)]
    self.compiled_tasks.append(task)
    return task

#@feature('fortran')
#@after('apply_core')
#def apply_fortran_link(self):
#    task = self.create_task('fortran_link')
#    task.inputs = [t.outputs[0] for t in self.compiled_tasks]
#    task.outputs = [self.path.find_or_declare(self.target)]
#    self.linktasks.append(task)

# Compile task
cls = Task.simple_task_type('fortran',
        '${FC} ${FCFLAGS} -c -o ${TGT} ${SRC}',
        'GREEN',
        ext_out=EXT_OBJ,
        ext_in=EXT_FC)

# # Link task
# cls = Task.simple_task_type('fortran_link',
#         '${FC} -o ${TGT} ${SRC}',
#         color='YELLOW', ext_in=EXT_OBJ)
# cls.maxjobs = 1

detect = '''
find_gfortran
'''
