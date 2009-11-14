::
:: win32 support file: allow running pythons scripts as binary 
::
:: run from package source root 
:: 
:: another solution may be http://mail.python.org/pipermail/python-list/1999-December/018772.html
:: or http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/366355
:: 
@echo off

if not defined PYTHON (
	if exist "\PYTHON24\python.exe" (
		set PYTHON=\Python24
		echo PYTHON installation found unter: %PYTHON%
	)	else (
		if exist "c:\PYTHON24\python.exe" (
			set PYTHON=c:\Python24
			echo PYTHON installation found unter: %PYTHON%
		)
	)
)

if not "%PYTHON%"=="" (
	assoc .py=Python.File
	ftype Python.File=%PYTHON%\python.exe "%%1" %%*
	set PATHEXT=%PATHEXT%;.py

	set PATH=%CD%;%CD%\utils;%PATH%
	echo ...
	echo now you can start any python script from waf 


) else (
	echo please set PYTHON environment variable to your python installation
)

