#!/usr/bin/env python

#    Copyright (C) 2006  Andrew Straw  <strawman@astraw.com>
#
#    This program can be distributed under the terms of the GNU LGPL.
#    See the file COPYING.
#

import hashlib
import unicodedata
import time
import re
import httplib
import json
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

class Logger(object):

    logger = logging.getLogger()
    logger.addHandler(logging.handlers.SysLogHandler(address = "/dev/log", facility = logging.handlers.SysLogHandler.LOG_USER))
    logger.setLevel(logging.DEBUG)

    @classmethod
    def debug(cls, msg):
        global logger
        cls.logger.debug(msg)

    @classmethod
    def error(cls, msg):
        global logger
        cls.logger.error(msg)

    @classmethod
    def info(cls, msg):
        global logger
        cls.logger.info(msg)

    @classmethod
    def warning(cls, msg):
        global logger
        cls.logger.warning(msg)

    @classmethod
    def log(cls, level, msg):
        global logger
        cls.logger.log(level, msg)


class MyStat(fuse.Stat):
    def __init__(self):
        self.st_mode = 0
        self.st_ino = 0
        self.st_dev = 0
        self.st_nlink = 0
        self.st_uid = 1000
        self.st_gid = 1000
        self.st_size = 0
        self.st_atime = 0
        self.st_mtime = 0
        self.st_ctime = 0

    def __str__(this):
        return "mode: %d, n_link: %d, uid: size: %d" % (this.st_mode, this.st_nlink, this.st_size)

""" Mapping of a FS object """
class FSObject(object):

    def __init__(this, fs_mode, fs_size, fs_name, fs_abspath = "", fs_uri = "", fs_parent = None):
        this.fs_parent = fs_parent
        this.fs_mode = fs_mode
        this.fs_size = fs_size
        this.fs_abspath = fs_abspath
        this.fs_name = fs_name
        this._stat_struct = MyStat()
        this.fs_uri = "" # TODO

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
        stats.st_size = this.fs_size
        stats.st_nlink = 1
        stats.st_mode = this.fs_mode
        return stats

    def getUri(this):
        return this.fs_uri

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
        Logger.debug("HASH_STRING::String: " + string)
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

    """ Return a list of objects contained in directory which hash is dirhash """
    def __getHashedDirectoryContent(this, dirhash):
        return this.__directories[dirhash]

    """ Return a FSObject that matches entryhash """
    def __getHashedEntry(this, entryhash):
        return this.__entries[entryhash]

    """ Return if given hash is known in our tree """
    def __hasHashedEntry(this, hash):
        return this.__entries.has_key(hash)

    @classmethod
    def normalize_unicode(cls, u):
        if type(u) is str: return u
        return unicodedata.normalize("NFKD", u).encode("ascii", "ignore")

    """ Build internal tree structure mapping FileSystem in memory. Recursive """
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
                if type(dirname) is unicode:
                    dirname = HelloFS.normalize_unicode(dirname)
                    HelloFS.logger.debug("Dealing with directory normalized '%s'" % dirname)
                slash = ""
                if not path[-1] == "/":
                    slash = "/"
                abspath = path + slash + dirname
                abspath = HelloFS.normalize_unicode(abspath)
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
                (filename, filesize, fileuri) = entry
                Logger.debug("Filename: %s" % filename)
                Logger.debug("FileURI: %s" % fileuri)
                file_name = HelloFS.normalize_unicode(filename)
                Logger.debug("Filename decode: %s" % file_name)
                slash = ""
                if not path[-1] == "/":
                    slash = "/"
                abspath = path + slash + file_name
                hashed_filename = HelloFS.hash_string(abspath)

                HelloFS.logger.debug("Dealing with file '%s' which is hashed to '%s'" % (abspath, hashed_filename))

                fileObject = FSObject(fs_mode = stat.S_IFREG | 0644, fs_size = filesize, fs_abspath = abspath, fs_name = file_name, fs_uri = fileuri, fs_parent = parentHash)
                this.__entries[hashed_filename] = fileObject # Update collection
                this.__directories[parentHash].append(fileObject) # Update parent directory content


    def getattr(this, path):
        HelloFS.logger.debug("getAttr[Path]: %s" % path)

        hashed_path = HelloFS.hash_string(path)
        HelloFS.logger.debug("getAttr[hash]: %s" % hashed_path)
        entry = this.__getHashedEntry(hashed_path)
        HelloFS.logger.debug("getAttr[entry]: %s" % str(entry))

        if entry is not None:
            stats = entry.getStatStruct()
            HelloFS.logger.debug("Stats: " + str(stats))
            return stats

        HelloFS.logger.debug("No entry found")

        return -errno.ENOENT


    def readdir(this, path, offset):
	HelloFS.logger.debug("readdir[path, offset]: '%s' '%d'" % (path, offset))
        content = [".", ".."]

        hashed_path = HelloFS.hash_string(path)
        dir_content = this.__getHashedDirectoryContent(hashed_path)

        if dir_content is None:
            raise ValueError("No such hash in tree")
    
        for entry in dir_content:
            content.append(str(entry.getName().decode("ascii", "ignore")))

        HelloFS.logger.debug("Content: " + str(content))

        for r in content:
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

class RemoteFSoverHTTPs(object):
    def __init__(this, host = "media.riton.fr", uri = "/json.php", use_keep_alive = False, http_debug_level = 0, update_delay = 10, **x509):
        this.host = host
        this.uri = uri
        this.use_keep_alive = use_keep_alive
        this.http_debug_level = http_debug_level
        this.x509 = x509
        this.update_delay = update_delay
        this.__json_decoder = json.JSONDecoder()
        this.__fs_mapping = []
        this.__last_update_time = 0

    def __need_update(this):
        if int(time.time()) - this.__last_update_time >= int(this.update_delay):
            Logger.debug("Cache needs to be updated")
            return True
        Logger.debug("Cache is up to date")
        return False

    def _update(this):
        Logger.info("Refreshing remote FS cache")
        conn = httplib.HTTPSConnection(
                host = this.host,
                key_file = this.x509["key_file"],
                cert_file = this.x509["cert_file"]
        )
        conn.set_debuglevel(this.http_debug_level)
        conn.putrequest('GET', this.uri)
        if this.use_keep_alive == True:
            conn.putheader("Connection", "keep-alive")
        conn.endheaders()
        response = conn.getresponse()
        body = response.read()

        obj = this.__json_decoder.decode(body)

        (root, content) = obj.popitem()
        this.__fs_mapping = content
        this.__last_update_time = int(time.time())
        return content

    def getRemoteFSMap(this):
        if this.__need_update():
            return this._update()
        return this.__fs_mapping



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

    remoteFS = RemoteFSoverHTTPs(key_file = "/home/riton/.certs/riton.key", cert_file = "/home/riton/.certs/riton.crt")


    fs_map = remoteFS.getRemoteFSMap()

    print str(fs_map)

    usage="""
Userspace hello example

""" + Fuse.fusage
    server = HelloFS(dir_structure = fs_map, version="%prog " + fuse.__version__, usage=usage, dash_s_do='setsingle')
    server.parse(errex=1)
    server.main()

if __name__ == '__main__':
    main()
