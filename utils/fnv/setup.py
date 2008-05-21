from distutils.core import setup, Extension
setup(name="fnv", version="0.1", ext_modules=[Extension("fnv", ["fnv.c"])])
