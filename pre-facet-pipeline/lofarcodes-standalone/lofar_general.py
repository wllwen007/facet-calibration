import os,sys
import numpy as np
import psutil
import lofar.parmdb as lp
import glob
import time
scriptdir = os.path.dirname(os.path.realpath(__file__)+'/aux-lib')
sys.path.append(scriptdir)
scriptdir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(scriptdir)
from pythoncodes.astronomy import *
import lofar.bdsm as bdsm
import pyrap.tables as pt
import pyrap.images as pim


def split_parmdbs_copy(inparmdb,outparmdb,time1,time2):
    """ Concat a time ordered list of parmdbs -- taken from https://github.com/darafferty/Ion/blob/master/ion_image.py -- THIS COPIES THE DEFAULT VALUES FROM THE FIRST IMAGE."""
    if os.path.exists(outparmdb):
        print 'Parmdb exists so cant concatenate'
        sys.exit(0)
    os.system('cp -r %s %s'%(inparmdb,outparmdb))
    pdb_split = lp.parmdb(outparmdb)
    
    for parmname in pdb_split.getNames():
        pdb_split.deleteValues(parmname)
    pdb = lp.parmdb(inparmdb)
    starttime,endtime = lp.parmdb(inparmdb).getRange()[2:]
    for parmname in pdb.getNames():
        v = pdb.getValuesGrid(parmname,stime=starttime+time1,etime=starttime+time2)
        pdb_split.addValues(v)
    pdb_split.flush()
    pdb.flush()
    return



def concat_parmdbs(msnames,outdir,inparmdb,outparmdb):
    """ Concat a time ordered list of parmdbs -- taken from https://github.com/darafferty/Ion/blob/master/ion_image.py -- THIS DOES NOT COPY THE DEFAULT VALUES"""
    if os.path.exists(outparmdb):
        print 'Parmdb exists so cant concatenate'
        sys.exit(0)
    pdb_concat = lp.parmdb(outdir+'/'+outparmdb, create=True)
    for msname in msnames:
        print msname
        pdb = lp.parmdb(msname + "/" + inparmdb)
        for parmname in pdb.getNames():
            v = pdb.getValuesGrid(parmname)
            pdb_concat.addValues(v)
    pdb_concat.flush()
    return

def concat_parmdbs_copy(msnames,outdir,inparmdb,outparmdb):
    """ Concat a time ordered list of parmdbs -- taken from https://github.com/darafferty/Ion/blob/master/ion_image.py -- THIS COPIES THE DEFAULT VALUES FROM THE FIRST IMAGE."""
    if os.path.exists(outparmdb):
        print 'Parmdb exists so cant concatenate'
        sys.exit(0)
    os.system('cp -r %s/%s %s/%s'%(msnames[0],inparmdb,outdir,outparmdb))
    pdb_concat = lp.parmdb(outdir+'/'+outparmdb)
    
    for parmname in pdb_concat.getNames():
        pdb_concat.deleteValues(parmname)

    for msname in msnames:
        print msname
        pdb = lp.parmdb(msname + "/" + inparmdb)
        for parmname in pdb.getNames():
            v = pdb.getValuesGrid(parmname)
            pdb_concat.addValues(v)
    pdb_concat.flush()
    return




def split_htmlfile(htmlfilename,begsub,endsub,outhtmlfilename,numberofsubbbands):
    htmlfile = open('%s'%htmlfilename,'r')
    outhtmlfile = open('%s'%outhtmlfilename,'w')
    subbandrange = np.arange(begsub,endsub,1)
    numberwritten = 0
    for line in htmlfile:
        for subband in subbandrange:
            if 'SB%s_'%int(subband) in line  or 'SB%s_'%(int(subband)+numberofsubbbands) in line:
                outhtmlfile.write(line)
                numberwritten+=1
            if 'SB0%s_'%int(subband) in line  or 'SB0%s_'%(int(subband)+numberofsubbbands) in line:
                outhtmlfile.write(line)
                numberwritten+=1
            if 'SB00%s_'%int(subband) in line  or 'SB00%s_'%(int(subband)+numberofsubbbands) in line:
                outhtmlfile.write(line)
                numberwritten+=1
                
    outhtmlfile.close()
    if numberwritten == 0:
        print 'No subbands in the range %s to %s'%(begsub,endsub)
        os.system('rm %s'%outhtmlfilename)
    return
                
        

def split_equal_chunks(new_lofar_msfile,outputdirectory,totaltime,numberchunks,startdate,enddate):

    splittimes = np.arange(0,totaltime,totaltime/numberchunks)
    splittimes = splittimes/(60.0*60.0)
    newfiles = []
    os.system('mkdir %s'%outputdirectory)
    for i in range(0,len(splittimes)):
        starttime = splittimes[i]
        try:
            endtime = splittimes[i+1]
        except IndexError:
            endtime = totaltime/(60.0*60.0)
        tmpfile=open('timesplit.sh','w')
        tmpfile.write('python %s/aux-scripts/split_dataset.py <<EOF\n'%scriptdir)
        tmpfile.write('%s\n'%new_lofar_msfile)
        tmpfile.write('%s/%s_%s.ms\n'%(outputdirectory,starttime,endtime))
        tmpfile.write('%s\n'%starttime)
        tmpfile.write('%s\n'%endtime)
        tmpfile.write('<<EOF\n')
        tmpfile.close()
	os.system('chmod +x timesplit.sh')
        os.system('./timesplit.sh')
	
	#tmpfile=open('ndppp_edit.sh','w')
	#tmpfile.write('msin=%s/%s_%s.ms\n'%(outputdirectory,starttime,endtime))
	#tmpfile.write('msout=%s/%s_%s_editmeta.ms\n'%(outputdirectory,starttime,endtime))
	#tmpfile.write('msin.sort=true\n')
	#tmpfile.write('msin.missingdata = true\n')
	#tmpfile.write('msin.orderms=False\n')
	#tmpfile.write('msin.autoweight = false\n')
	#tmpfile.write('msin.forceautoweight = false\n')
	#tmpfile.write('msin.datacolumn = DATA\n')
	#tmpfile.write('msin.starttime=%s\n'%startdate)
	#tmpfile.write('msin.endtime=%s\n'%enddate)
	#tmpfile.write('steps=[]\n')
	#tmpfile.close()
	#os.system('NDPPP ndppp_edit.sh')

        newfiles.append('%s/%s_%s.ms'%(outputdirectory,starttime,endtime))
    return newfiles



def deeper_2nd_clean(origimagename,newimagename,new_lofar_msfile,iterations,threshold,cellsize,uvmin,uvmax,npix,operation,cutthreshold,robust,brightthres):
    # copy the avg, spheroid_cut, model, etc etc files to the newimagename
    if origimagename != newimagename:
        os.system('cp -r %s0.avgpb %s0.avgpb'%(origimagename,newimagename))
        os.system('cp -r %s0.spheroid_cut %s0.spheroid_cut'%(origimagename,newimagename))
        os.system('cp -r %s0.spheroid_cut_im %s0.spheroid_cut_im'%(origimagename,newimagename))
        os.system('cp -r %s.model %s.model'%(origimagename,newimagename))
        os.system('cp -r %s.model.corr %s.model.corr'%(origimagename,newimagename))
        os.system('cp -r %s.psf %s.psf'%(origimagename,newimagename))
        os.system('cp -r %s.residual %s.residual'%(origimagename,newimagename))
        os.system('cp -r %s.residual.corr %s.residual.corr'%(origimagename,newimagename))
        os.system('cp -r %s.restored %s.restored'%(origimagename,newimagename))
        os.system('cp -r %s.restored.corr %s.restored.corr'%(origimagename,newimagename))

    img = bdsm.process_image('%s.restored'%newimagename,advanced_opts='True',detection_image='%s.restored'%newimagename,thresh_isl=3,thresh_pix=5,blank_limit=1E-4,adaptive_rms_box='True',adaptive_thresh='%s'%brightthres)#,atrous_do='True')
    img.export_image(outfile="all_mask_%s"%newimagename,img_type='island_mask',img_format='casa',clobber=True)
    img.export_image(outfile="rms_%s"%newimagename,img_type='rms',img_format='casa',clobber=True)

    #img = bdsm.process_image('%s.restored'%newimagename,advanced_opts='True',detection_image='%s.restored'%newimagename,thresh_isl=6,thresh_pix=100,blank_limit=1E-4)#,atrous_do='True')
    #img.export_image(outfile="bright_mask_%s"%newimagename,img_type='island_mask',img_format='casa')
    os.system('cp -r all_mask_%s tmp_mask_%s'%(newimagename,newimagename))

    # Subtract the mask images.
    image1 = pim.image("all_mask_%s"%newimagename)
    imshape = image1.shape()
    dataarray1 = image1.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])

    #image2 = pim.image("bright_mask_%s"%newimagename)
    #imshape = image1.shape()
    #dataarray2 = image2.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])

    image3 = pim.image("rms_%s"%newimagename)
    imshape = image1.shape()
    dataarray3 = image3.getdata(blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    
    newmaskdata = dataarray1#-dataarray2
    newmaskdata = newmaskdata.clip(0)
    floatthreshold = float(threshold.replace('mJy','E-3'))
    floatcutthreshold = float(cutthreshold.replace('mJy','E-3'))
    newmaskdata[np.where(dataarray3 > floatcutthreshold)] = 0
    newmaskdata[np.where(np.isnan(dataarray3))] = 0    

    image3 = pim.image('tmp_mask_%s'%newimagename)
    image3.putdata(newmaskdata,blc=[0,0,0,0], trc=[imshape[0]-1,imshape[1]-1,imshape[2]-1,imshape[3]-1])
    image3.saveas('withoutbright_mask_%s'%newimagename)

    aw_imagedata('%s'%new_lofar_msfile,'aw_imager_deeper_%s.inp'%newimagename,'%s'%newimagename,iterations,threshold,cellsize,uvmin,uvmax,npix,operation,'withoutbright_mask_%s'%newimagename,robust)

    return

def find_imagesize(skymodel,fieldra,fielddec):
    infile = open(skymodel,'r')
    pbeamfwhm = 4.0*60.0
    dessep = 2.5
    brightestsource = 0.0
    for line in infile:
        line = line[:-1]
        line = line.split(',')
        if '#' in line[0] and 'format' not in line[-1]:
            continue
        if 'FORMAT' in line[0] or 'format' in line[-1]:
            for i in range(0,len(line)):
                if 'Ra' in line[i]:
                    rapos = i
                if 'Dec' in line[i]:
                    decpos = i
                if line[i] == ' I':
                    fluxpos = i
            continue
        if len(line) == 1:
            continue
        rah,ram,ras = float(line[rapos].split(':')[0]),float(line[rapos].split(':')[1]),float(line[rapos].split(':')[2])
        decd,decm,decs = float(line[decpos].split('.')[0]),float(line[decpos].split('.')[1]),float(line[decpos].split('.')[2])
        rarad = RA_J2000_to_radians(rah,ram,ras)
        decrad = DEC_J2000_to_radians(decd,decm,decs)
        sourcesep = sepn(rarad,decrad,fieldra,fielddec)*rad2deg
        pbtaper = exp(-(sourcesep*60.0)**2.0/(2*(pbeamfwhm/2.35482)**2.0))
        flux = float(line[fluxpos])
        apparentflux = pbtaper*flux
        if apparentflux > 1.0 and sourcesep > (dessep-0.2):
            print 'Furthest bright source',sourcesep,dessep
            
            dessep = np.max([dessep,sourcesep])+0.2 # Make the field 0.1deg larger than required.
            print 'Updated dessep',dessep
        if apparentflux > brightestsource:
	    brightestsource = apparentflux
	    print 'brightest source',apparentflux, flux,pbtaper, sourcesep,rarad,decrad
    print dessep
    if dessep > 4.0:
        return 4.0,10.0
    return dessep,brightestsource




def ateam_clip(parsetname,msfile):
        parset = open(parsetname,'w')
        parset.write('Strategy.InputColumn = DATA\n')
        parset.write('Strategy.ChunkSize = 50\n')
        parset.write('Strategy.UseSolver = F\n')
        parset.write('Strategy.Steps = [predict4]\n')

        parset.write('Step.predict4.Model.Sources         = [VirA_4_patch,CygAGG,CasA_4_patch,TauAGG]\n')
        parset.write('Step.predict4.Model.Cache.Enable    = T\n')
        parset.write('Step.predict4.Model.Gain.Enable     = F\n')
        parset.write('Step.predict4.Operation             = PREDICT\n')
        parset.write('Step.predict4.Output.Column         = MODEL_DATA\n')
        parset.write('Step.predict4.Model.Beam.Enable     = T\n')
        parset.write('Step.predict4.Model.Beam.UseChannelFreq = T\n')
        parset.close()
        if not os.path.exists('Ateam_LBA_CC.skymodel'):
            os.system('cp %s/models/Ateam_LBA_CC.skymodel .'%scriptdir)
        os.system('calibrate-stand-alone -f %s %s Ateam_LBA_CC.skymodel'%(msfile,parsetname))
        os.system('python %s/aux-scripts/Ateamclipper.py %s'%(scriptdir,msfile))

        return
                      



def bbs_correct(parsetname,msfile,parmdbfile):
        parset = open(parsetname,'w')

        parset.write('Strategy.InputColumn = DATA\n')
        parset.write('Strategy.TimeRange = []\n')
        parset.write('Strategy.Baselines = *&\n')
        parset.write('Strategy.ChunkSize = 50\n')
        parset.write('Strategy.UseSolver = F\n')
        parset.write('Strategy.Steps = [correct]\n')

        parset.write('Step.correct.Operation = CORRECT\n')
        parset.write('Step.correct.Model.Sources = []\n')
        parset.write('Step.correct.Model.Gain.Enable = T\n')
        parset.write('Step.correct.Model.Beam.Enable = F          # only apply the solutions\n')
        parset.write('Step.correct.Model.CommonRotationAngle.Enable = T\n')
        parset.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
        parset.write('Step.correct.Output.Column = CORRECTED_DATA\n')

        parset.close()
        os.system('touch empty.model')
        os.system('calibrate-stand-alone -f --parmdb %s %s %s %s' %(parmdbfile,msfile,parsetname,'empty.model'))
        return
           

def bbs_correct_phasors(parsetname,msfile,parmdbfile):

        parset = open(parsetname,'w')

        parset.write('Strategy.InputColumn = DATA\n')
        parset.write('Strategy.TimeRange = []\n')
        parset.write('Strategy.Baselines = *&\n')
        parset.write('Strategy.ChunkSize = 50 \n')
        parset.write('Strategy.UseSolver = F\n')
        parset.write('Strategy.Steps = [correct]\n')

        parset.write('Step.correct.Operation = CORRECT\n')
        parset.write('Step.correct.Model.Sources = []\n')
        parset.write('Step.correct.Model.Phasors.Enable = T\n')
        parset.write('Step.correct.Model.Gain.Enable = T\n')
        parset.write('Step.correct.Model.Beam.Enable = T\n')
        parset.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
        parset.write('Step.correct.Output.Column = CORRECTED_DATA\n')

        parset.close()
        os.system('touch empty.model')
        os.system('calibrate-stand-alone -f --parmdb %s %s %s %s' %(parmdbfile,msfile,parsetname,'empty.model'))
        return

def bbs_clock_correct(parsetname,msfile,parmdbfile):
        parset = open(parsetname,'w')

        parset.write('Strategy.InputColumn = DATA\n')
        parset.write('Strategy.ChunkSize = 50 \n')
        parset.write('Strategy.UseSolver = F\n')
        parset.write('Strategy.Steps = [clockcorrect]\n')

        parset.write('Step.clockcorrect.Operation = CORRECT\n')
        parset.write('Step.clockcorrect.Model.Sources = []\n')
        parset.write('Step.clockcorrect.Model.Cache.Enable = T\n')
        parset.write('Step.clockcorrect.Model.Clock.Enable = T\n')
        parset.write('Step.clockcorrect.Model.Gain.Enable = T\n')
        parset.write('Step.clockcorrect.Model.Beam.Enable = F          # only apply the solutions\n')
        parset.write('Step.clockcorrect.Model.CommonRotation.Enable = F\n')
        parset.write('Step.clockcorrect.Output.Column = CORRECTED_DATA\n')

        parset.close()
        os.system('touch empty.model')
        os.system('calibrate-stand-alone -f --parmdb %s %s %s %s' %(parmdbfile,msfile,parsetname,'empty.model'))
        return

    
def bbs_removebeam(msfile,parsetfile):
    calfile = open('%s'%parsetfile,'w')

    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [correct]\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = F\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = \n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()
    os.system('calibrate-stand-alone --replace-parmdb %s %s'%(msfile,parsetfile))

    return


def downloaddata(downloadlist,downloadlogname,username,password):
        origfiles = glob.glob('./*.tar')
        downloadlistfile = open(downloadlist,'r')
        newdownloadlistfile = open('%s_edit'%downloadlist,'w')
        for downloadfile in downloadlistfile:
            truefilename = downloadfile.split('/')[-1][:-1]
            existingfiles = glob.glob('/net/para10/data1/shimwell/HETDEX/datastore/*%s'%truefilename)
            if len(existingfiles) == 1:
                print 'ALREADY EXISTS -- %s'%downloadfile
                os.system('mv %s .'%existingfiles[0])
            else:
                print 'DOES NOT EXIST -- downloading %s %s'%(downloadfile,len(existingfiles))
                newdownloadlistfile.write(downloadfile)
        newdownloadlistfile.close()    
        os.system("wget -i %s_edit --user=%s --password='%s'> %s 2>&1"%(downloadlist,username,password,downloadlogname))
	print "wget -i %s_edit --user=%s --password='%s'> %s 2>&1"%(downloadlist,username,password,downloadlogname)
        allfiles = glob.glob('./*.tar')
        newfiles = list(set(allfiles) - set(origfiles))
        # Rename the files
        for oldfname in newfiles:
                os.system('tar -xf %s'%oldfname)
        return


def ndppp_prepare(measurementset,msout,timeavg,freqavg,flagants,parsetfile,logfile):
    flagfile = open('%s'%parsetfile,'w')

    flagfile.write('msin =%s\n'%measurementset)
    flagfile.write('msout =%s \n'%msout)
    flagfile.write('msin.datacolumn = DATA \n')
    flagfile.write('steps = [flag,filter,avg,flagamp]\n')
    flagfile.write('filter.type = filter\n')
    flagfile.write('filter.baseline = [ [CS*] , [RS*] ]\n')
    flagfile.write('filter.remove = true\n')
    flagfile.write('avg.type = average\n')
    flagfile.write('avg.freqstep = %s\n'%freqavg)
    flagfile.write('avg.timestep = %s\n'%timeavg)
    flagfile.write('flag.type = preflagger\n')
    if flagants == '':
	flagfile.write('flag.baseline = [ DE* , FR* , SE* , UK* ]\n')
    else:
	flagfile.write('flag.baseline = [ DE* , FR* , SE* , UK*, %s ]\n'%flagants)
    flagfile.write('flagamp.type = preflagger\n')
    flagfile.write('flagamp.amplmin = 1e-30\n')

    flagfile.close()

    os.system('NDPPP %s > %s 2>&1'%(parsetfile,logfile))


def smooth_solutions(smoothtime,msfile,usebeam):

	losoto_smooth = open('losoto_smooth.parset','w')
	losoto_smooth.write('LoSoTo.Steps = [smooth]\n')
	losoto_smooth.write('LoSoTo.Solset = [sol000]\n')
	losoto_smooth.write('LoSoTo.Soltab = [sol000/amplitude000]\n')
	losoto_smooth.write('LoSoTo.SolType = [amplitude]\n')
	losoto_smooth.write('LoSoTo.ant = []\n')
	losoto_smooth.write('LoSoTo.pol = [XX,YY]\n')
	losoto_smooth.write('LoSoTo.dir = []\n')
	losoto_smooth.write('LoSoTo.Steps.smooth.Operation = SMOOTH\n')
	losoto_smooth.write('LoSoTo.Steps.smooth.Axes = [time]\n')
	losoto_smooth.write('LoSoTo.Steps.smooth.FWHM = [%s]\n'%smoothtime)
	losoto_smooth.close()
	
	os.system('H5parm_importer.py -v -i instrument %s_h5parm %s'%(msfile,msfile))
	os.system('losoto.py -v  %s_h5parm losoto_smooth.parset'%msfile)
	os.system('H5parm_exporter.py -i instrument -s sol000 --clobber -v %s_h5parm %s'%(msfile,msfile))
	os.system('mv %s/instrument %s/instrument_presmooth'%(msfile,msfile))
	os.system('mv %s/sol000_instrument %s/instrument'%(msfile,msfile))
	os.system('rm -rf %s_h5parm'%msfile)

	calfile = open('apply_smooth.bbs','w')

        calfile.write('Strategy.InputColumn = DATA\n')
        calfile.write('Strategy.ChunkSize = 50\n')
        calfile.write('Strategy.UseSolver = F\n')
        calfile.write('Strategy.Steps = [correct]\n')

        calfile.write('Step.correct.Operation = CORRECT\n')
        calfile.write('Step.correct.Model.Sources = []\n')
        calfile.write('Step.correct.Phasors.Enable = F\n')
        calfile.write('Step.correct.Model.Gain.Enable = T\n')
        calfile.write('Step.correct.Model.Beam.Enable = %s\n'%usebeam)
        calfile.write('Step.correct.Model.Beam.UseChannelFreq = %s\n'%usebeam)
        calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

        calfile.close()
        os.system('calibrate-stand-alone %s apply_smooth.bbs'%(msfile))

	return

def copy_colums(msfilename,msfileout,parsetname,incolumn,outcolumn):
    
    ndpppfile = open('%s'%parsetname,'w')
    ndpppfile.write('msin= %s\n'%msfilename) 
    ndpppfile.write('msin.datacolumn= %s\n'%incolumn) 
    ndpppfile.write('msout= %s\n'%msfileout) 
    ndpppfile.write('msout.datacolumn= %s\n'%outcolumn) 
    ndpppfile.write('steps= []\n') 
    ndpppfile.close()
    
    os.system('NDPPP %s'%parsetname)

    return


def monitor_computer(outputfilename,freq,length):
    starttime = time.time()
    outputfile = open(outputfilename,'w')
    outputfile.close()
    while time.time()-starttime < length:
            outputfile = open(outputfilename,'a')
            numbercpus = psutil.NUM_CPUS

            cpuusage = psutil.cpu_percent(percpu=True)

            virtualmemtotal,virtualmemavailable,virtualmemusedpercentage,virtualmemused = psutil.virtual_memory()[0],psutil.virtual_memory()[1],psutil.virtual_memory()[2],psutil.virtual_memory()[4]

            swapmemtotal,swapmemavailable,swapmemusedpercentage,swapmemused = psutil.swap_memory()[0],psutil.swap_memory()[2],psutil.swap_memory()[3],psutil.swap_memory()[1]
            outputfile.write('%s %s %s %s \n'%(time.time()-starttime,cpuusage,swapmemusedpercentage,virtualmemusedpercentage))
            time.sleep(freq)
            outputfile.close()

    return cpuusage,swapmemusedpercentage,virtualmemusedpercentage


def combine_measurementsets(measurementlist,msout,logfile,timeavg,freqavg,incol):
    # Measurement list needs to be e.g. /disks/lofar/ELAIS/data/*
    combfile = open('ndppp_comb.parset','w')

    combfile.write('msin = ')
    combfile.write('%s\n'%measurementlist)
    combfile.write('msin.missingdata=true\n')
    combfile.write('msin.orderms=False\n')
    combfile.write('msin.autoweight=false\n')
    combfile.write('msin.datacolumn = %s\n'%incol)
    combfile.write('msout = %s\n'%msout)
    combfile.write('steps = [preflag,count,avg1]\n')
    combfile.write('avg1.type=squash\n')
    combfile.write('avg1.freqstep=%s\n'%freqavg)
    combfile.write('avg1.timestep=%s\n'%timeavg)
    combfile.write('preflag.type=preflagger\n')
    combfile.write('preflag.corrtype=auto\n')
    combfile.close()

    os.system('NDPPP ndppp_comb.parset > %s 2>&1'%logfile)

def flag_measurementset(measurementset,msout,column,logfile):
    flagfile = open('ndppp_flag.parset','w')

    flagfile.write('msin =%s\n'%measurementset)
    flagfile.write('msin.missingdata = true \n')
    flagfile.write('msin.orderms=False \n')
    flagfile.write('msin.autoweight = false \n')
    flagfile.write('msin.forceautoweight = false \n')
    flagfile.write('msin.datacolumn = %s \n'%column)
    flagfile.write('msout =%s \n'%msout)
    flagfile.write('steps=[preflag,count,avg1,flag1] \n')
    flagfile.write('avg1.type=squash \n')
    flagfile.write('avg1.freqstep = 1 \n')
    flagfile.write('avg1.timestep= 1 \n')
    flagfile.write('preflag.type=preflagger \n')
    flagfile.write('preflag.corrtype=auto \n')
    flagfile.write('flag1.type=aoflagger \n')
    flagfile.close()

    os.system('NDPPP ndppp_flag.parset > %s 2>&1'%logfile)
    return

def phaseshift(ndpppfile,measurementlist,phasecenter,outms,incol,outcol):

    phaseshiftfile = open('%s'%ndpppfile,'w')

    phaseshiftfile.write('msin = ')
    phaseshiftfile.write('%s\n'%measurementlist)
    phaseshiftfile.write('msin.datacolumn = %s\n'%incol)
    phaseshiftfile.write('msout = %s\n'%outms)
    phaseshiftfile.write('msout.datacolumn = %s\n'%outcol)
    phaseshiftfile.write('steps = [PhaseShift]\n')
    phaseshiftfile.write('PhaseShift.type=phaseshift \n')
    phaseshiftfile.write('PhaseShift.phasecenter=[%sdeg, %sdeg] \n'%(phasecenter[0],phasecenter[1]))
    phaseshiftfile.close()

    os.system('NDPPP %s'%ndpppfile)

    return



def aw_imagedata(msfile,awimagename,imoutname,iterations,threshold,cellsize,uvmin,uvmax,npix,operation,mask,robust):

    imfile = open('%s'%awimagename,'w')
    imfile.write('ms=%s\n'%msfile)
    imfile.write('mask=%s\n'%mask)
    imfile.write('image=%s\n'%imoutname)
    imfile.write('data=CORRECTED_DATA\n')
    imfile.write('weight=briggs\n')
    imfile.write('robust=%s\n'%robust)
    imfile.write('npix=%s\n'%npix)
    imfile.write('cellsize=%s\n'%cellsize)
    imfile.write('padding=1.18\n')
    imfile.write('gain=0.1\n')
    imfile.write('stokes=I\n')
    imfile.write('operation=%s\n'%operation)
    imfile.write('oversample=5\n')
    imfile.write('timewindow=300\n')
    imfile.write('ApplyElement=0\n')
    imfile.write('FindNWplanes=True\n')
    imfile.write('threshold=%s\n'%threshold)
    imfile.write('PBCut=1e-2\n')
    imfile.write('wmax=20000 \n')
    imfile.write('UVmin=%s\n'%uvmin)
    imfile.write('UVmax=%s\n'%uvmax)
    imfile.write('SpheSupport=15\n')
    imfile.write('niter=%s\n'%iterations)

    imfile.close()
    
    os.system('awimager %s'%awimagename)

    return

def distance_on_unit_sphere(lat1, long1, lat2, long2):

    # Convert latitude and longitude to 
    # spherical coordinates in radians.
    degrees_to_radians = np.pi/180.0
        
    # phi = 90 - latitude
    phi1 = (90.0 - lat1)*degrees_to_radians
    phi2 = (90.0 - lat2)*degrees_to_radians
        
    # theta = longitude
    theta1 = long1*degrees_to_radians
    theta2 = long2*degrees_to_radians
        
    # Compute spherical distance from spherical coordinates.
        
    # For two locations in spherical coordinates 
    # (1, theta, phi) and (1, theta, phi)
    # cosine( arc length ) = 
    #    sin phi sin phi' cos(theta-theta') + cos phi cos phi'
    # distance = rho * arc length
    
    cos = (np.sin(phi1)*np.sin(phi2)*np.cos(theta1 - theta2) + 
           np.cos(phi1)*np.cos(phi2))
    arc = np.arccos( cos )

    earth_radius = 6378.1E3
    distance = arc*earth_radius
    # Remember to multiply arc by the radius of the earth 
    # in your favorite set of units to get length.
    return distance

def date_to_julian(year,month,day,hour,minute,second):
    if type(month) is str:
        if 'jan' in month.lower():
            month = 1
    if type(month) is str:
        if 'feb' in month.lower():
            month = 2
    if type(month) is str:
        if 'mar' in month.lower():
            month = 3
    if type(month) is str:
        if 'apr' in month.lower():
            month = 4
    if type(month) is str:
        if 'may' in month.lower():
            month = 5
    if type(month) is str:
        if 'jun' in month.lower():
            month = 6
    if type(month) is str:
        if 'jul' in month.lower():
            month = 7
    if type(month) is str:
        if 'aug' in month.lower():
            month = 8
    if type(month) is str:
        if 'sep' in month.lower():
            month = 9
    if type(month) is str:
        if 'oct' in month.lower():
            month = 10
    if type(month) is str:
        if 'nov' in month.lower():
            month = 11
    if type(month) is str:
        if 'dec' in month.lower():
            month = 12
        
    year = int(year) + 4800 - (14.0-int(month))/12.0
    month = int(month) + (14.0-int(month)) - 3.0

    julian_day = int(float(day)) + int((((float(month)*153.0+2)+2)/5)) + int(float(year)*365.0) + int(float(year)/4.0) - int(float(year)/100.0) + int(float(year)/400.0) -32045
    julian_time = float(hour)/24.0 + float(minute)/(24.0*60.0) + float(second)/(24.0*60.0*60.0)

    julian = julian_day + julian_time

    return julian


def find_fileinfo(msfilename,outfilename):

    os.system('msoverview in=%s verbose=T > %s'%(msfilename,outfilename))

    infodict = {}
    infodict['#ERRORS#'] = []
    antennadict = {}
    tmpfile = open(outfilename,'r')
    for line in tmpfile:
        line = line[:-1]
        line = line.split(' ')
        while '' in line:
            line.remove('')
        print line
        if len(line) > 4:
            if 'J2000' in line[4]:
                rah,ram,ras = float(line[2].split(':')[0]),float(line[2].split(':')[1]),float(line[2].split(':')[2])
                decd,decm,decs = float(line[3].split('.')[0]),float(line[3].split('.')[1]),float(line[3].split('.')[2])
                rarad = RA_J2000_to_radians(rah,ram,ras)
                decrad = DEC_J2000_to_radians(decd,decm,decs)
                infodict['RA(rad)'] = rarad
                infodict['DEC(rad)'] = decrad
        if len(line) > 1:
            if 'Antennas:' in line[0]:
                infodict['Num ants'] = int(line[1].replace(':',''))
        if len(line) > 1:
            if 'XX' in line and 'YY' in line and 'TOPO' in line[3]:
                infodict['ChannelWidth'] = float(line[5])*1E3
                infodict['Ref Freq'] = float(line[4])*1E6
                infodict['Num Chans'] = float(line[2])
            if 'XX' in line and 'YY' in line and 'TOPO' in line[2]:
                infodict['ChannelWidth'] = float(line[5])*1E3
                infodict['Ref Freq'] = float(line[3])*1E6
                infodict['Num Chans'] = float(line[1])
        if len(line) > 3:
            if 'nbaselines=' in line[3]:
                infodict['Baselines'] = int(line[3].replace('nbaselines=',''))
        if len(line) > 7:
            if 'Data' in line[0] and 'records:' in line[1]:
                infodict['numvis'] = float(line[2])
                infodict['inttime'] = float(line[7])
        if len(line) > 5:
            if 'Observed' in str(line[0]) and 'from' in str(line[1]):
                day,month,year = line[2].split('/')[0].split('-')[0],line[2].split('/')[0].split('-')[1],line[2].split('/')[0].split('-')[2]
                hour,minute,second = line[2].split('/')[1].split(':')[0],line[2].split('/')[1].split(':')[1],line[2].split('/')[1].split(':')[2]
                infodict['julian_date'] = date_to_julian(year,month,day,hour,minute,second)
		infodict['Obsdate_start'] = line[2]
		infodict['Obsdate_end'] = line[4] 
        if len(line) > 5:
            if 'LOFAR' in line[1] and len(line) > 6:
                longit = abs(float(line[-8].split('.')[0])) + float(line[-8].split('.')[1])/60.0 +  float(line[-8].split('.')[2])/(60.0*60.0) +  float(line[-8].split('.')[3])/(60.0*60.0*10.0)
                latt =  abs(float(line[-7].split('.')[0])) + float(line[-7].split('.')[1])/60.0 +  float(line[-7].split('.')[2])/(60.0*60.0) +  float(line[-7].split('.')[3])/(60.0*60.0*10.0)
                antennadict['Ant%s'%(line[0])] = longit,latt
            if 'LOFAR' in line[1] and len(line) == 6:
                longit = abs(float(line[4].split('.')[0])) + float(line[4].split('.')[1])/60.0 +  float(line[4].split('.')[2])/(60.0*60.0) +  float(line[4].split('.')[3])/(60.0*60.0*10.0)
                latt =  abs(float(line[5].split('.')[0])) + float(line[5].split('.')[1])/60.0 +  float(line[5].split('.')[2])/(60.0*60.0) +  float(line[5].split('.')[3])/(60.0*60.0*10.0)
                antennadict['Ant%s'%(line[0])] = longit,latt

    infodict['Smoothing'] = (float(infodict['inttime']) * float(infodict['Baselines']))/float(infodict['numvis'])

    infodict['Est Noise'] = 0.31*((8.0*60.0*60.0/float(infodict['inttime']))**0.5)*((3.66E6/(float(infodict['Num Chans'])*float(infodict['ChannelWidth'])))**0.5) #Estimated lofar sensitivity at 150MHz for the core is 0.31mJy in 8hrs for 3.66MHz bandwidth subbands.

    maxbaseline = 0.0
    minbaseline = 999999.0
    baselinedistances = []
    donelist = []
    antenna_minbase_dict = {}

    for element1 in antennadict:
        try:
            antenna_minbase_dict[element1]
        except KeyError:
            antenna_minbase_dict[element1] = []
 
        for element2 in antennadict:
            if element1 == element2:
                continue
            baselinedistance = distance_on_unit_sphere(antennadict[element1][0],antennadict[element1][1],antennadict[element2][0],antennadict[element2][1])

            antenna_minbase_dict[element1].append(baselinedistance)

            if ('%s-%s'%(element1,element2)) in donelist or ('%s-%s'%(element2,element1)) in donelist:
                continue
            donelist.append('%s-%s'%(element1,element2))            
            if baselinedistance > maxbaseline:
                maxbaseline = baselinedistance
            if baselinedistance < minbaseline:
                minbaseline = baselinedistance
            baselinedistances.append(baselinedistance)

    infodict['Min ant baselines']= []
    for element1 in antenna_minbase_dict:
        infodict['%s minbase'%element1] = np.min(antenna_minbase_dict[element1])
        if np.min(antenna_minbase_dict[element1]) not in infodict['Min ant baselines']:
            infodict['Min ant baselines'].append(np.min(antenna_minbase_dict[element1]))

    infodict['Min ant baselines'].sort()
    infodict['Baseline distances'] = baselinedistances
    infodict['Baseline distances'].sort()
    infodict['Max baseline'] = maxbaseline
    infodict['Min baseline'] = minbaseline


    # From http://www.cv.nrao.edu/course/astr534/Interferometers1.html
    infodict['Resolution (deg)'] = (((3E8/infodict['Ref Freq'])/infodict['Max baseline'])*(180.0/np.pi))
    infodict['Resolution (arcsec)'] = (((3E8/infodict['Ref Freq'])/infodict['Max baseline'])*(180.0/np.pi))*60.0*60.0
    infodict['Time smearing limit (1deg)'] = 1.37E4*infodict['Resolution (deg)']/1.0
    infodict['Bandwidth smearing limit (1deg)'] = infodict['Ref Freq']*infodict['Resolution (deg)']/1.0

    timesmearingcheck = infodict['Smoothing']/infodict['Time smearing limit (1deg)']
    bandwidthsmearingcheck =  infodict['ChannelWidth']/infodict['Bandwidth smearing limit (1deg)']

    if timesmearingcheck  > 0.3:
        print 'Time smearing limit ', infodict['Time smearing limit (1deg)']
        print 'Time smoothing in dataset',infodict['Smoothing']
        infodict['#ERRORS#'].append('Too much time smearing (%s)'%(timesmearingcheck))
    if bandwidthsmearingcheck > 0.3:
        print 'Bandwidth smearing limit', infodict['Bandwidth smearing limit (1deg)']
        print 'Frequency averaging in data',infodict['ChannelWidth']

        infodict['#ERRORS#'].append('Too much bandwidth smearing (%s)'%(bandwidthsmearingcheck))

    tmpfile.close()
    
    tmpfile = open(outfilename,'a')
    for value in infodict:
        tmpfile.write(str(value) + '     ' + str(infodict[value]) +'\n')
    tmpfile.close()

    return infodict

def ndppp_ampphase_calibratedata(msfile,model,calfilename,uvmin,uvmax):
    
    os.system('makesourcedb in=%s out=sourcedb format="<%s"'%(model,model))
    calfile = open('%s'%calfilename,'w')
 
    calfile.write('msin=%s\n'%msfile)
    calfile.write('msin.datacolumn=DATA\n')
    calfile.write('msout=%s\n'%msfile)
    calfile.write('msout.datacolumn=CORRECTED_DATA\n')
    
    calfile.write('steps = [cal]\n')

    calfile.write('cal.type=calibrate\n')
    calfile.write('cal.caltype=fulljones\n')
    calfile.write('cal.parmdb=%s/instrument\n'%msfile)
    calfile.write('cal.solint=1\n')
    calfile.write('cal.usemodelcolumn=false\n')
    calfile.write('cal.sourcedb=sourcedb\n')
    calfile.write('cal.sources=[]\n')
    calfile.write('cal.usebeammodel=true\n')
    calfile.write('cal.onebeamperpatch=true\n')
    calfile.write('cal.usechannelfreq=true\n')
    calfile.write('cal.maxiter=500\n')
    calfile.write('cal.detectstalling=true\n')
    calfile.write('cal.tolerance=1.0e-4\n')
    calfile.write('cal.debuglevel=0\n')

    calfile.close()

    os.system('NDPPP %s'%calfilename)


    calfile = open('%s.bbs'%calfilename,'w')
   
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [correct]\n')
    
    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')
    
    calfile.close()
    os.system('calibrate-stand-alone -f %s %s.bbs'%(msfile,calfilename))
    
    return




def ndppp_phase_calibratedata(msfile,model,calfilename,uvmin,uvmax):
    
    os.system('makesourcedb in=%s out=sourcedb format="<%s"'%(model,model))

    calfile = open('%s'%calfilename,'w')
 
    calfile.write('msin=%s\n'%msfile)
    calfile.write('msin.datacolumn=DATA\n')
    calfile.write('msout=%s\n'%msfile)
    #calfile.write('msout.datacolumn=CORRECTED_DATA\n')
    
    calfile.write('steps = [filter,cal]\n')

    calfile.write('filter.type=filter\n')
    calfile.write('filter.blrange=[%s,%s]\n'%(uvmin,uvmax))

    calfile.write('cal.type=calibrate\n')
    calfile.write('cal.caltype=phaseonly\n')
    calfile.write('cal.parmdb=ndppp_instrument\n')
    calfile.write('cal.solint=1\n')
    calfile.write('cal.usemodelcolumn=false\n')
    calfile.write('cal.sourcedb=sourcedb\n')
    calfile.write('cal.sources=[]\n')
    calfile.write('cal.usebeammodel=true\n')
    calfile.write('cal.onebeamperpatch=true\n')
    calfile.write('cal.usechannelfreq=true\n')
    calfile.write('cal.maxiter=500\n')
    calfile.write('cal.detectstalling=true\n')
    calfile.write('cal.tolerance=1.0e-5\n')
    calfile.write('cal.debuglevel=1\n')

    calfile.close()

    os.system('NDPPP %s'%calfilename)


    calfile = open('%s.bbs'%calfilename,'w')
   
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [correct]\n')
    
    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = T\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')
    
    calfile.close()
    #os.system('calibrate-stand-alone -f %s %s.bbs'%(msfile,calfilename))
    
    return

def phase_calibratedata_ddc(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus,usebeam):

    calfile = open('%s'%calfilename,'w')

    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    
    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = %s\n'%usebeam)
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = %s\n'%usebeam)
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Phasors.Enable = T\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Mode = COMPLEX\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:Phase:*","Gain:1:1:Phase:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) #was 4# Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = F\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = T\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = %s\n'%usebeam)
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = %s\n'%usebeam)
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f %s %s %s'%(ncpus,msfile,calfilename,model))

    return




def phase_calibratedata(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus):

    calfile = open('%s'%calfilename,'w')

    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    
    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Phasors.Enable = T\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Mode = COMPLEX\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:Phase:*","Gain:1:1:Phase:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) #was 4# Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = F\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = T\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f %s %s %s'%(ncpus,msfile,calfilename,model))

    return

def phase_calibratedata_arrayfactor(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus):

    calfile = open('%s'%calfilename,'w')

    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    
    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Beam.Mode = ARRAY_FACTOR\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Phasors.Enable = T\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Mode = COMPLEX\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:Phase:*","Gain:1:1:Phase:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) #was 4# Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = F\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = T\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = F\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = F\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f %s %s %s'%(ncpus,msfile,calfilename,model))

    return



def phase_calibratedata_nomodel(msfile,uvmodel,calfilename,uvmin,uvmax,timescale,ncpus):

    os.system('touch empty_model.bbs')

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    
    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Phasors.Enable = T\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Mode = COMPLEX\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:Phase:*","Gain:1:1:Phase:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) #was 4# Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = F\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.correct.Model.Phasors.Enable = T\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f %s %s %s'%(ncpus,msfile,calfilename,'empty_model.bbs'))

    return


def ampphase_calibratedata(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus):

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    calfile.write('Strategy.InputColumn = DATA\n')

    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:*","Gain:1:1:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) # Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = T\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone -f --numthreads %s %s %s %s'%(ncpus,msfile,calfilename,model))

    return

def ampphase_calibratedata_arrayfactor(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus):

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    calfile.write('Strategy.InputColumn = DATA\n')

    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Beam.Mode = ARRAY_FACTOR\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:*","Gain:1:1:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) # Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = T\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = F\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = F\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone -f --numthreads %s %s %s %s'%(ncpus,msfile,calfilename,model))

    return


def ampphase_calibratedata_ddc(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus,usebeam):

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    calfile.write('Strategy.InputColumn = DATA\n')

    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = %s\n'%usebeam)
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = %s\n'%usebeam)
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Phasors.Enable = F\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Mode = COMPLEX \n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:*","Gain:1:1:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) # Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = F\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 1000\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Phasors.Enable = F\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = %s\n'%usebeam)
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = %s\n'%usebeam)
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone -f --numthreads %s %s %s %s'%(ncpus,msfile,calfilename,model))

    return

def ampphase_calibratedata_rotationangle(msfile,model,calfilename,uvmin,uvmax,timescale,ncpus):

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.TimeRange = []\n')
    calfile.write('Strategy.Baselines = *&\n')

    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = []\n')
    calfile.write('Step.solve.Model.Beam.Enable = True\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Phasors.Enable = F\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Model.CommonRotation.Enable= T\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:*","Gain:1:1:*","CommonRotationAngle:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 1\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) # Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = T\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 100\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = []\n')
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.CommonRotation.Enable = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone -f -v %s %s %s'%(msfile,calfilename,model))

    return



def ampphase_calibratedata_nomodel(msfile,uvmodel,calfilename,uvmin,uvmax,timescale,ncpus):

    os.system('touch empty_model.bbs')

    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [solve, correct]\n')
    calfile.write('Strategy.InputColumn = DATA\n')

    calfile.write('Step.solve.Operation = SOLVE\n')
    calfile.write('Step.solve.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.solve.Model.Beam.Enable = T\n')
    calfile.write('Step.solve.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.solve.Model.Cache.Enable = T\n')
    calfile.write('Step.solve.Model.Bandpass.Enable = F\n')
    calfile.write('Step.solve.Model.Gain.Enable = T\n')
    calfile.write('Step.solve.Model.DirectionalGain.Enable = F\n')
    calfile.write('Step.solve.Solve.Parms = ["Gain:0:0:*","Gain:1:1:*"]\n')
    calfile.write('Step.solve.Solve.UVRange = [%s, %s]\n'%(uvmin,uvmax))
    calfile.write('Step.solve.Solve.ExclParms = []\n')
    calfile.write('Step.solve.Solve.CalibrationGroups = []\n')
    calfile.write('Step.solve.Solve.CellSize.Freq = 0\n')
    calfile.write('Step.solve.Solve.CellSize.Time = %s\n'%timescale) # Less than about 30seconds (remember previous time average).
    calfile.write('Step.solve.Solve.CellChunkSize = 25\n')
    calfile.write('Step.solve.Solve.PropagateSolutions = T\n')
    calfile.write('Step.solve.Solve.Options.MaxIter = 500\n')
    calfile.write('Step.solve.Solve.Options.EpsValue = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.EpsDerivative = 1e-8\n')
    calfile.write('Step.solve.Solve.Options.ColFactor = 1e-9\n')
    calfile.write('Step.solve.Solve.Options.LMFactor = 1.0\n')
    calfile.write('Step.solve.Solve.Options.BalancedEqs = F\n')
    calfile.write('Step.solve.Solve.Options.UseSVD = T\n')

    calfile.write('Step.correct.Operation = CORRECT\n')
    calfile.write('Step.correct.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.correct.Model.Gain.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.Enable = T\n')
    calfile.write('Step.correct.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.correct.Output.Column = CORRECTED_DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f %s %s %s'%(ncpus,msfile,calfilename,'empty_model.bbs'))


    return

def subtract_cleancomponents_data(msfile,uvmodel,parmdb,calfilename,ncpus):

    os.system('touch empty_model.bbs')
    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [subtract]\n')

    calfile.write('Step.subtract.Operation = SUBTRACT\n')
    calfile.write('Step.subtract.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.subtract.Model.Gain.Enable = T\n')
    calfile.write('Step.subtract.Model.Phasors.Enable = T\n')
    calfile.write('Step.subtract.Model.Beam.Enable = T \n')   
    calfile.write('Step.subtract.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.subtract.Output.Column = DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f --parmdb %s %s %s %s'%(ncpus,parmdb,msfile,calfilename,'empty_model.bbs'))

def subtract_cleancomponents_data_bbs(msfile,parmdb,calfilename,bbsfile,ncpus):


    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [subtract]\n')

    calfile.write('Step.subtract.Operation = SUBTRACT\n')
    calfile.write('Step.subtract.Model.Sources = []\n')
    calfile.write('Step.subtract.Model.Gain.Enable = T\n')
    calfile.write('Step.subtract.Model.Phasors.Enable = T\n')
    calfile.write('Step.subtract.Model.Beam.Enable = T \n')   
    calfile.write('Step.subtract.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.subtract.Output.Column = DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f --parmdb %s %s %s %s'%(ncpus,parmdb,msfile,calfilename,'%s'%bbsfile))


def subtract_cleancomponents_data_bbs_nophasors(msfile,parmdb,calfilename,bbsfile,ncpus):


    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [subtract]\n')

    calfile.write('Step.subtract.Operation = SUBTRACT\n')
    calfile.write('Step.subtract.Model.Sources = []\n')
    calfile.write('Step.subtract.Model.Gain.Enable = T\n')
    calfile.write('Step.subtract.Model.Phasors.Enable = F\n')
    calfile.write('Step.subtract.Model.Beam.Enable = T \n')   
    calfile.write('Step.subtract.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.subtract.Output.Column = DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f --parmdb %s %s %s %s'%(ncpus,parmdb,msfile,calfilename,'%s'%bbsfile))





def add_cleancomponents_data(msfile,uvmodel,parmdb,calfilename,ncpus):

    os.system('touch empty_model.bbs')
    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [add]\n')

    calfile.write('Step.add.Operation = ADD\n')
    calfile.write('Step.add.Model.Sources = [@%s]\n'%uvmodel)
    calfile.write('Step.add.Model.Gain.Enable = T\n')
    calfile.write('Step.add.Model.Phasors.Enable = T\n')
    calfile.write('Step.add.Model.Beam.Enable = T \n')   
    calfile.write('Step.add.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.add.Output.Column = DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f --parmdb %s %s %s %s'%(ncpus,parmdb,msfile,calfilename,'empty_model.bbs'))

def add_cleancomponents_data_bbs(msfile,parmdb,calfilename,bbsfile,ncpus):


    calfile = open('%s'%calfilename,'w')
    calfile.write('Strategy.InputColumn = DATA\n')
    calfile.write('Strategy.ChunkSize = 50\n')
    calfile.write('Strategy.UseSolver = F\n')
    calfile.write('Strategy.Steps = [add]\n')

    calfile.write('Step.add.Operation = ADD\n')
    calfile.write('Step.add.Model.Sources = []\n')
    calfile.write('Step.add.Model.Gain.Enable = T\n')
    calfile.write('Step.add.Model.Phasors.Enable = T\n')
    calfile.write('Step.add.Model.Beam.Enable = T \n')   
    calfile.write('Step.add.Model.Beam.UseChannelFreq = T\n')
    calfile.write('Step.add.Output.Column = DATA\n')

    calfile.close()

    os.system('calibrate-stand-alone --numthreads %s -f --parmdb %s %s %s %s'%(ncpus,parmdb,msfile,calfilename,bbsfile))



def casa_imagedata(msfile,imoutname,iterations,threshold,cellsize,imsize,uvmin,uvmax):
    imfile = open('cleaning-casa.sh','w')
    imfile.write('casapy <<EOF\n')
    imfile.write("clean(vis='%s',imagename='%s',gridmode='widefield',wprojplanes=256,selectdata=True,mode='mfs',nterms=2,niter=%s,gain=0.01,threshold='%s',psfmode='clark',interactive=False,imsize=[%s,%s],cell=['%s','%s'],weighting='briggs',robust=0,uvtaper=False,pbcor=False,minpb=0.2,multiscale=[0,3,9],uvrange=['%s~%sklambda'])\n"%(msfile,imoutname,iterations,threshold,imsize,imsize,cellsize,cellsize,uvmin,uvmax))
    imfile.write('exit\n')
    imfile.write('<<EOF\n')
    imfile.close()
    os.system('chmod +x cleaning-casa.sh')
    os.system('./cleaning-casa.sh')
    return


def casa_imagedata_simple(msfile,imoutname,iterations,threshold,cellsize,imsize,uvmin,uvmax):
    imfile = open('cleaning-casa.sh','w')
    imfile.write('casapy <<EOF\n')
    imfile.write("clean(vis='%s',imagename='%s',gridmode='widefield',wprojplanes=256,selectdata=True,mode='mfs',nterms=1,niter=%s,gain=0.01,threshold='%s',psfmode='clark',interactive=False,imsize=[%s,%s],cell=['%s','%s'],weighting='briggs',robust=-0.5,uvtaper=False,pbcor=False,minpb=0.2,uvrange=['%s~%sklambda'])\n"%(msfile,imoutname,iterations,threshold,imsize,imsize,cellsize,cellsize,uvmin,uvmax))
    imfile.write('exit\n')
    imfile.write('<<EOF\n')
    imfile.close()
    os.system('chmod +x cleaning-casa.sh')
    os.system('./cleaning-casa.sh')
    return
