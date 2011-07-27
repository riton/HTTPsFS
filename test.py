#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import hashlib
import random
import logging
import logging.handlers

import os, stat, errno, sys
# pull in some spaghetti to make this stuff work without fuse-py being installed
try:
    import _find_fuse_parts
except ImportError:
    pass
import fuse
from fuse import Fuse


if not hasattr(fuse, '__version__'):
    raise RuntimeError, \
        "your fuse-py doesn't know of fuse.__version__, probably it's too old."

fuse.fuse_python_api = (0, 2)

hello_path = '/hello'
hello_str = 'Hello World!\n'

class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 0
        self.st_gid = 0
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

""" Mapping of a FS object """
class FSObject(object):

    def __init__(this, fs_mode, fs_size, fs_name, fs_abspath = "", fs_parent = None):
        this.fs_parent = fs_parent
        this.fs_mode = fs_mode
        this.fs_size = fs_size
        this.fs_abspath = fs_abspath
        this.fs_name = fs_name
        this._stat_struct = MyStat()

    def getMode(this):
        return this.fs_mode

    def getSize(this):
        return this.fs_size

    def getAbsPath(this):
        return this.fs_abspath

    def getName(this):
        return this.fs_name

    def getParent(this):
        return this.fs_parent

    def getStatStruct(this):
        stats = this._stat_struct
        stats.s_size = this.fs_size
        stats.s_nlink = 1
        stats.s_mode = this.fs_mode
        return stats

    def setAbsPath(this, path):
        this.fs_abspath = path

    def setParent(this, parent):
        this.fs_parent = parent

    def isDir(this):
        return this.fs_mode & stat.S_IFDIR

    def isFile(this):
        return this.fs_mode & stat.S_IFREG

    def __str__(this):
        return "FS_mode: '%d', FS_size: '%d', FS_name: '%s', FS_abspath: '%s', FS_parent: '%s'" % (this.fs_mode, this.fs_size, this.fs_name, this.fs_abspath, this.fs_parent)


class HelloFS(Fuse):

    logger = logging.getLogger()
    handler = logging.handlers.SysLogHandler(address = "/dev/log", facility = logging.handlers.SysLogHandler.LOG_USER)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    @classmethod
    def hash_string(cls, string):
        return hashlib.sha1(string).hexdigest()

    def __init__(this, dir_structure, *args, **kw):
        Fuse.__init__(this, *args, **kw)
        this.dir_structure = dir_structure
        HelloFS.logger.debug(str(dir_structure))

        """ Every FSObject we have indexed on sha() values """
        this.__entries = {}

        """ Every directories content with references on __entries objects """
        this.__directories = {}

        this._build_cache(dir_structure)

        HelloFS.logger.debug(str(this))

        name = "/dir1/file3"
        hashed = HelloFS.hash_string(name)
        HelloFS.logger.debug(str(this.__entries[hashed]))

        dirname = "/dir1"
        hashed = HelloFS.hash_string(dirname)
        for content in this.__directories[hashed]:
            HelloFS.logger.debug(str(content) + "belongs to " + dirname)

        sys.exit(0)


    """ Feed internal structures. Recursive """
    def _build_cache(this, entries, path = "/", parentHash = None):

        HelloFS.logger.debug("Entering function _build_cache")

        if parentHash == None:
            hashed_root = HelloFS.hash_string("/")
            dirObject = FSObject(fs_mode = stat.S_IFDIR | 0755, fs_size = 4096, fs_abspath = "/", fs_name = "", fs_parent = None)
            this.__entries[hashed_root] = dirObject
            this.__directories[hashed_root] = []
            parentHash = hashed_root


        for entry in entries:
            # Directory
            if type(entry) == dict:
                HelloFS.logger.debug("Entry '%s' is a dictionnary" % entry)
                dirname = entry.keys()[0] # Dir name we're dealing with
                HelloFS.logger.debug("Dealing with directory '%s'" % dirname)
                slash = ""
                if not path[-1] == "/":
                    slash = "/"
                abspath = path + slash + dirname
                hashed_dirname = HelloFS.hash_string(abspath)

                HelloFS.logger.debug("Dealing with absolute path '%s' which is hashed to '%s'" % (abspath, hashed_dirname))

                dirObject = FSObject(fs_mode = stat.S_IFDIR | 0755, fs_size = 4096, fs_abspath = abspath, fs_name = dirname, fs_parent = parentHash)
                this.__entries[hashed_dirname] = dirObject # Update collection
                this.__directories[hashed_dirname] = [] # Create a new directory
                this.__directories[parentHash].append(dirObject) # Update parent directory content
                this._build_cache(entry.values()[0], path + slash + dirname, hashed_dirname)

            # File    
            else:
                HelloFS.logger.debug("Entry: '%s'" % entry)
                (filename, filesize) = entry
                slash = ""
                if not path[-1] == "/":
                    slash = "/"
                abspath = path + slash + filename
                hashed_filename = HelloFS.hash_string(abspath)

                HelloFS.logger.debug("Dealing with file '%s' which is hashed to '%s'" % (abspath, hashed_filename))

                fileObject = FSObject(fs_mode = stat.S_IFREG | 0644, fs_size = filesize, fs_abspath = abspath, fs_name = filename, fs_parent = parentHash)
                this.__entries[hashed_filename] = fileObject # Update collection
                this.__directories[parentHash].append(fileObject) # Update parent directory content


#    def getattr(this, path):
#	HelloFS.logger.debug("getAttr[Path]: %s" % path)
#
#        st = MyStat()
#
#        if path == '/':
#            st.st_mode = stat.S_IFDIR | 0755
#            st.st_nlink = 1
#        elif this._fs_structure[path] is not None:
#            current = this._fs_structure[path]
#            st.st_mode = current.getMode()
#            st.st_nlink = 1
#            st.st_size = current.getSize()
#        else:
#            return -errno.ENOENT
#        return st


    def getattr(this, path):
        HelloFS.logger.debug("getAttr[Path]: %s" % path)
        st = MyStat()

        if path == "/":
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 1
            st.st_size = 4096
        elif path == "/dir" or path == "/dir/sub_dir":
            st.st_mode = stat.S_IFDIR | 0755
            st.st_nlink = 1
            st.st_size = 4096
        elif path == "/dir/file1" or path == "/dir/sub_dir/file2":
            st.st_mode = stat.S_IFREG | 0644
            st.st_nlink = 1
        else:
            return -errno.ENOENT

        return st


#    def readdir(self, path, offset):
#	HelloFS.logger.debug("readdir[path, offset]: %s %d" % (path, offset))
#        l = ['.', '..']
#        for entry in self._fs_structure.keys():
#            l.append(entry[1:])
#        for i in l:
#            HelloFS.logger.debug(str(i))
#        for r in  l:
#            yield fuse.Direntry(name = r, offset = offset, type = stat.S_IFDIR)
#

    def readdir(this, path, offset):
	HelloFS.logger.debug("readdir[path, offset]: '%s' '%d'" % (path, offset))
        l = [".", ".."]
        if path == "/":
            l.extend(["dir"])
        elif path == "/dir":
            l.extend(["sub_dir", "file1"])
        elif path == "/dir/sub_dir":
            l.extend(["file2"])
        for r in l:
            yield fuse.Direntry(name = r, offset = offset, type = stat.S_IFDIR)

    def open(self, path, flags):
	HelloFS.logger.debug("open[path, flags] : %s %d" % (path, flags))
        if path != hello_path:
            return -errno.ENOENT
        accmode = os.O_RDONLY | os.O_WRONLY | os.O_RDWR
        if (flags & accmode) != os.O_RDONLY:
            return -errno.EACCES

    def read(self, path, size, offset):
	HelloFS.logger.debug("read[path, size, offset] : %s %d %d" % (path, size, offset))
        if path != hello_path:
            return -errno.ENOENT
        slen = len(hello_str)
        if offset < slen:
            if offset + size > slen:
                size = slen - offset
            buf = hello_str[offset:offset+size]
        else:
            buf = ''
        return buf

def getRandomSize(upperLimit = 5092):
    return random.randrange(upperLimit)

def main():

    directory_structure = [
       ["file1", getRandomSize()],
       [ "file2", getRandomSize()],
        {"dir1": [
            ["file3", getRandomSize()],
            ["file4", getRandomSize()],
            {"sub_dir_1": [
                ["file5", getRandomSize()],
                ["file6", getRandomSize()],
            ]},
        ]},
    ]

    usage="""
Userspace hello example

""" + Fuse.fusage
    server = HelloFS(dir_structure = directory_structure, version="%prog " + fuse.__version__, usage=usage, dash_s_do='setsingle')
    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()