
#include "Python.h"
#include "swigtooldemo.hpp"

extern "C"
{
	void init_swigdemo(void);
}

TestClass* TestClass::_instance = 0;

int main()
{
        Py_Initialize();
        init_swigdemo();

        /*FILE* file_py;
        file_py = fopen(i_oFile.toLocal8Bit(), "r");
        PyRun_SimpleFile(file_py, i_oFile.toLocal8Bit());
        fclose(file_py);
	*/
	PyRun_SimpleString("import swigdemo, sys\nsys.stderr.write('hey pfo\\n')\nsys.stderr.write(str(swigdemo.TestClass.instance()))");

        Py_Finalize();
}
