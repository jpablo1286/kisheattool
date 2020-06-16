#!/usr/bin/python
import pprint
import collections
import sqlite3
import heatmap
import math
from functools import partial
import pyproj
from shapely.ops import transform
from shapely.geometry import Point
import xml.etree.ElementTree
import re
from xml.etree.ElementTree import ElementTree
from optparse import OptionParser
from os.path import basename
from os.path import isfile
from sqlite3 import Error

def create_connection(db_file):
    """ create a database connection to the SQLite database
        specified by db_file
    :param db_file: database file
    :return: Connection object or None
    """
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)

    return conn


def create_table(conn, create_table_sql):
	try:
		c = conn.cursor()
		c.execute(create_table_sql)
		c.close()
	except Error as e:
		print(e)

def insert_device(conn, parameters):
	try:
		sql_insert_dev = """ INSERT INTO devices(first_time,last_time,devkey,phyname,devmac,strongest_signal,min_lat,min_lon,max_lat,max_lon,avg_lat,avg_lon,bytes_data,type,device)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?); """
		c = conn.cursor()
		c.execute(sql_insert_dev,parameters)
		c.close()
	except Error as e:
		print(e)

def insert_packet(conn, parameters):
	try:
		sql_insert_pack = """ INSERT INTO packets(ts_sec,ts_usec,phyname,sourcemac,destmac,transmac,frequency,devkey,lat,lon,alt,speed,heading,packet_len,signal,datasource,dlt,packet,error,tags)
		VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?); """
		c = conn.cursor()
		c.execute(sql_insert_pack,parameters)
		c.close()
	except Error as e:
		print(e)

def splitup(stringthing):
	parts = stringthing.partition('=')
	return (parts[0], parts[2].strip('"'))

def default_factory(): return 0

proj_wgs84 = pyproj.Proj(init='epsg:4326')

def geodesic_point_buffer(lat, lon, m):
    # Azimuthal equidistant projection
    aeqd_proj = '+proj=aeqd +lat_0={lat} +lon_0={lon} +x_0=0 +y_0=0'
    project = partial(
        pyproj.transform,
        pyproj.Proj(aeqd_proj.format(lat=lat, lon=lon)),
        proj_wgs84)
    buf = Point(0, 0).buffer(m)  # distance in metres
    return transform(project, buf).exterior.coords[:]

pp = pprint.PrettyPrinter(indent=4)

usage = "usage: [options] OPUTFILENAME"
parser = OptionParser(usage=usage)
parser.add_option('-a', '--latitud',help='Latitud for simulated AP',dest='latitud',default=0.0,action='store',type='float')
parser.add_option('-o', '--longitud',help='Longitud for simulated AP',dest='longitud',default=0.0,action='store',type='float')
parser.add_option('-e', '--list',help='Use existing Kismet file',dest='existingFile',default=False,action='store_true')

(options, args) = parser.parse_args()

if len(args) == 0:
	print usage
	exit()

matchEssid = ''

if len(args) == 1:
	outputFile = args[0]

database = outputFile + ".kismet"

if isfile(database) and options.existingFile is not True:
	print ("Output file already exist ... exiting")
	exit()

topSig=0
bottomSig=-85
iter=10
step=(bottomSig - topSig)/iter
startPoint=0
endPoint=35
stepPoint=(endPoint-startPoint)/iter



sql_create_devices_table = """ CREATE TABLE devices (
									first_time INT,
									last_time INT,
									devkey TEXT,
									phyname TEXT,
									devmac TEXT,
									strongest_signal INT,
									min_lat REAL,
									min_lon REAL,
									max_lat REAL,
									max_lon REAL,
									avg_lat REAL,
									avg_lon REAL,
									bytes_data INT,
									type TEXT,
									device BLOB,
									UNIQUE(phyname, devmac) ON CONFLICT REPLACE
									); """

sql_create_packets_table = """ CREATE TABLE packets (
									ts_sec INT,
									ts_usec INT,
									phyname TEXT,
									sourcemac TEXT,
									destmac TEXT,
									transmac TEXT,
									frequency REAL,
									devkey TEXT,
									lat REAL,
									lon REAL,
									alt REAL,
									speed REAL,
									heading REAL,
									packet_len INT,
									signal INT,
									datasource TEXT,
									dlt INT,
									packet BLOB,
									error INT,
									tags TEXT
									);"""



conn = create_connection(database)


if conn is not None:
	if options.existingFile is not True:
		create_table(conn, sql_create_devices_table)
		create_table(conn, sql_create_packets_table)
		parameters = (1577370500,1577370500,'4202770D00000000_279349E5A4E20000','IEEE802.11','00:00:00:00:00:00',-90,3.88803339004517,-76.9734725952148,3.88803339004517,-76.9734725952148,3.888033,-76.973472,0,'Wi-Fi AP','{"kismet.device.base.name":"virtualAP","kismet.device.base.channel":10}')
		insert_device(conn, parameters)

else:
    print("Error! cannot create the database connection.")

print options.latitud," ",options.longitud

for x in range(1,iter+1):
    distance=x*stepPoint
    signal=x*step
    print "distance: ",distance," signal:",signal
    b = geodesic_point_buffer(options.latitud, options.longitud,distance )
    for cord in b:
		packet=(1577369147,968918,'IEEE802.11','00:00:00:00:00:00','00:00:00:00:00:00','00:00:00:00:00:00',2412000.0,0,cord[1],cord[0],43.7000007629395,0.0,0.0,250,signal,'5FE308BD-0000-0000-0000-E2A6FDD13ED7',127,None,0,None)
		insert_packet(conn, packet)

conn.commit()
conn.close()
