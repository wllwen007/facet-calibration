from math import *
from constants import *
import numpy as np
try:
    from astropy import coordinates as coord
except ImportError:
    print 'Find coords will not work'
try: from astropy import units as u
except ImportError:
    print 'Find coords will not work'
from astronomy import *
import pyfits
import os,sys

def find_coords(objectname):

    # Some name changes
    if objectname == 'MACS J0717+3745':
        objectname = 'ClG J0717+3745'
    if objectname == 'OPHIUCHUS':
        objectname = 'OPH CLUSTER'
    if 'ZwCl' in objectname:
        for i in range(0,10):
            objectname = objectname.replace('.%s+'%i,'+')
    if objectname == 'ESO 3060170':
        objectname = 'ACO S 540'
    if 'MACS J' in objectname:
        objectname = objectname.replace('MACS J', 'RX J')
    
    try:
        coords = coord.ICRSCoordinates.from_name("%s"%objectname)
    except Exception as ex:
        print ex
        return 'Unable to find coords for %s'%objectname
    rad2deg = 360.0/(2*np.pi)
    coordsra = coords.ra.radians*rad2deg
    coordsdec = coords.dec.radians*rad2deg

    return coordsra,coordsdec

def query_summs(queryra,querydec,queryradius,pbeamfwhm):
    # Given an RA, DEC, radius and primary beam this wil return information on sources in the vicinity
    # queryra,querydec and queryradius are in degrees
    # pbeamfwhm is in arcmin (for ATCA = 42.0)
    sourcecat = open('/data2/shimwell/acretion-shock/cluster_cats/sumsscat.Feb-16-2012.txt','r')

    queryra = queryra*deg2rad
    querydec = querydec*deg2rad


    maxsourceflux = 0.0
    totalsourceflux = 0.0
    numbersources = 0.0
    maxsourcesep = queryradius

    sourceras = np.array([])
    sourcedecs = np.array([])
    sourcefluxs = np.array([])
    sourcefields = np.array([])

    for source in sourcecat:
        source = source[:-1]
        source = source.split(' ')
        while '' in source:
            source.remove('')
        if '#' in source[0]:
            continue

        if abs(float(source[3])-querydec*rad2deg) > 1.5*(queryradius+1.0):
            continue
        sourcera = RA_J2000_to_radians(source[0],source[1],source[2])
        sourcedec = DEC_J2000_to_radians(source[3],source[4],source[5])
        flux = float(source[8])
        sourcefield = source[18]
        
        sourceras = np.append(sourceras,sourcera)
        sourcedecs = np.append(sourcedecs,sourcedec)
        sourcefluxs = np.append(sourcefluxs,flux)
        sourcefields = np.append(sourcefields,sourcefield)

    sourceseps = sepn(sourceras,sourcedecs,queryra,querydec)*rad2deg
    numsources = len(sourceseps)
    sourcedict = np.zeros( (numsources,) ,dtype=('f8,f8,f8,f8,a10'))
    for i in range(0,numsources):
        sourcedict[i][0] = sourceras[i]
        sourcedict[i][1] = sourcedecs[i]
        sourcedict[i][2] = sourcefluxs[i]
        sourcedict[i][3] = sourceseps[i]
        sourcedict[i][4] = sourcefields[i]

    closedict = filter(lambda (a,b,c,d,e): d<=queryradius,sourcedict)

    for source in closedict:

        ra = radians_to_RA_J2000(source[0])
        ra = '%s %s %s'%(ra[0],ra[1],ra[2] + ra[3]/100.0) 
        dec = radians_to_DEC_J2000(source[1])
        dec = '%s %s %s'%(dec[0],dec[1],dec[2] + dec[3]/100.0) 
        flux = source[2]
        sourcesep = source[3]

        pbtaper = exp(-(sourcesep*60.0)**2.0/(2*(pbeamfwhm/2.35482)**2.0))
        sourceflux = pbtaper*float(flux)

        totalsourceflux +=sourceflux
        numbersources += 1.0
            
        if sourceflux > maxsourceflux:
            maxsourceflux = sourceflux
            maxsourcesep = sourcesep

    sourcecat.close()
    # sourcefluxs are in mJy
    return maxsourceflux, maxsourcesep, totalsourceflux, numbersources, closedict

   

def query_nvss(queryra,querydec,queryradius,pbeamfwhm):
    # Given an RA, DEC, radius and primary beam this wil return information on sources in the vicinity
    # queryra,querydec and queryradius are in degrees
    # pbeamfwhm is in arcmin (for ATCA = 42.0)
    nvssname = '/net/kolkje/data2/shimwell/General/Total-Checked-Out-svn/my_codes/trunk/search_nvss/NVSS.fits'

    queryra = queryra*deg2rad
    querydec = querydec*deg2rad
    sourcecat = pyfits.open(nvssname)
    maxsourceflux = 0.0
    totalsourceflux = 0.0
    numbersources = 0.0
    maxsourcesep = queryradius

    nvssras = sourcecat[1].data['_RAJ2000']*deg2rad
    nvssdecs = sourcecat[1].data['_DEJ2000']*deg2rad
    flux = sourcecat[1].data['S1_4']
    fluxerr = sourcecat[1].data['e_S1_4']
    sourcefields = sourcecat[1].data['Field']
    nvsssep = sepn(nvssras,nvssdecs,queryra,querydec)*rad2deg
    
    numsources = len(sourcecat[1].data)
    nvssdict = np.zeros( (numsources,) ,dtype=('f8,f8,f8,f8,a10'))
    for i in range(0,numsources):
        nvssdict[i][0] = nvssras[i]
        nvssdict[i][1] = nvssdecs[i]
        nvssdict[i][2] = flux[i]
        #nvssdict[i][3] = fluxerr[i]
        nvssdict[i][3] =nvsssep[i]
        nvssdict[i][4] =sourcefields[i]
    closedict = filter(lambda (a,b,c,d,e): d<=queryradius,nvssdict)

    for source in closedict:
        ra = radians_to_RA_J2000(source[0])
        ra = '%s %s %s'%(ra[0],ra[1],ra[2] + ra[3]/100.0) 
        dec = radians_to_DEC_J2000(source[1])
        dec = '%s %s %s'%(dec[0],dec[1],dec[2] + dec[3]/100.0) 
        flux = source[2]
        #fluxerr = source[3] 
        sourcesep = source[3]

        pbtaper = exp(-(sourcesep*60.0)**2.0/(2*(pbeamfwhm/2.35482)**2.0))
        sourceflux = pbtaper*float(flux)

        totalsourceflux +=sourceflux
        numbersources += 1.0
            
        if sourceflux > maxsourceflux:
            maxsourceflux = sourceflux
            maxsourcesep = sourcesep


    sourcecat.close()
    return maxsourceflux, maxsourcesep, totalsourceflux, numbersources, closedict


def query_atca(queryra,querydec):
    atcacat = open('/Users/shi11n/Desktop/work/merging-clusters/cats/recent-atca-halos.txt','r')

    queryra = queryra*deg2rad
    querydec = querydec*deg2rad

    matchedatca = False

    for atcacluster in atcacat:
        atcacluster = atcacluster[:-1]
        atcacluster = atcacluster.split(' ')
        while '' in atcacluster:
            atcacluster.remove('')
        if '#' in atcacluster[0]:
            continue

        atcaraj2000h,atcaraj2000m,atcaraj2000s = float(atcacluster[1].split(':')[0]),float(atcacluster[1].split(':')[1]),float(atcacluster[1].split(':')[2])
        atcadecj2000d,atcadecj2000m,atcadecj2000s = float(atcacluster[2].split(':')[0]),float(atcacluster[2].split(':')[1]),float(atcacluster[2].split(':')[2])
        
        atcara =  RA_J2000_to_radians(atcaraj2000h,atcaraj2000m,atcaraj2000s)
        atcadec = DEC_J2000_to_radians(atcadecj2000d,atcadecj2000m,atcadecj2000s)
        atcasep = sepn(atcara,atcadec,queryra,querydec)*rad2deg
        if atcasep < 1.0:
            matchedatca = True
            matchedatcaob = atcacluster[0]
            matchedatcasep = atcasep

    atcacat.seek(0,0)
    
    return matchedatca



def query_first(queryra,querydec,queryradius):
    # Given an RA, DEC, radius and primary beam this wil return information on sources in the vicinity
    # queryra,querydec and queryradius are in degrees


    firstname = '/net/kolkje/data2/shimwell/General/Total-Checked-Out-svn/my_codes/trunk/search_first/first_14mar04.fits'
  
    queryra = queryra*deg2rad
    querydec = querydec*deg2rad

    first = pyfits.open(firstname)
    firstras = first[1].data['RA']*deg2rad
    firstdecs = first[1].data['DEC']*deg2rad
    flux = first[1].data['FPEAK']
    fluxerr = first[1].data['RMS']
    firstfield = first[1].data['FLDNAME']
    firstmajor = first[1].data['MAJOR']
    firstsep = sepn(firstras,firstdecs,queryra,querydec)*rad2deg
    numsources = len(first[1].data)
    firstdict = np.zeros( (numsources,) ,dtype=('f8,f8,f8,f8,f8,a10,f8'))
    first.close()

    for i in range(0,numsources):
        firstdict[i][0] = firstras[i]
        firstdict[i][1] = firstdecs[i]
        firstdict[i][2] = flux[i]
        firstdict[i][3] = fluxerr[i]
        firstdict[i][4] =firstsep[i]
        firstdict[i][5] = firstfield[i]
        firstdict[i][6] = firstmajor[i]
        
    closedict = filter(lambda (a,b,c,d,e,f,g): e<=queryradius,firstdict)

    print 'Found sources %s sources ' %(len(closedict))
    for source in closedict:
        ra = radians_to_RA_J2000(source[0])
        ra = '%s %s %s'%(ra[0],ra[1],ra[2] + ra[3]/100.0) 
        dec = radians_to_DEC_J2000(source[1])
        dec = '%s %s %s'%(dec[0],dec[1],dec[2] + dec[3]/100.0) 
        flux = source[2]
        fluxerr = source[3] 
        sep = source[4]
        field = source[5]
        majorax = source[6]

    return closedict
