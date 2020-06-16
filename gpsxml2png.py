#!/usr/bin/env python2

"""
Copyright (c) 2016, Bliksem Labs B.V.
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import sys
import sqlite3
import numpy
from scipy.interpolate import griddata
import matplotlib.pyplot as plt


try:
    from lxml import etree
except ImportError:
    try:
        # Python 2.5
        import xml.etree.cElementTree as etree
    except ImportError:
        try:
            # Python 2.5
            import xml.etree.ElementTree as etree
        except ImportError:
            try:
                # normal cElementTree install
                import cElementTree as etree
            except ImportError:
                try:
                    # normal ElementTree install
                    import elementtree.ElementTree as etree
                except ImportError:
                    print("Failed to import ElementTree from any known place")
# Process the Kismet GPSXML into columns.
def parse_xml(filename):
    ts = []
    bssid = []
    signal = []
    lat = []
    lon = []
    walked_lon = []
    walked_lat = []
    mybssid = {}
    try:
        sqliteConnection = sqlite3.connect(filename, timeout=20)
        cursor = sqliteConnection.cursor()
        print("Connected to SQLite")

        sqlite_select_query = """SELECT devmac as MAC,json_extract(device, '$."kismet.device.base.name"') as BSSID FROM devices WHERE type='Wi-Fi AP'"""
        cursor.execute(sqlite_select_query)
        bssidr = cursor.fetchall()
        cursor.close()
        for row in bssidr:
            mybssid[row[0]] = row[1]
    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
        print("The SQLite connection is closed")
    try:
        sqliteConnection = sqlite3.connect(filename, timeout=20)
        cursor = sqliteConnection.cursor()
        print("Connected to SQLite")

        sqlite_select_query = """SELECT * from snapshots WHERE snaptype='GPS'"""
        cursor.execute(sqlite_select_query)
        gpssteps = cursor.fetchall()
        cursor.close()
        for row in gpssteps:
            walked_lon.append(float(row[3]))
            walked_lat.append(float(row[2]))

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
        print("The SQLite connection is closed")
    try:
        sqliteConnection = sqlite3.connect(filename, timeout=20)
        cursor = sqliteConnection.cursor()
        print("Connected to SQLite")

        sqlite_select_query = """SELECT * from packets"""
        cursor.execute(sqlite_select_query)
        packets = cursor.fetchall()
        cursor.close()
        for row in packets:
            if row[3] in mybssid.keys():
                bssid.append(mybssid[row[3]])
                ts.append(int(row[0]))
                lat.append(float(row[8]))
                lon.append(float(row[9]))
                signal.append(int(row[14]))

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if (sqliteConnection):
            sqliteConnection.close()
        print("The SQLite connection is closed")

    return (ts, bssid, signal, lat, lon, walked_lon, walked_lat,)


# Draw parsed data on a surface

def draw_data(ts, bssid, signal, lat, lon, walked_lon, walked_lat):

	# We create a grid of 1000x1000
	grid_x, grid_y = numpy.mgrid[min(walked_lon):max(walked_lon):1000j, min(walked_lat):max(walked_lat):1000j]

	# We want to draw all unique APs
	bssids = list(set(bssid))

	# For each BSSID...
	for s in bssids:
		points_lon = []
		points_lat = []
		values = []
		h = []

		# Apply all points on an intermediate surface
		# so we can distinct points where we were, without reception
		for i in range(0, len(bssid)):
			if bssid[i] == s:
				hc = hash((lon[i], lat[i]))
				if hc not in h:
					points_lon.append(lon[i])
					points_lat.append(lat[i])
					values.append(float(signal[i]))
					h.append(hash((lon[i], lat[i])))

		# Optional: apply -100dBm where we don't have gathered data
		for i in range(0, len(walked_lon)):
			hc = hash((walked_lon[i], walked_lat[i]))
			if hc not in h:
				points_lon.append(lon[i])
				points_lat.append(lat[i])
				values.append(float(-100))
				h.append(hash((walked_lon[i], walked_lat[i])))

		# Interpolate the data
		grid = griddata((points_lon, points_lat), numpy.array(values), (grid_x, grid_y), method='cubic')

		# Store the bitmap in the current folder.
		plt.show()
		plt.imsave('%s.png' % (s), grid.T)

		# Calculate the World File for use in Qgis
		a = ((max(walked_lon)-min(walked_lon))/1000)
		b = 0
		c = 0
		d = ((max(walked_lat)-min(walked_lat))/1000)
		e = min(walked_lon)
		f = min(walked_lat)

		# Write the World File
		open('%s.pngw' % (s), 'w').write('%.16f\n%d\n%d\n%.16f\n%.16f\n%.16f' % (a, b, c, d, e, f,))

if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("Usage %s << /path/to/Kismet.gpsxml >>" % (sys.argv[0]))
		sys.exit(-1)

	draw_data(*parse_xml(sys.argv[1]))
