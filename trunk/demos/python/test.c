#include <Python.h>

static int numargs=0;

static PyObject* emb_numargs(PyObject *self, PyObject *args)
{
    if(!PyArg_ParseTuple(args, ":numargs"))
        return NULL;
    return Py_BuildValue("i", numargs);
}

static PyMethodDef EmbMethods[] = {
    {"numargs", emb_numargs, METH_VARARGS,
     "Return the number of arguments received by the process."},
    {NULL, NULL, 0, NULL}
};


int main(int argc, char *argv[])
{
	Py_Initialize();
	numargs = argc;
	Py_InitModule("emb", EmbMethods);
	PyRun_SimpleString("import emb; print 'Number of arguments', emb.numargs()");
	Py_Finalize();
	return 0;
}
