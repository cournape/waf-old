/*
fnv.c implemented from http://isthe.com/chongo/tech/comp/fnv/

Changing md5 for fnv:
* brings a 10% speed improvement on hashing files (tried on a fast computer for hashing divx files)
* reduces the signature size by 2 (128 bits -> 64 bits) pickling the cache is faster

Thomas Nagy 2008
*/

#include <Python.h>

/*
To compile, put the following in new file named "setup.py"
Then run the command "python setup.py build"

from distutils.core import setup, Extension
setup(name="fnv", version="0.1", ext_modules=[Extension("fnv", ["fnv.c"])])

To try the beast, put the .so in the current folder, or run
python setup.py install, and then try the following script

import fnv
x = fnv.new()
for num in xrange(15):
	x.update("blahla")
	print str(x.digest())
*/

#define INTSIZE 8
/* (sizeof(u_int64_t)) */
#define FNV1_64_INIT ((u_int64_t)14695981039346656037ULL)
#define FNV1_64_PRIME ((u_int64_t)1099511628211)

/* second line is much faster - why? */
/*#define FNV_64A_OP(hash, octet) (((u_int64_t)(hash) ^ (u_int8_t)(octet)) * FNV1_64_PRIME) */
#define FNV_64A_OP(hash, octet) ((hash ^ octet) * FNV1_64_PRIME)

typedef struct fnv_struct
{
	PyObject_HEAD
	u_int64_t sum;
} fnv_struct;

static PyObject * fnv_update(fnv_struct *self, PyObject *args)
{
	unsigned char *cp;
	int len;

	if (!PyArg_ParseTuple(args, "s#:update", &cp, &len))
		return NULL;

	int i;
	for (i = 0; i < len; ++i)
	{
		self->sum = FNV_64A_OP(self->sum, cp[i]);
	}

	Py_INCREF(Py_None);
	return Py_None;
}

static PyObject * fnv_hfile(fnv_struct *self, PyObject *args)
{
	unsigned char *cp;
	int len;
	if (!PyArg_ParseTuple(args, "s#:hfile", &cp, &len))
		return NULL;

	self->sum = FNV1_64_INIT;
	FILE *stream;
	unsigned char buf[8192];
	int i;
	int numread;
	if ((stream = fopen((char*)cp, "r")) != NULL)
	{
		do
		{
			numread = fread(buf, sizeof(unsigned char), 8192, stream);
			for (i=0; i<numread; ++i)
			{
				self->sum = FNV_64A_OP(self->sum, buf[i]);
			}
		}
		while (numread);
		fclose(stream);
	}
	else
	{
		return NULL;
	}
	return PyString_FromStringAndSize((char*) &self->sum, INTSIZE);
}

static PyObject * fnv_digest(fnv_struct *self)
{
	return PyString_FromStringAndSize((char*) &self->sum, INTSIZE);
}

static PyObject * fnv_hexdigest(fnv_struct *self)
{
    unsigned char hexdigest[2*INTSIZE];
    int i;
    for (i=0; i<INTSIZE; ++i)
    {
        char u = ((unsigned char*) &self->sum)[i];
        char c;
        c = (u >> 4) & 0xf;
        c = (c>9) ? c + 'a' - 10 : c + '0';
        hexdigest[2*i] = c;
        c = u & 0xf;
        c = c > 9 ? c + 'a' - 10 : c + '0';
        hexdigest[2*i+1] = c;
    }
	PyObject* ret = PyString_FromStringAndSize((char *) hexdigest, 2*INTSIZE);
	return ret;
}

static PyMethodDef fnv_methods[] = {
	{"update",    (PyCFunction)fnv_update,    METH_VARARGS, NULL},
	{"digest",    (PyCFunction)fnv_digest,    METH_NOARGS,  NULL},
	{"hexdigest", (PyCFunction)fnv_hexdigest, METH_NOARGS,  NULL},
	{"hfile",     (PyCFunction)fnv_hfile,     METH_VARARGS, NULL},
	{NULL}
};

static void fnv_dealloc(fnv_struct* self)
{
	PyObject_Del(self);
}

static PyTypeObject fnv_type;

static fnv_struct * fnv_new(void)
{
	fnv_struct * obj;
	obj = PyObject_New(fnv_struct, &fnv_type);
	if (obj == NULL) return NULL;
	obj->sum = FNV1_64_INIT;
	return obj;
}

static PyObject * new_fnv_new(PyObject *self, PyObject *args)
{
	fnv_struct *obj;
	if ((obj = fnv_new()) == NULL)
		return NULL;
	return (PyObject *)obj;
}

static PyTypeObject fnv_type = {
	PyObject_HEAD_INIT(NULL)
	0,                       /*ob_size*/
	"fnv",                   /*tp_name*/
	sizeof(fnv_struct),      /*tp_basicsize*/
	0,                       /*tp_itemsize*/
	(destructor)fnv_dealloc, /*tp_dealloc*/
	0,                       /*tp_print*/
	0,                       /*tp_getattr*/
	0,                       /*tp_setattr*/
	0,                       /*tp_compare*/
	0,                       /*tp_repr*/
	0,                       /*tp_as_number*/
	0,                       /*tp_as_sequence*/
	0,                       /*tp_as_mapping*/
	0,                       /*tp_hash */
	0,                       /*tp_call*/
	0,                       /*tp_str*/
	0,                       /*tp_getattro*/
	0,                       /*tp_setattro*/
	0,                       /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,      /*tp_flags*/
	"fnv objects",           /* tp_doc */
	0,		         /* tp_traverse */
	0,		         /* tp_clear */
	0,		         /* tp_richcompare */
	0,		         /* tp_weaklistoffset */
	0,		         /* tp_iter */
	0,		         /* tp_iternext */
	fnv_methods,             /* tp_methods */
	0,                       /* tp_members */
	0,                       /* tp_getset */
	0,                       /* tp_base */
	0,                       /* tp_dict */
	0,                       /* tp_descr_get */
	0,                       /* tp_descr_set */
	0,                       /* tp_dictoffset */
	0,                       /* tp_init */
	0,                       /* tp_alloc */
	0,                       /* tp_new */
};

static PyMethodDef fnv_funs[] = {
	{"new",	(PyCFunction)new_fnv_new, METH_VARARGS, NULL},
	{NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC initfnv(void)
{
	PyObject* m;

	fnv_type.tp_new = PyType_GenericNew;
	if (PyType_Ready(&fnv_type) < 0)
		return;

	m = Py_InitModule3("fnv", fnv_funs, NULL);

	Py_INCREF(&fnv_type);
	PyModule_AddObject(m, "fnv", (PyObject *)&fnv_type);
}

