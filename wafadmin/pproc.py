# subprocess - Subprocesses with accessible I/O streams
#
# For more information about this module, see PEP 324.
#
# Copyright (c) 2003-2004 by Peter Astrand <astrand@lysator.liu.se>
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of the
# author not be used in advertising or publicity pertaining to
# distribution of the software without specific, written prior
# permission.
#
# THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE,
# INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS.
# IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, INDIRECT OR
# CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
# OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT,
# NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION
# WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

import sys
mswindows = (sys.platform == "win32")

import os
import types
import traceback

if mswindows:
    import threading
    import msvcrt
    if 0: # <-- change this to use pywin32 instead of the _subprocess driver
        import pywintypes
        from win32api import GetStdHandle, STD_INPUT_HANDLE, \
                             STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
        from win32api import GetCurrentProcess, DuplicateHandle, \
                             GetModuleFileName, GetVersion
        from win32con import DUPLICATE_SAME_ACCESS, SW_HIDE
        from win32pipe import CreatePipe
        from win32process import CreateProcess, STARTUPINFO, \
                                 GetExitCodeProcess, STARTF_USESTDHANDLES, \
                                 STARTF_USESHOWWINDOW, CREATE_NEW_CONSOLE
        from win32event import WaitForSingleObject, INFINITE, WAIT_OBJECT_0
    else:
        from _subprocess import *
        class STARTUPINFO:
            dwFlags = 0
            hStdInput = None
            hStdOutput = None
            hStdError = None
        class pywintypes:
            error = IOError
else:
    import select
    import errno
    import fcntl
    import pickle

__all__ = ["Popen", "PIPE", "STDOUT", "call"]

try:
    MAXFD = os.sysconf("SC_OPEN_MAX")
except:
    MAXFD = 256

# True/False does not exist on 2.2.0
try:
    False
except NameError:
    False = 0
    True = 1

_active = []

def _cleanup():
    for inst in _active[:]:
        inst.poll()

PIPE = -1
STDOUT = -2


def call(*args, **kwargs):
    """Run command with arguments.  Wait for command to complete, then
    return the returncode attribute.

    The arguments are the same as for the Popen constructor.  Example:

    retcode = call(["ls", "-l"])
    """
    return Popen(*args, **kwargs).wait()


def list2cmdline(seq):
    """
    Translate a sequence of arguments into a command line
    string, using the same rules as the MS C runtime:

    1) Arguments are delimited by white space, which is either a
       space or a tab.

    2) A string surrounded by double quotation marks is
       interpreted as a single argument, regardless of white space
       contained within.  A quoted string can be embedded in an
       argument.

    3) A double quotation mark preceded by a backslash is
       interpreted as a literal double quotation mark.

    4) Backslashes are interpreted literally, unless they
       immediately precede a double quotation mark.

    5) If backslashes immediately precede a double quotation mark,
       every pair of backslashes is interpreted as a literal
       backslash.  If the number of backslashes is odd, the last
       backslash escapes the next double quotation mark as
       described in rule 3.
    """

    # See
    # http://msdn.microsoft.com/library/en-us/vccelng/htm/progs_12.asp
    result = []
    needquote = False
    for arg in seq:
        bs_buf = []

        # Add a space to separate this argument from the others
        if result:
            result.append(' ')

        needquote = (" " in arg) or ("\t" in arg)
        if needquote:
            result.append('"')

        for c in arg:
            if c == '\\':
                # Don't know if we need to double yet.
                bs_buf.append(c)
            elif c == '"':
                # Double backspaces.
                result.append('\\' * len(bs_buf)*2)
                bs_buf = []
                result.append('\\"')
            else:
                # Normal char
                if bs_buf:
                    result.extend(bs_buf)
                    bs_buf = []
                result.append(c)

        # Add remaining backspaces, if any.
        if bs_buf:
            result.extend(bs_buf)

        if needquote:
            result.extend(bs_buf)
            result.append('"')

    return ''.join(result)


class Popen(object):
    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None,
                 preexec_fn=None, close_fds=False, shell=False,
                 cwd=None, env=None, universal_newlines=False,
                 startupinfo=None, creationflags=0):
        """Create new Popen instance."""
        _cleanup()

        if not isinstance(bufsize, (int, long)):
            raise TypeError("bufsize must be an integer")

        if mswindows:
            if preexec_fn is not None:
                raise ValueError("preexec_fn is not supported on Windows "
                                 "platforms")
            if close_fds:
                raise ValueError("close_fds is not supported on Windows "
                                 "platforms")
        else:
            # POSIX
            if startupinfo is not None:
                raise ValueError("startupinfo is only supported on Windows "
                                 "platforms")
            if creationflags != 0:
                raise ValueError("creationflags is only supported on Windows "
                                 "platforms")

        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.pid = None
        self.returncode = None
        self.universal_newlines = universal_newlines

        # Input and output objects. The general principle is like
        # this:
        #
        # Parent                   Child
        # ------                   -----
        # p2cwrite   ---stdin--->  p2cread
        # c2pread    <--stdout---  c2pwrite
        # errread    <--stderr---  errwrite
        #
        # On POSIX, the child objects are file descriptors.  On
        # Windows, these are Windows file handles.  The parent objects
        # are file descriptors on both platforms.  The parent objects
        # are None when not using PIPEs. The child objects are None
        # when not redirecting.

        (p2cread, p2cwrite,
         c2pread, c2pwrite,
         errread, errwrite) = self._get_handles(stdin, stdout, stderr)

        self._execute_child(args, executable, preexec_fn, close_fds,
                            cwd, env, universal_newlines,
                            startupinfo, creationflags, shell,
                            p2cread, p2cwrite,
                            c2pread, c2pwrite,
                            errread, errwrite)

        if p2cwrite:
            self.stdin = os.fdopen(p2cwrite, 'wb', bufsize)
        if c2pread:
            if universal_newlines:
                self.stdout = os.fdopen(c2pread, 'rU', bufsize)
            else:
                self.stdout = os.fdopen(c2pread, 'rb', bufsize)
        if errread:
            if universal_newlines:
                self.stderr = os.fdopen(errread, 'rU', bufsize)
            else:
                self.stderr = os.fdopen(errread, 'rb', bufsize)

        _active.append(self)


    def _translate_newlines(self, data):
        data = data.replace("\r\n", "\n")
        data = data.replace("\r", "\n")
        return data


    if mswindows:
        #
        # Windows methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tupel with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            if stdin == None and stdout == None and stderr == None:
                return (None, None, None, None, None, None)

            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin == None:
                p2cread = GetStdHandle(STD_INPUT_HANDLE)
            elif stdin == PIPE:
                p2cread, p2cwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                p2cwrite = p2cwrite.Detach()
                p2cwrite = msvcrt.open_osfhandle(p2cwrite, 0)
            elif type(stdin) == types.IntType:
                p2cread = msvcrt.get_osfhandle(stdin)
            else:
                # Assuming file-like object
                p2cread = msvcrt.get_osfhandle(stdin.fileno())
            p2cread = self._make_inheritable(p2cread)

            if stdout == None:
                c2pwrite = GetStdHandle(STD_OUTPUT_HANDLE)
            elif stdout == PIPE:
                c2pread, c2pwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                c2pread = c2pread.Detach()
                c2pread = msvcrt.open_osfhandle(c2pread, 0)
            elif type(stdout) == types.IntType:
                c2pwrite = msvcrt.get_osfhandle(stdout)
            else:
                # Assuming file-like object
                c2pwrite = msvcrt.get_osfhandle(stdout.fileno())
            c2pwrite = self._make_inheritable(c2pwrite)

            if stderr == None:
                errwrite = GetStdHandle(STD_ERROR_HANDLE)
            elif stderr == PIPE:
                errread, errwrite = CreatePipe(None, 0)
                # Detach and turn into fd
                errread = errread.Detach()
                errread = msvcrt.open_osfhandle(errread, 0)
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif type(stderr) == types.IntType:
                errwrite = msvcrt.get_osfhandle(stderr)
            else:
                # Assuming file-like object
                errwrite = msvcrt.get_osfhandle(stderr.fileno())
            errwrite = self._make_inheritable(errwrite)

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _make_inheritable(self, handle):
            """Return a duplicate of handle, which is inheritable"""
            return DuplicateHandle(GetCurrentProcess(), handle,
                                   GetCurrentProcess(), 0, 1,
                                   DUPLICATE_SAME_ACCESS)


        def _find_w9xpopen(self):
            """Find and return absolut path to w9xpopen.exe"""
            w9xpopen = os.path.join(os.path.dirname(GetModuleFileName(0)),
                                    "w9xpopen.exe")
            if not os.path.exists(w9xpopen):
                # Eeek - file-not-found - possibly an embedding
                # situation - see if we can locate it in sys.exec_prefix
                w9xpopen = os.path.join(os.path.dirname(sys.exec_prefix),
                                        "w9xpopen.exe")
                if not os.path.exists(w9xpopen):
                    raise RuntimeError("Cannot locate w9xpopen.exe, which is "
                                       "needed for Popen to work with your "
                                       "shell or platform.")
            return w9xpopen


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (MS Windows version)"""

            if not isinstance(args, types.StringTypes):
                args = list2cmdline(args)

            # Process startup details
            default_startupinfo = STARTUPINFO()
            if startupinfo == None:
                startupinfo = default_startupinfo
            if not None in (p2cread, c2pwrite, errwrite):
                startupinfo.dwFlags |= STARTF_USESTDHANDLES
                startupinfo.hStdInput = p2cread
                startupinfo.hStdOutput = c2pwrite
                startupinfo.hStdError = errwrite

            if shell:
                default_startupinfo.dwFlags |= STARTF_USESHOWWINDOW
                default_startupinfo.wShowWindow = SW_HIDE
                comspec = os.environ.get("COMSPEC", "cmd.exe")
                args = comspec + " /c " + args
                if (GetVersion() >= 0x80000000L or
                        os.path.basename(comspec).lower() == "command.com"):
                    # Win9x, or using command.com on NT. We need to
                    # use the w9xpopen intermediate program. For more
                    # information, see KB Q150956
                    # (http://web.archive.org/web/20011105084002/http://support.microsoft.com/support/kb/articles/Q150/9/56.asp)
                    w9xpopen = self._find_w9xpopen()
                    args = '"%s" %s' % (w9xpopen, args)
                    # Not passing CREATE_NEW_CONSOLE has been known to
                    # cause random failures on win9x.  Specifically a
                    # dialog: "Your program accessed mem currently in
                    # use at xxx" and a hopeful warning about the
                    # stability of your system.  Cost is Ctrl+C wont
                    # kill children.
                    creationflags |= CREATE_NEW_CONSOLE

            # Start the process
            try:
                hp, ht, pid, tid = CreateProcess(executable, args,
                                         # no special security
                                         None, None,
                                         # must inherit handles to pass std
                                         # handles
                                         1,
                                         creationflags,
                                         env,
                                         cwd,
                                         startupinfo)
            except pywintypes.error, e:
                # Translate pywintypes.error to WindowsError, which is
                # a subclass of OSError.  FIXME: We should really
                # translate errno using _sys_errlist (or simliar), but
                # how can this be done from Python?
                raise WindowsError(*e.args)

            # Retain the process handle, but close the thread handle
            self._handle = hp
            self.pid = pid
            ht.Close()

            # Child is launched. Close the parent's copy of those pipe
            # handles that only the child should have open.  You need
            # to make sure that no handles to the write end of the
            # output pipe are maintained in this process or else the
            # pipe will not close when the child process exits and the
            # ReadFile will hang.
            if p2cread != None:
                p2cread.Close()
            if c2pwrite != None:
                c2pwrite.Close()
            if errwrite != None:
                errwrite.Close()


        def poll(self):
            """Check if child process has terminated.  Returns returncode
            attribute."""
            if self.returncode == None:
                if WaitForSingleObject(self._handle, 0) == WAIT_OBJECT_0:
                    self.returncode = GetExitCodeProcess(self._handle)
                    _active.remove(self)
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode == None:
                obj = WaitForSingleObject(self._handle, INFINITE)
                self.returncode = GetExitCodeProcess(self._handle)
                _active.remove(self)
            return self.returncode


        def _readerthread(self, fh, buffer):
            buffer.append(fh.read())


        def communicate(self, input=None):
            """Interact with process: Send data to stdin.  Read data from
            stdout and stderr, until end-of-file is reached.  Wait for
            process to terminate.  The optional input argument should be a
            string to be sent to the child process, or None, if no data
            should be sent to the child.

            communicate() returns a tuple (stdout, stderr)."""
            stdout = None # Return
            stderr = None # Return

            if self.stdout:
                stdout = []
                stdout_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stdout, stdout))
                stdout_thread.setDaemon(True)
                stdout_thread.start()
            if self.stderr:
                stderr = []
                stderr_thread = threading.Thread(target=self._readerthread,
                                                 args=(self.stderr, stderr))
                stderr_thread.setDaemon(True)
                stderr_thread.start()

            if self.stdin:
                if input != None:
                    self.stdin.write(input)
                self.stdin.close()

            if self.stdout:
                stdout_thread.join()
            if self.stderr:
                stderr_thread.join()

            # All data exchanged.  Translate lists into strings.
            if stdout != None:
                stdout = stdout[0]
            if stderr != None:
                stderr = stderr[0]

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(open, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

    else:
        #
        # POSIX methods
        #
        def _get_handles(self, stdin, stdout, stderr):
            """Construct and return tupel with IO objects:
            p2cread, p2cwrite, c2pread, c2pwrite, errread, errwrite
            """
            p2cread, p2cwrite = None, None
            c2pread, c2pwrite = None, None
            errread, errwrite = None, None

            if stdin == None:
                pass
            elif stdin == PIPE:
                p2cread, p2cwrite = os.pipe()
            elif type(stdin) == types.IntType:
                p2cread = stdin
            else:
                # Assuming file-like object
                p2cread = stdin.fileno()

            if stdout == None:
                pass
            elif stdout == PIPE:
                c2pread, c2pwrite = os.pipe()
            elif type(stdout) == types.IntType:
                c2pwrite = stdout
            else:
                # Assuming file-like object
                c2pwrite = stdout.fileno()

            if stderr == None:
                pass
            elif stderr == PIPE:
                errread, errwrite = os.pipe()
            elif stderr == STDOUT:
                errwrite = c2pwrite
            elif type(stderr) == types.IntType:
                errwrite = stderr
            else:
                # Assuming file-like object
                errwrite = stderr.fileno()

            return (p2cread, p2cwrite,
                    c2pread, c2pwrite,
                    errread, errwrite)


        def _set_cloexec_flag(self, fd):
            try:
                cloexec_flag = fcntl.FD_CLOEXEC
            except AttributeError:
                cloexec_flag = 1

            old = fcntl.fcntl(fd, fcntl.F_GETFD)
            fcntl.fcntl(fd, fcntl.F_SETFD, old | cloexec_flag)


        def _close_fds(self, but):
            for i in range(3, MAXFD):
                if i == but:
                    continue
                try:
                    os.close(i)
                except:
                    pass


        def _execute_child(self, args, executable, preexec_fn, close_fds,
                           cwd, env, universal_newlines,
                           startupinfo, creationflags, shell,
                           p2cread, p2cwrite,
                           c2pread, c2pwrite,
                           errread, errwrite):
            """Execute program (POSIX version)"""

            if isinstance(args, types.StringTypes):
                args = [args]

            if shell:
                args = ["/bin/sh", "-c"] + args

            if executable == None:
                executable = args[0]

            # For transferring possible exec failure from child to parent
            # The first char specifies the exception type: 0 means
            # OSError, 1 means some other error.
            errpipe_read, errpipe_write = os.pipe()
            self._set_cloexec_flag(errpipe_write)

            self.pid = os.fork()
            if self.pid == 0:
                # Child
                try:
                    # Close parent's pipe ends
                    if p2cwrite:
                        os.close(p2cwrite)
                    if c2pread:
                        os.close(c2pread)
                    if errread:
                        os.close(errread)
                    os.close(errpipe_read)

                    # Dup fds for child
                    if p2cread:
                        os.dup2(p2cread, 0)
                    if c2pwrite:
                        os.dup2(c2pwrite, 1)
                    if errwrite:
                        os.dup2(errwrite, 2)

                    # Close pipe fds.  Make sure we doesn't close the same
                    # fd more than once.
                    if p2cread:
                        os.close(p2cread)
                    if c2pwrite and c2pwrite not in (p2cread,):
                        os.close(c2pwrite)
                    if errwrite and errwrite not in (p2cread, c2pwrite):
                        os.close(errwrite)

                    # Close all other fds, if asked for
                    if close_fds:
                        self._close_fds(but=errpipe_write)

                    if cwd != None:
                        os.chdir(cwd)

                    if preexec_fn:
                        apply(preexec_fn)

                    if env == None:
                        os.execvp(executable, args)
                    else:
                        os.execvpe(executable, args, env)

                except:
                    exc_type, exc_value, tb = sys.exc_info()
                    # Save the traceback and attach it to the exception object
                    exc_lines = traceback.format_exception(exc_type,
                                                           exc_value,
                                                           tb)
                    exc_value.child_traceback = ''.join(exc_lines)
                    os.write(errpipe_write, pickle.dumps(exc_value))

                # This exitcode won't be reported to applications, so it
                # really doesn't matter what we return.
                os._exit(255)

            # Parent
            os.close(errpipe_write)
            if p2cread and p2cwrite:
                os.close(p2cread)
            if c2pwrite and c2pread:
                os.close(c2pwrite)
            if errwrite and errread:
                os.close(errwrite)

            # Wait for exec to fail or succeed; possibly raising exception
            data = os.read(errpipe_read, 1048576) # Exceptions limited to 1 MB
            os.close(errpipe_read)
            if data != "":
                os.waitpid(self.pid, 0)
                child_exception = pickle.loads(data)
                raise child_exception


        def _handle_exitstatus(self, sts):
            if os.WIFSIGNALED(sts):
                self.returncode = -os.WTERMSIG(sts)
            elif os.WIFEXITED(sts):
                self.returncode = os.WEXITSTATUS(sts)
            else:
                # Should never happen
                raise RuntimeError("Unknown child exit status!")

            _active.remove(self)


        def poll(self):
            """Check if child process has terminated.  Returns returncode
            attribute."""
            if self.returncode == None:
                try:
                    pid, sts = os.waitpid(self.pid, os.WNOHANG)
                    if pid == self.pid:
                        self._handle_exitstatus(sts)
                except os.error:
                    pass
            return self.returncode


        def wait(self):
            """Wait for child process to terminate.  Returns returncode
            attribute."""
            if self.returncode == None:
                pid, sts = os.waitpid(self.pid, 0)
                self._handle_exitstatus(sts)
            return self.returncode


        def communicate(self, input=None):
            """Interact with process: Send data to stdin.  Read data from
            stdout and stderr, until end-of-file is reached.  Wait for
            process to terminate.  The optional input argument should be a
            string to be sent to the child process, or None, if no data
            should be sent to the child.

            communicate() returns a tuple (stdout, stderr)."""
            read_set = []
            write_set = []
            stdout = None # Return
            stderr = None # Return

            if self.stdin:
                # Flush stdio buffer.  This might block, if the user has
                # been writing to .stdin in an uncontrolled fashion.
                self.stdin.flush()
                if input:
                    write_set.append(self.stdin)
                else:
                    self.stdin.close()
            if self.stdout:
                read_set.append(self.stdout)
                stdout = []
            if self.stderr:
                read_set.append(self.stderr)
                stderr = []

            while read_set or write_set:
                rlist, wlist, xlist = select.select(read_set, write_set, [])

                if self.stdin in wlist:
                    # When select has indicated that the file is writable,
                    # we can write up to PIPE_BUF bytes without risk
                    # blocking.  POSIX defines PIPE_BUF >= 512
                    bytes_written = os.write(self.stdin.fileno(), input[:512])
                    input = input[bytes_written:]
                    if not input:
                        self.stdin.close()
                        write_set.remove(self.stdin)

                if self.stdout in rlist:
                    data = os.read(self.stdout.fileno(), 1024)
                    if data == "":
                        self.stdout.close()
                        read_set.remove(self.stdout)
                    stdout.append(data)

                if self.stderr in rlist:
                    data = os.read(self.stderr.fileno(), 1024)
                    if data == "":
                        self.stderr.close()
                        read_set.remove(self.stderr)
                    stderr.append(data)

            # All data exchanged.  Translate lists into strings.
            if stdout != None:
                stdout = ''.join(stdout)
            if stderr != None:
                stderr = ''.join(stderr)

            # Translate newlines, if requested.  We cannot let the file
            # object do the translation: It is based on stdio, which is
            # impossible to combine with select (unless forcing no
            # buffering).
            if self.universal_newlines and hasattr(open, 'newlines'):
                if stdout:
                    stdout = self._translate_newlines(stdout)
                if stderr:
                    stderr = self._translate_newlines(stderr)

            self.wait()
            return (stdout, stderr)

