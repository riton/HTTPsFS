#!/usr/bin/env python

import httplib
import urllib
import re
import json
import sys
import time

conn = httplib.HTTPSConnection(
        host = "media.riton.fr",
        key_file = "/home/riton/.certs/riton.key",
        cert_file = "/home/riton/.certs/riton.crt",
)
conn.set_debuglevel(255)
conn.putrequest('GET', '/json.php')
conn.putheader("Connection", "keep-alive")
conn.endheaders()
response = conn.getresponse()
body = response.read()

decoder = json.JSONDecoder()
obj = decoder.decode(body)

print type(obj)

print str(obj)

# TODO
def getresource(uri, offset, length):
    conn = httplib.HTTPSConnection(
            host = "media.riton.fr",
            key_file = "/home/riton/.certs/riton.key",
            cert_file = "/home/riton/.certs/riton.crt",
    )
    match = re.search("^https://media.riton.fr(.*)", uri)
    conn.putrequest("GET", match.group(1))
    if offset != 0:
        conn.putheader("Range", "bytes=%d-%d" % (offset, offset + length))
    conn.endheaders()
    response = conn.getresponse()
    return response.read(length)

def getresourcelength(uri):
    conn = httplib.HTTPSConnection(
            host = "media.riton.fr",
            key_file = "/home/riton/.certs/riton.key",
            cert_file = "/home/riton/.certs/riton.crt",
    )
    match = re.search("^https://media.riton.fr(.*)", uri)
    conn.putrequest("HEAD", match.group(1))
    conn.endheaders()
    return conn.getresponse().getheader("Content-Length")

def readresource(uri, size, offset):
    conn = httplib.HTTPSConnection(
            host = "media.riton.fr",
            key_file = "/home/riton/.certs/riton.key",
            cert_file = "/home/riton/.certs/riton.crt",
    )
    match = re.search("^https://media.riton.fr(.*)", uri)
    conn.putrequest("GET", match.group(1))
    if offset != 0:
        conn.putheader("Range", "bytes=%d-%d" % (offset, offset + length))
    conn.endheaders()
    response = conn.getresponse()
    if response.status != httplib.PARTIAL_CONTENT or response.status != httplib.OK:
        return -errno.ENOENT
    return response.read(length)


def fetch_content(content, parent):

    for i in content:
        if type(i) is dict:
            # Found a new directory
            dir_content = []
            traverse_directory(i, dir_content)
            print "DirContent: " + str(dir_content)
            parent.append(dir_content)
        elif type(i) is list:
            # Found a new file
            (file_name, file_size, file_uri) = i
            parent.append((file_name, file_size, file_uri))
#
#        else:
#            print str(type(i))
#            print i
#            raise ValueError("Not supposed to get a string value")
#            mapping.append(i)
#            continue
#            url = urllib.unquote(unicode(i[2]))
#            print "Name: '%s', Size: %d, Url: '%s'" % (unicode(i[0]), i[1], url)
#            if url == "https://media.riton.fr/Incoming/Game of thrones.Saison 1 complete.HDTV.XviD.Proper.VOST + Soundtrack.MC07/info.nfo":
#                offset = 0
#                resource_length = int(getresourcelength(url))
#                print "Total Resource Length: " + str(resource_length)
#                time.sleep(2)
#                read_size = 5092
#                still_read = resource_length
#
#                while still_read > 0:
#                    if still_read < read_size:
#                        read_size = still_read
#                    data = getresource(url, offset, read_size)
#                    offset += len(data)
#                    print "ReadLength: " + str(len(data))
#                    print data
#                    print "#############"
#                    print "resource_length: %d, Offset: %d" % (resource_length, offset)
#                    still_read = resource_length - offset
#
#                sys.exit(0)

def traverse_directory(directory, parent):

    (dirname, content) = directory.popitem()

    print "Dirname: " + dirname

    fetch_content(content, parent)

directory_content = []
traverse_directory(obj, directory_content)
print str(directory_content)
