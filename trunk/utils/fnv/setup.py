from distutils.core import setup, Extension
setup(name="fnv", version="0.1", ext_modules=[Extension("fnv", ["fnv.c"], extra_compile_args=['-std=c89', '-Wall'])] )
