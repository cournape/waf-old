#! /usr/bin/env python
# encoding: utf-8
# Oscar Blumberg 2006 (nael)

import gamin
 
class DirectoryWatcher:
        def __init__(self, directory):
                self.watcher = gamin.WatchMonitor()
                self.setDirectory(directory)
 
        def setDirectory(self, directory):
                self.dirname = directory
 
        def start(self):
                try:
                        self.stop()
                except:
			pass
                self.watcher.watch_directory(self.dirname, self.handle_events)
 
        def stop(self):
                self.watcher.stop_watch(self.dirname)
 
        def getDirectory(self):
                return dirname
 
        def loop(self):
                while 1:
                        events = self.watcher.event_pending()
                        if events > 0: self.watcher.handle_events()
 
        def handle_events(self, file, event):
                print "Event %s on file %s" % (event, file)
                if event == gamin.GAMChanged:
                        self.changed(file)
 
        def changed(self, file):
                # TODO
                self.stop()
 
d = DirectoryWatcher("/tmp")
d.start()
d.loop()

