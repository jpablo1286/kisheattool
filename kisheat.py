#!/usr/bin/python
import pprint
import collections
import sqlite3
import heatmap
import xml.etree.ElementTree
import re
from xml.etree.ElementTree import ElementTree
from optparse import OptionParser
from os.path import basename



def splitup(stringthing):
	parts = stringthing.partition('=')
	return (parts[0], parts[2].strip('"'))

def default_factory(): return 0

pp = pprint.PrettyPrinter(indent=4)

usage = "usage: [options] [path/to/]SAMPLE_NAME [ESSID PATTERN]"
parser = OptionParser(usage=usage)
parser.add_option('-l', '--list',help='Just list xSSIDs and exit',dest='listOnly',default=False,action='store_true')
parser.add_option('-a', '--alldata',help='Include all samples taken while not moving (can exagerate signal strength)',dest='allData',default=False,action='store_true')
parser.add_option('-m','--mergedata',help='Merge all datasets into one overlay whose name you must specify.  If you use a regex filter the merged data will be restricted to accesspoints that matched it. Useful for mapping whole-network coverage mapping.',dest='mergeTo',default=None,action='store',type='string')
parser.add_option('-c','--channel',help='Filter by channel',dest='channelFilter',default=None,action='store',type='string')
parser.add_option('-d', '--list-channels',help='List channels and distribution',dest='listChannels',default=False,action='store_true')

(options, args) = parser.parse_args()

if len(args) == 0:
	print usage
	exit()

matchEssid = ''

if len(args) == 2:
	matchEssid = args[1]

accesspoints = {}
networks = {}
channels = {}
listchannels = {}
datasetName = basename(args[0])

try:
	sqliteConnection = sqlite3.connect(args[0], timeout=20)
	cursor = sqliteConnection.cursor()
	print("Connected to SQLite")

	sqlite_select_query = """SELECT devmac as MAC,json_extract(device, '$."kismet.device.base.name"') as ESSID, json_extract(device, '$."kismet.device.base.channel"') as CHANNEL FROM devices WHERE type='Wi-Fi AP'"""
	cursor.execute(sqlite_select_query)
	bssidr = cursor.fetchall()
	cursor.close()
	for row in bssidr:
		networks[row[0]] = row[1]
		channels[row[0]] = row[2]
		if options.listChannels:
			if row[2] in listchannels:
				listchannels[row[2]] += 1
			else:
				listchannels[row[2]] = 1

except sqlite3.Error as error:
	print("Error while connecting to sqlite", error)
finally:
	if (sqliteConnection):
		sqliteConnection.close()
	print("The SQLite connection is closed")

if options.mergeTo is not None:
	accesspoints[options.mergeTo] = list()

if options.listOnly or options.listChannels:
	if options.listOnly:
		for bssid,essid in networks.items():
			print bssid," ",essid
	if options.listChannels:
		for channel,counts in listchannels.items():
			print channel,": ",counts
else:
	locations = {}
	try:
		sqliteConnection = sqlite3.connect(args[0], timeout=20)
		cursor = sqliteConnection.cursor()
		print("Connected to SQLite")

		sqlite_select_query = """SELECT * from packets"""
		cursor.execute(sqlite_select_query)
		packets = cursor.fetchall()
		cursor.close()
		for row in packets:
			if row[3] in networks.keys():
				if (row[3] not in accesspoints) and (options.mergeTo is None):
					accesspoints[row[3]] = list()
				if not options.allData:
					location = '%(bssid)s,%(lon)f,%(lat)f' % {"bssid": row[3], "lon": float(row[9]), "lat": float(row[8])}
					if location in locations:
						locations[location]+=1
					else:
						locations[location]=1
				if (locations[location] == 1) or options.allData:
					if options.mergeTo is None:
						if options.channelFilter is None:
							accesspoints[row[3]].append((float(row[9]),float(row[8]),100+float(row[14])))
						else:
							if options.channelFilter == channels[row[3]]:
								accesspoints[row[3]].append((float(row[9]),float(row[8]),100+float(row[14])))
					else:
						if options.channelFilter is None:
							accesspoints[options.mergeTo].append((float(row[9]),float(row[8]),100+float(row[14])))
						else:
							if options.channelFilter == channels[row[3]]:
								accesspoints[options.mergeTo].append((float(row[9]),float(row[8]),100+float(row[14])))

	except sqlite3.Error as error:
		print("Error while connecting to sqlite", error)
	finally:
		if (sqliteConnection):
			sqliteConnection.close()
		print("The SQLite connection is closed")

	for key in accesspoints:
		if options.mergeTo is None:
			print networks[key]
		else:
			print options.mergeTo
		hm = heatmap.Heatmap()
		try:
			if options.mergeTo is None:
				hm.heatmap(accesspoints[key],'%(bssid)s_%(channel)s.png'% {'bssid': key, 'channel': channels[key]})
				hm.saveKML('%(bssid)s-%(channel)s.kml'% {'bssid': key, 'channel': channels[key]})
			else:
				hm.heatmap(accesspoints[key],'%(bssid)s.png'% {'bssid': key})
				hm.saveKML('%(dataset)s-%(network)s.kml'% {'dataset' : datasetName, 'network': options.mergeTo})
		except ZeroDivisionError:
			print "Error generating map overlay - data sample too small"
		except IndexError:
			print "Error generating map overlay - data sample too small"
