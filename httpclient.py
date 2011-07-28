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

def trav_list(list):
    for i in list:
        if type(i) == dict:
            trav_dict(i)
        elif type(i) == list:
            trav_list(i)
        else:
            url = urllib.unquote(unicode(i[2]))
            print "Name: '%s', Size: %d, Url: '%s'" % (unicode(i[0]), i[1], url)
            if url == "https://media.riton.fr/Incoming/Game of thrones.Saison 1 complete.HDTV.XviD.Proper.VOST + Soundtrack.MC07/info.nfo":
                offset = 0
                resource_length = int(getresourcelength(url))
                print "Total Resource Length: " + str(resource_length)
                time.sleep(2)
                read_size = 5092
                still_read = resource_length

                while still_read > 0:
                    if still_read < read_size:
                        read_size = still_read
                    data = getresource(url, offset, read_size)
                    offset += len(data)
                    print "ReadLength: " + str(len(data))
                    print data
                    print "#############"
                    print "resource_length: %d, Offset: %d" % (resource_length, offset)
                    still_read = resource_length - offset

                sys.exit(0)

def trav_dict(dict):
    for key in dict.keys():
        if type(dict[key]) == dict:
            trav_dict(dict[key])
        elif type(dict[key]) == list:
            trav_list(dict[key])
        else:
            print "Name: '%s', Size: %d, Url: '%s'" % (unicode(i[0]), i[1], unicode(i[2]))

trav_dict(obj)
