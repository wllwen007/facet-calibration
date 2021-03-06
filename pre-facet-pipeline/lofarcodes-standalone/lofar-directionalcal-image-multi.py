#!bin/python
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pylab as pylab
import os,sys
import time
scriptdir = os.path.dirname(os.path.realpath(__file__)+'/aux-lib')
sys.path.append(scriptdir)
scriptdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(scriptdir)
from lofar_general import *
from pythoncodes.astronomy import *
from pythoncodes.inputs import *
from pythoncodes.fits import *
from pythoncodes.maths import *
import lofar.bdsm as bdsm
import pyfits
import glob
import multiprocessing as mp
import argparse
from astropy.wcs import WCS
import pyrap.tables as pt
import pyrap.images as pim

print 'Inputs should be:'
print 'msfile with amplitude calibrated data in DATA and GSM calibrated in CORRECTED DATA'
print 'The LOFAR image should be the GSM calibrated image'
print 'The LOFAR model should be the primary beam corrected model'

parser = argparse.ArgumentParser() 
parser.add_argument('msin', help="Give LOFAR msfile")
parser.add_argument('imagein', help="initial LOFAR image")
parser.add_argument('-f', '--workdir', dest='workdir', default='directional_cal', help="working directory")
parser.add_argument('-n', '--numsource', dest='numsource', default=1, help="number of sources to dircal")
parser.add_argument('-j', '--ncpus', dest='ncpus', default=8, help="number of sources to dircal")

args = parser.parse_args()
orig_lofar_msfile = args.msin
orig_lofar_image = args.imagein
workingdir = args.workdir
numsources = int(args.numsource)
ncpus = int(args.ncpus)

print orig_lofar_msfile
new_lofar_msfile = 'datafile.ms'
new_lofar_image = 'image_orig'

startdir = os.getcwd()

starttime = time.time()
loggingfilename = '%s/lofar-dircal-multi-logging.txt'%startdir
loggingfile = open(loggingfilename,'w')
loggingfile.write('Start time %s \n'%(time.time()))
loggingfile.close()

# Check for existing files to resume from or set up a new directory structure
if os.path.exists('%s'%workingdir):
    print '%s exists -- will check to resume '%workingdir
    os.chdir(workingdir)
    os.system('mkdir old_run_%s'%starttime)
    os.system('mv ./* old_run_%s'%starttime)
    os.system('mv old_run_%s/Iter* .'%starttime)
    os.system('mv old_run_%s/startingfiles .'%starttime)
else:
    os.system('mkdir %s'%workingdir)
    os.system('cp -r %s %s/%s'%(orig_lofar_msfile,workingdir,new_lofar_msfile))
    os.system('cp -r %s %s/%s'%(orig_lofar_image,workingdir,new_lofar_image))
    os.chdir(workingdir)
    os.system('mkdir startingfiles')
    os.system('cp -r ./* startingfiles/')

# Extract the N brightest sources from the initial image.
img = bdsm.process_image('startingfiles/%s'%new_lofar_image,adaptive_rms_box='True',advanced_opts='True',detection_image="startingfiles/%s"%new_lofar_image,thresh_isl=6,thresh_pix=8,blank_limit=1E-4,atrous_do='True')
img.write_catalog(outfile="%s_sources.fits"%new_lofar_image,catalog_type='gaul',format='fits',correct_proj='True') 
img.export_image(outfile="%s_pydbsm_mask"%new_lofar_image,img_type='island_mask',img_format='casa')
f = pyfits.open('%s_sources.fits'%new_lofar_image)
fluxes = f[1].data['PEAK_FLUX'].copy()
f.close()
fluxes.sort()
fluxes = sorted(fluxes,reverse=True)
fluxes = fluxes[:]
sourcelist = {}
sourcecounter = 0
for flux in fluxes[:]:
    if sourcecounter >= numsources:
        sourcecounter +=1
        break
    for source in f[1].data:
        if sourcecounter >= numsources:
            sourcecounter+=1
            break
        if source['PEAK_FLUX'] == flux:
            minseparation = 99999.0
            if sourcecounter == 0:
                sourcelist[source['PEAK_FLUX']] = [source['Gaus_id'],source['RA'],source['DEC'],0.0]
                sourcecounter +=1
                if sourcecounter == numsources:
                    break
            else:
                for chosensource in sourcelist:
                    separation = sepn(source['RA']*deg2rad,source['DEC']*deg2rad,sourcelist[chosensource][1]*deg2rad,sourcelist[chosensource][2]*deg2rad)
                    if separation < minseparation:
                        minseparation = separation
                if minseparation*rad2deg >  0.1:
                    sourcelist[source['PEAK_FLUX']] = [source['Gaus_id'],source['RA'],source['DEC'],minseparation*rad2deg]
                    sourcecounter +=1
                    if sourcecounter == numsources:
                        break
filteredfluxes = np.array([])
for chosensource in sourcelist:
    filteredfluxes = np.append(filteredfluxes,chosensource)
    os.system("echo 'Source %s %s (%s %s) chosen. This is the %s brightest source ' >> %s"%(sourcelist[chosensource][1],sourcelist[chosensource][2],radians_to_RA_J2000(sourcelist[chosensource][1]*deg2rad),radians_to_DEC_J2000(sourcelist[chosensource][2]*deg2rad),np.where(fluxes==chosensource),loggingfilename))

fluxes = filteredfluxes
fluxes.sort()
fluxes = sorted(fluxes,reverse=True)





# Find file informatation
infodict = find_fileinfo('startingfiles/'+new_lofar_msfile,'file-info.txt')
resolution = calc_resolution(infodict['Ref Freq'],5000.0)*rad2arcsec
cellsize = str(round(resolution/5.0,2)) + 'arcsec'
iterations,threshold = 300000,'%smJy'%(np.max(infodict['Est Noise']*10.0,np.max(fluxes)/100.0))

# Log time taken to prepare for subtraction.
os.system("echo '@@@@@ Setup for subtraction took %s ' >> %s"%(time.time()-starttime,loggingfilename))
previoustime = time.time()

# Loop through the N brightest sources subtracting them

i=0
for flux in fluxes:
    source = sourcelist[flux]
    source_ra,source_dec = source[1],source[2]
    os.system("echo 'Looking at %s %s (%s,%s)' >> %s"%(source_ra,source_dec,radians_to_RA_J2000(source_ra*deg2rad),radians_to_DEC_J2000(source_dec*deg2rad),loggingfilename))
    
    # Check if resumable
    if os.path.exists('Iter%s'%i):
        dirlist = glob.glob('*')
        itersdone = []
        for listofiles in dirlist:
            if listofiles[:4] == 'Iter':
                itersdone.append(float(listofiles.replace('Iter','')))
        maxiterdone = np.max(itersdone)
        os.system("echo 'Iterations up to %s have already been completed will resume with %s iteration' >> %s"%(np.max(itersdone),np.max(itersdone)+1,loggingfilename))
        if i !=maxiterdone:
            i+=1
            continue
        else:
            os.system('cp -r Iter%s/source_%s.MS .'%(i,i))
            os.system('casapy2bbs.py --mask=Iter%s/newphase_postsub_iter%s_pydbsm_mask Iter%s/newphase_postsub_maskiter%s.model.corr latestmodel%s.bbs'%(i,i,i,i,i))
            new_lofar_msfile = 'source_%s.MS'%i
            latestmodel = 'latestmodel%s.bbs'%i
            i+=1
            continue        
    
    
    os.system('cp -r %s source_%s.MS'%(new_lofar_msfile,i))
    new_lofar_msfile = 'source_%s.MS'%i


    # Perform imaging of the field
    aw_imagedata(new_lofar_msfile,'awimager_inputs_presub','image_presub',iterations,threshold,'10arcsec',0.15,4.0,3072,'mfclark','')
    img = bdsm.process_image('image_presub.restored',adaptive_rms_box='True',advanced_opts='True',detection_image='image_presub.restored',thresh_isl=6,thresh_pix=8,blank_limit=1E-4,atrous_do='True')
    img.export_image(outfile="mask_image_presub",img_type='island_mask',img_format='casa')
    os.system('image2fits in=image_presub.restored out=image_presub.restored.fits')
    f = pyfits.open('image_presub.restored.fits')
    noisearray = f[0].data.flatten()
    maxpixel = np.max(noisearray)
    noisearray = np.random.permutation(noisearray)[:10000]
    noisepix = np.array(filter(lambda x: abs(x) > 10E-8,noisearray))
    noisepix = np.array(filter(lambda x: abs(x)<infodict['Est Noise']*50.0/1000.0,noisepix))
    rms = fit_gaussian_histogram(noisepix,'n')
    rms = np.max([rms,maxpixel/1000.0])
    f.close()
    boxthreshold = str(rms*1.0*1000.0) +'mJy'
    threshold = str(rms*5.0*1000.0) +'mJy'
    aw_imagedata(new_lofar_msfile,'awimager_inputs','image_presub_noiseclean',iterations,boxthreshold,'10arcsec',0.15,4.0,3072,'mfclark','mask_image_presub')
    new_lofar_model = 'image_presub_noiseclean.model.corr'
    os.system("echo '@@@@@ For Iter %s initial imaging took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Identify the source for subtracting in the clean component images and make BBS models of the target soure and the rest of the field
    os.system('image2fits in=%s out=%s.fits'%(new_lofar_model,new_lofar_model))
    #topcorner = find_pixel('%s.fits'%new_lofar_model,source_dec+0.1,source_ra-0.1)
    #bottomcorner = find_pixel('%s.fits'%new_lofar_model,source_dec-0.1,source_ra+0.1)
    w = WCS('%s.fits'%new_lofar_model)
    topcorner = int(w.wcs_world2pix(source_ra-0.1,source_dec+0.1,0,0,1)[1]),int(w.wcs_world2pix(source_ra-0.1,source_dec+0.1,0,0,1)[0])
    bottomcorner = int(w.wcs_world2pix(source_ra+0.1,source_dec-0.1,0,0,1)[1]),int(w.wcs_world2pix(source_ra+0.1,source_dec-0.1,0,0,1)[0])

    os.system('cp -r %s OUTSIDE.model'%new_lofar_model)
    image1 = pim.image('OUTSIDE.model')
    imshape = image1.shape()
    dataarray = image1.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    dataarray[0,0,bottomcorner[0]:topcorner[0],bottomcorner[1]:topcorner[1]] = 0.0
    image1.putdata(dataarray,blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    os.system('cp -r %s TARGET.model'%new_lofar_model)
    image1 = pim.image('TARGET.model')
    imshape = image1.shape()
    dataarray = image1.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    dataarray[0,0,:bottomcorner[0],:] = 0.0
    dataarray[0,0,:,:bottomcorner[1]] = 0.0
    dataarray[0,0,topcorner[0]:,:] = 0.0
    dataarray[0,0,:,topcorner[1]:] = 0.0
    image1.putdata(dataarray,blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    image1.unlock()
    os.system('cp -r mask_image_presub TARGET.mask')
    image1 = pim.image('TARGET.mask')
    imshape = image1.shape()
    dataarray = image1.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    dataarray[0,0,:bottomcorner[0],:] = 0.0
    dataarray[0,0,:,:bottomcorner[1]] = 0.0
    dataarray[0,0,topcorner[0]:,:] = 0.0
    dataarray[0,0,:,topcorner[1]:] = 0.0
    image1.putdata(dataarray,blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    image1.unlock()
    os.system('casapy2bbs.py --mask=mask_image_presub   OUTSIDE.model OUTSIDE.bbs')
    os.system('casapy2bbs.py --mask=mask_image_presub TARGET.model TARGET.bbs')
    os.system("echo '@@@@@ For Iter %s manipulating the models took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Subtract the field apart from the target source
    os.system('cp -r %s/instrument tmpparmdb'%new_lofar_msfile)
    newfiles = split_equal_chunks(new_lofar_msfile,'./splitA',infodict['inttime'],ncpus,infodict['Obsdate_start'],infodict['Obsdate_end'])
    splittimes = np.arange(0,infodict['inttime'],infodict['inttime']/ncpus)
    timedif =  infodict['inttime']/ncpus
    for t in range(0,len(newfiles)):
        split_parmdbs_copy('tmpparmdb','%s_tmpparmdb'%newfiles[t],splittimes[t],splittimes[t]+timedif)
    for newfile in newfiles:
        process=mp.Process(target=subtract_cleancomponents_data_bbs,args=('%s'%newfile,'%s_tmpparmdb'%newfile,'BBSsubrun%s_%s'%(i,newfiles.index(newfile)),'OUTSIDE.bbs',1))
        process.start()
        while len(mp.active_children()) >= ncpus:
            print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
            time.sleep(10)
    time.sleep(60) #Just to give a little break incase they are taking a min to start
    while len(mp.active_children()) >= 1:
        print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
        time.sleep(10)    
    os.system('rm -rf %s'%new_lofar_msfile)
    combinelist = ' '.join(newfiles)
    os.system('python %s/aux-scripts/concat.py %s %s'%(scriptdir,new_lofar_msfile,combinelist))
    os.system('cp -r tmpparmdb %s/instrument'%new_lofar_msfile)
    os.system("echo '@@@@@ For Iter %s subtracting the field sources took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    os.system('rm -rf splitA')
    previoustime = time.time()

    # Phase shift to the target source and average the phase shifted data
    phaseshift('ndppp_source_%s.parset'%i,new_lofar_msfile,[source_ra,source_dec],'source_%s_phase.MS'%i,'DATA','DATA')
    new_lofar_msfile = 'source_%s_phase.MS'%i
    combine_measurementsets(['%s'%new_lofar_msfile],'source_%s_phase_avg.MS'%i,'combine.log',20,1,'DATA')
    new_lofar_msfile = 'source_%s_phase_avg.MS'%i
    os.system("echo '@@@@@ For Iter %s phaseshifting to the target source took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Phase calibrate the phase shifted data on the target and image
    phase_calibratedata('%s'%new_lofar_msfile,'TARGET.bbs','bbs-postsub.parset',150,9999999,4,1)
    os.system("echo '@@@@@ For Iter %s calibrating the phase shifted data took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    aw_imagedata(new_lofar_msfile,'awimager_inputs_postsub','image_postsub',0,threshold,'10arcsec',0.15,4.0,3096,'mfclark','')
    os.system("echo '@@@@@ For Iter %s imaging the calibrated phase shifted data took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))   
    previoustime = time.time()

    # Run selfcal and get final high resolution iamges
    selfcalfile=open('run_selfcal.sh','w')
    selfcalfile.write('python %s/lofar-selfcal-image.py <<EOF \n'%scriptdir)
    selfcalfile.write('%s\n'%new_lofar_msfile)
    selfcalfile.write('%s/selfcal\n'%os.getcwd())
    selfcalfile.write('y\n')
    selfcalfile.write('0.3\n')
    selfcalfile.write('high\n')
    selfcalfile.write('30\n')	
    selfcalfile.write('%s\n'%ncpus)
    selfcalfile.write('y\n')
    selfcalfile.write('y\n')
    selfcalfile.write('%s\n'%(flux))
    selfcalfile.write('<<EOF\n')
    selfcalfile.close()
    os.system('chmod +x run_selfcal.sh')
    os.system('./run_selfcal.sh')
    os.system('cp -r selfcal/FINAL_IMAGE_*.model.corr HIGHRES%s.model'%i)
    os.system('cp -r selfcal/final_mask_IMAGE_* MASK6')
    os.system('casapy2bbs.py --mask=MASK6 HIGHRES%s.model HIGHRES%s.bbs'%(i,i))
    os.system("echo '@@@@@ For Iter %s selfcalibration took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Amp and phase calibrate the pre phase shifted data and image
    new_lofar_msfile = 'source_%s.MS'%i
    newfiles = split_equal_chunks(new_lofar_msfile,'./splitB',infodict['inttime'],ncpus,infodict['Obsdate_start'],infodict['Obsdate_end'])
    for newfile in newfiles:
        process=mp.Process(target=ampphase_calibratedata,args=('%s'%newfile,'HIGHRES%s.bbs'%i,'highresampphase_bbs.parset',150,9999999,4,1))
        process.start()
        while len(mp.active_children()) >= ncpus:
            print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
            time.sleep(10)
    time.sleep(60) #Just to give a little break incase they are taking a min to start
    while len(mp.active_children()) >= 1:
        print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
        time.sleep(10) 
    for newfile in newfiles:
        smooth_solutions(30,newfile,'T')
    combinelist = ' '.join(newfiles)
    os.system('rm -rf %s'%new_lofar_msfile)
    os.system('python %s/aux-scripts/concat.py %s %s'%(scriptdir,new_lofar_msfile,combinelist))
    concat_parmdbs_copy(newfiles,new_lofar_msfile,'instrument','instrument')
    os.system('rm -rf splitB')
    os.system("echo '@@@@@ For Iter %s amp and phase calibrating the pre phase shifted data took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()

    aw_imagedata(new_lofar_msfile,'awimager_inputs','image_newcal_iter%s'%i,iterations,threshold,'10arcsec',0.15,4.0,3072,'mfclark','TARGET.mask')
    os.system('cp -r %s/instrument tmpparm%s'%(new_lofar_msfile,i))
    os.system("echo '@@@@@ For Iter %s imaging the calibrated field subtracted data took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()

    
    # Subtract the cleancomponents of the highresolution using the instrument table obtained from the high resolution calibration
    newfiles = split_equal_chunks(new_lofar_msfile,'./splitC',infodict['inttime'],ncpus,infodict['Obsdate_start'],infodict['Obsdate_end'])
    splittimes = np.arange(0,infodict['inttime'],infodict['inttime']/ncpus)
    timedif = infodict['inttime']/ncpus
    for t in range(0,len(newfiles)):
        split_parmdbs_copy('tmpparm%s'%i,'%s_tmpparm%s'%(newfiles[t],i),splittimes[t],splittimes[t]+timedif)
    for newfile in newfiles:
        process=mp.Process(target=subtract_cleancomponents_data_bbs_nophasors,args=(newfile,'%s_tmpparm%s'%(newfile,i),'BBSsubrun_highres%s'%i,'HIGHRES%s.bbs'%i,1))
        process.start()
        while len(mp.active_children()) >= ncpus:
            print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
            time.sleep(10)
    time.sleep(60) #Just to give a little break incase they are taking a min to start
    while len(mp.active_children()) >= 1:
        print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
        time.sleep(10)    
    os.system('rm -rf %s'%new_lofar_msfile)
    combinelist = ' '.join(newfiles)
    os.system('python %s/aux-scripts/concat.py %s %s'%(scriptdir,new_lofar_msfile,combinelist))
    os.system('cp -r tmpparmdb %s/instrument'%(new_lofar_msfile))
    os.system("echo '@@@@@ For Iter %s subtracting the high resolution target clean components took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    os.system('rm -rf splitC')
    previoustime = time.time()


    # Add back the field data using the same instrument table that was used for the subtraction of the field data
    os.system('casapy2bbs.py --mask=mask_image_presub OUTSIDE.model OUTSIDE.bbs')
    newfiles = split_equal_chunks(new_lofar_msfile,'./splitD',infodict['inttime'],ncpus,infodict['Obsdate_start'],infodict['Obsdate_end'])
    splittimes = np.arange(0,infodict['inttime'],infodict['inttime']/ncpus)
    timedif = infodict['inttime']/ncpus
    for t in range(0,len(newfiles)):
        split_parmdbs_copy('tmpparmdb','%s_tmpparmdb'%(newfiles[t]),splittimes[t],splittimes[t]+timedif)
    for newfile in newfiles:
        process=mp.Process(target=add_cleancomponents_data_bbs,args=(newfile,'%s_tmpparmdb'%newfile,'BBSaddrun%s'%i,'OUTSIDE.bbs',1))
	process.start()
        while len(mp.active_children()) >= ncpus:
            print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
            time.sleep(10)
    time.sleep(60) #Just to give a little break incase they are taking a min to start
    while len(mp.active_children()) >= 1:
        print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
        time.sleep(10)    
    os.system('rm -rf %s'%new_lofar_msfile)
    combinelist = ' '.join(newfiles)
    os.system('python %s/aux-scripts/concat.py %s %s'%(scriptdir,new_lofar_msfile,combinelist))
    os.system('cp -r tmpparmdb %s/instrument'%(new_lofar_msfile))
    os.system("echo '@@@@@ For Iter %s adding back the field clean components took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    os.system('rm -rf splitD')
    previoustime = time.time()


    # Phase calibrate the data on the model with out the subtracted source
    newfiles = split_equal_chunks(new_lofar_msfile,'./splitE',infodict['inttime'],ncpus,infodict['Obsdate_start'],infodict['Obsdate_end'])
    for newfile in newfiles:
        process=mp.Process(target=phase_calibratedata,args=(newfile,'OUTSIDE.bbs','outsidephase_bbs.parset',150,9999999,4,1))
        process.start()
        while len(mp.active_children()) >= ncpus:
            print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
            time.sleep(10)
    time.sleep(60) #Just to give a little break incase they are taking a min to start
    while len(mp.active_children()) >= 1:
        print len(mp.active_children()),'still running subtraction',time.asctime(time.gmtime())
        time.sleep(10) 
    combinelist = ' '.join(newfiles)
    os.system('rm -rf %s'%new_lofar_msfile)
    os.system('python %s/aux-scripts/concat.py %s %s'%(scriptdir,new_lofar_msfile,combinelist))
    concat_parmdbs_copy(newfiles,new_lofar_msfile,'instrument','instrument')
    os.system('rm -rf splitE')
    os.system("echo '@@@@@ For Iter %s phase calibrating the target source subtracted field took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Image the source subtracted data
    aw_imagedata(new_lofar_msfile,'awimager_inputs','image_postsub_iter%s'%i,iterations,threshold,'10arcsec',0.15,4.0,3072,'mfclark','')
    img = bdsm.process_image('image_postsub_iter%s.restored'%i,adaptive_rms_box='True',advanced_opts='True',detection_image="image_postsub_iter%s.restored"%i,thresh_isl=6,thresh_pix=8,blank_limit=1E-4,atrous_do='True')
    img.export_image(outfile="image_postsub_iter%s_pydbsm_mask"%i,img_type='island_mask',img_format='casa')
    aw_imagedata(new_lofar_msfile,'awimager_inputs','image_postsub_maskiter%s'%i,iterations,boxthreshold,'10arcsec',0.15,4.0,3072,'mfclark',"image_postsub_iter%s_pydbsm_mask"%i)
    os.system("echo '@@@@@ For Iter %s imaging the field took %s ' >> %s"%(i,time.time()-previoustime,loggingfilename))
    previoustime = time.time()


    # Prepare for the next iteration of source subtraction
    latestmodel = 'latestmodel%s.bbs'%i
    os.system('mkdir Iter%s'%i)
    os.system('mv ./* Iter%s'%i)
    os.system('mv Iter%s/Iter* .'%i)
    os.system('mv Iter%s/startingfiles .'%i)
    os.system('cp -r Iter%s/source_%s.MS .'%(i,i))
    os.system('casapy2bbs.py --mask=Iter%s/image_postsub_iter%s_pydbsm_mask Iter%s/image_postsub_maskiter%s.model.corr latestmodel%s.bbs'%(i,i,i,i,i))
    new_lofar_msfile = 'source_%s.MS'%i
    i+=1


