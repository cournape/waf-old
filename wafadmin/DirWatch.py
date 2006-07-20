#! /usr/bin/env python
# encoding: utf-8
# Oscar Blumberg 2006 (nael)
#edited by Matthias Jahn <jahn.matthias@freenet.de>
#added fam support

import os, sys, select, errno

try:
        import gamin
        have_gamin = True
except:
        have_gamin = False

try:
        import _fam
        have_fam = True
except:
        have_fam = False
if (not have_gamin) and (not have_fam):
        print "you need gamin or fam python bindings"
        sys.exit(1)

class TestRequest:
	def __init__(self, userData, isDir):
		self.fr = None
		self.userData = userData
		self.isDir = isDir

class DirectoryWatcher:
        def __init__(self, directory):
                if have_gamin:
                        self.watcher = gamin.WatchMonitor()
                else:
                        # hash of filename => TestRequest
                        self.requests={}
                        self.watcher = _fam.open()
                        self.requests[directory]=TestRequest('DIR %s: ' % directory, 1)
                        print "[__init__] DIR %s: "% directory
                self.setDirectory(directory)
 
        def setDirectory(self, directory):
                self.dirname = directory
 
        def start(self):
                try:
                        self.stop()
                except:
                        pass
                if have_gamin:
                        self.watcher.watch_directory(self.dirname, self.handle_events)
                else:
                        self.requests[self.getDirectory()].fr = self.watcher.monitorDirectory(self.getDirectory(), self.requests[self.getDirectory()].userData)
                        print "[start] DIR %s: "% self.getDirectory()
 
        def stop(self):
                if have_gamin:
                        self.watcher.stop_watch(self.dirname)
                else:
                        for request in self.requests.values():
                                print 'Cancelling monitoring of request %i' % request.fr.requestID()
                                request.fr.cancelMonitor()
 
        def getDirectory(self):
                return self.dirname
        
        def processDirEvents(self, fe):
                if fe.userData:
                        print fe.userData,
                print fe.filename, fe.code2str()
                self.handle_events(fe.filename, fe.code2str())

        def loop(self):
                if have_gamin:
                        while 1:
                                events = self.watcher.event_pending()
                                if events > 0: self.watcher.handle_events()
                else:
                                print "[loop]"
                                while 1:
                                        try:
                                                ri, ro, re = select.select([self.watcher], [], [])
                                        except select.error, er:
                                                errnumber, strerr = er
                                                if errnumber == errno.EINTR:
                                                        continue
                                                else:
                                                        print strerr
                                                        sys.exit(1)
                                        while self.watcher.pending():
                                                fe = self.watcher.nextEvent()
                                                self.processDirEvents(fe)

 
        def handle_events(self, file, event):
                print "Event [%s] on file %s" % (event, file)
                if have_gamin:
                        if event == gamin.GAMChanged:
                                self.changed(file)
                else:
                        #i hope that this i the meaning behind gamin.GAMChanged
                        if (event != 'exists') and (event != 'endExist'):
                                self.changed(file)
 
        def changed(self, file):
                # TODO
                self.stop()
                if not have_gamin:
                        print "[changed] file: %s\n .watcher close"% file
                        self.watcher.close()
                        print 'Closed connection'
                sys.exit(0)
 
d = DirectoryWatcher("/tmp")
d.start()
d.loop()

