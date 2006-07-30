#! /usr/bin/env python
# encoding: utf-8
#
#DirWatch chooses a supported backend (fam, gamin or fallback)
#it is mainly a wrapper script without own methods beside this


from Params import debug, error, trace, fatal, warning
import GaminAdaptor, FamAdaptor, FallbackAdaptor

class DirectoryWatcher:
        def __init__(self):
                if FamAdaptor.support:
                        debug("using FamAdaptor")
                        self.__adapter = FamAdaptor.WatchMonitor()
                elif GaminAdaptor.support:
                        debug("using GaminAdaptor")
                        self.__adapter = GaminAdaptor.WatchMonitor()
                else:
                        debug("using FallbackAdaptor")
                        self.__adapter = FallbackAdaptor.WatchMonitor()
        
        def addDirWatch(self, idxName, CallBackThis, dirList, handleEvents=['changed', 'deleted', 'created']):
                """add dirList to watch.
                idxName: unique name for ref
                CallBackThis: is called if something in dirs in dirlist has events (handleEvents)  
                callbackthis(idxName, changedFilePath)
                dirList: list of dirs to watch
                handleEvents:  events to handle possible are 'changed', 'deleted', 'created', 'exist'
                        suspendDirWatch after a handled change
                """
                self.__adapter.addDirWatch(idxName, CallBackThis, dirList, handleEvents)
        
        def removeDirWatch(self, idxName):
                """remove DirWatch with name idxName"""
                self.__adapter.removeDirWatch(idxName)
        
        def removeAllDirWatch(self):
                """remove all DirWatcher"""
                self.__adapter.removeAllDirWatch()
        
        def suspendDirWatch(self, idxName):
                """suspend DirWatch with name idxName. No dir/filechanges will be reacted until resume"""
                self.__adapter.suspendDirWatch(idxName)
        
        def suspendAllDirWatch(self):
                """suspend all DirWatcher ... they could be resumed with resumeAllDirWatch"""
                self.__adapter.suspendAllDirWatch()
        
        def resumeDirWatch(self, idxName):
                """resume a DirWatch that was supended with suspendDirWatch or suspendAllDirWatch"""
                self.__adapter.resumeDirWatch(idxName)
        
        def resumeAllDirWatch(self):
                """ resume all DirWatcher"""
                self.__adapter.resumeAllDirWatch()
        
        def loop(self):
                self.__adapter.loop()

class test:
        def __init__(self):
                self.fam_test=DirectoryWatcher()
                self.fam_test.addDirWatch("tmp Test", self.thisIsCalledBack, ["/tmp"])
                self.fam_test.loop()
                self.fam_test.loop()
        
        def thisIsCalledBack(self, idxName, pathName, event):
                print "idxName=%s, Path=%s, Event=%s "%(idxName, pathName, event)
                self.fam_test.resumeDirWatch(idxName)

if __name__=="__main__":
        test() 
