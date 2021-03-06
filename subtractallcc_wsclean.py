import os
import glob
import sys
import numpy
import pwd
from subprocess import Popen, PIPE
import time
import pyrap.images

username = pwd.getpwuid(os.getuid())[0]

if len(sys.argv)<2:
    raise Exception('Give the path to the setup code for the facet')

# setup code must set SCRIPTPATH, wsclean, mslist, casaregion, and may
# do anything else needed

print 'Using',sys.argv[1],'as the setup code'
execfile(sys.argv[1])
print 'script path is',SCRIPTPATH

print 'working on MS list',mslist

niterh = 40000
niterl = 20000
nterms = 1
imsizeh= 6144
imsizel= 4800
cellh  = '7.5arcsec'
celll  = '25arcsec'

threshisl = 2.5
threshpix = 5
atrous_do = "True"

def create_ndppp_parset(msin, msout):
    ndppp_parset = msin.split('.')[0] +'ndppp_lowresavg.parset'
    os.system('rm -f ' + ndppp_parset)

    f=open(ndppp_parset, 'w')
    f.write('msin ="%s"\n' % msin)
    f.write('msin.datacolumn = MODEL_DATA\n')
    f.write('msin.autoweight = false\n')
    f.write('msout ="%s"\n' % msout)
    f.write('msout.writefullresflag=False\n')
    f.write('steps = [avg1]\n')
    f.write('avg1.type = squash\n')
    f.write('avg1.freqstep = 5\n')
    f.write('avg1.timestep = 2\n')
    f.close()
    return ndppp_parset



for ms in mslist:

    imhigh = ms.split('.')[0] + 'highres'
    imlow  = ms.split('.')[0] + 'lowres'


    # ---------------------
    # image without mask
    cmd1 = wsclean + ' -reorder -name ' + imhigh + ' -size ' + str(imsizeh) + ' ' + str(imsizeh) + ' '
    cmd2 = '-scale ' + cellh + ' -weight briggs 0.0 -niter ' + str(niterh) + ' '
    cmd3 = '-maxuv-l 7e3 -mgain 0.65 -fitbeam -datacolumn CORRECTED_DATA -no-update-model-required ' + ms

    print cmd1+cmd2+cmd3


    ######### check that no wsclean is running
    warned=False
    cmd = "ps -f -u " + username + " | grep wsclean | grep -v _wsclean.py | grep -v wsclean.parset |grep -v grep |wc -l"
    output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    while output > 0 : # "grep -v grep" to prevent counting the grep command
        if not(warned):
            print 'A wsclean is already running, waiting for it to finish'
            warned=True
        time.sleep(2)
        output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    #########


    os.system(cmd1+cmd2+cmd3)


    # create the mask

    cmd='python '+SCRIPTPATH+'/makecleanmask_10sb_wsclean.py --threshpix '+str(threshpix)+\
                ' --threshisl '+str(threshisl) +' --atrous_do '+ str(atrous_do)+' '
    if casaregion!='':
        cmd+='--casaregion  '+ casaregion +' '
    cmd+=imhigh + '-image.fits'

    print cmd
    os.system(cmd)

    mask_name  = imhigh + '.fitsmask'
    casa_mask  = imhigh + '.casamask'

    maskim=pyrap.images.image(mask_name)
    maskim.saveas(casa_mask)

    # include region file
    if casaregion != '':
        os.system('casapy --nogui -c '+SCRIPTPATH+'/fitsandregion2image.py '\
                  + mask_name + ' ' + casa_mask + ' ' + casaregion)
    else:
        os.system('casapy --nogui -c '+SCRIPTPATH+'/fitsandregion2image.py '\
                  + mask_name + ' ' + casa_mask + ' ' + 'None')

    imhigh = imhigh + 'withmask'
    cmd1 = wsclean + ' -reorder -name ' + imhigh + ' -size ' + str(imsizeh) + ' ' + str(imsizeh) + ' '
    cmd2 = '-scale ' + cellh + ' -weight briggs 0.0 -niter ' + str(niterh) + ' '
    cmd3 = '-maxuv-l 7e3 -no-update-model-required -mgain 0.65 -fitbeam -datacolumn CORRECTED_DATA -casamask ' + casa_mask  + ' ' + ms

    print cmd1+cmd2+cmd3

    ######### check that no wsclean is running
    cmd = "ps -f -u " + username + " | grep wsclean | grep -v _wsclean.py | grep -v wsclean.parset |grep -v grep |wc -l"
    output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    while output > 0 : # "grep -v grep" to prevent counting the grep command
        time.sleep(2)
        output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    #########

    os.system(cmd1+cmd2+cmd3)

    fits_model = imhigh + '-model.fits'
    casa_model = imhigh + '.model'

    # convert model fits image to casa .model format
    print 'Converting model to casapy format', fits_model, ' ==> ', casa_model

    modelim=pyrap.images.image(fits_model)
    modelim.saveas(casa_model)

    #os.system('casapy --nogui -c '+SCRIPTPATH+'/fits2image.py '\
    #            + fits_model + ' ' + casa_model)

    # ---------------------
    # make the skymodel
    skymodel = imhigh  + '.skymodel'
    os.system('rm -f ' + '.skymodel')
    os.system(SCRIPTPATH+'/casapy2bbs_one_patch_per_cc.py '  + casa_model + ' ' +  skymodel)

    # ---------------------
    # subtract the cc
    parset = SCRIPTPATH+'/subtractall_highres_wsclean.parset'
    cmd = 'calibrate-stand-alone --replace-sourcedb --parmdb-name instrument_ap_smoothed '
    cmd = cmd + ms + ' ' + parset + ' ' + skymodel + ' >' + ms + '.highressubbbslog'
    print cmd

    os.system(cmd)

    # ---------------------
    # average down for lowres image



    msout = ms.split('.')[0] + '.lowres.ms'

    ndppp_parset = create_ndppp_parset(ms, msout)

    os.system('rm -rf ' + msout)
    os.system('NDPPP ' + ndppp_parset + '>tmp.txt')


    # make the lowres image (no mask)
    cmd1 = wsclean + ' -reorder -name ' + imlow + ' -size ' + str(imsizel) + ' ' + str(imsizel) + ' '
    cmd2 = '-scale ' + celll + ' -weight briggs 0.0 -niter ' + str(niterl) + ' '
    cmd3 = '-maxuv-l 2e3 -no-update-model-required -mgain 0.65 -fitbeam -datacolumn DATA ' + msout

    print cmd1+cmd2+cmd3

    ######### check that no wsclean is running
    cmd = "ps -f -u " + username + " | grep wsclean | grep -v _wsclean.py | grep -v wsclean.parset |grep -v grep |wc -l"
    output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    while output > 0 : # "grep -v grep" to prevent counting the grep command
        time.sleep(2)
        output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    #########
    os.system(cmd1+cmd2+cmd3)



    # ---------------------
    # create the lowres mask
    cmd='python '+SCRIPTPATH+'/makecleanmask_10sb_wsclean.py --threshpix '+str(5.0)+\
               ' --threshisl '+str(4.0) +' --atrous_do '+ str(atrous_do) + ' '
    if casaregion!='':
        cmd+='--casaregion  '+ casaregion +' '
    cmd+=imlow + '-image.fits'
    os.system(cmd)

    # convert to CASA format
    mask_name  = imlow + '.fitsmask'
    casa_mask  = imlow + '.casamask'

    maskim=pyrap.images.image(mask_name)
    maskim.saveas(casa_mask)

    # include region file
    if casaregion != '':
        os.system('casapy --nogui -c '+SCRIPTPATH+'/fitsandregion2image.py '\
                  + mask_name + ' ' + casa_mask + ' ' + casaregion)
    else:
        os.system('casapy --nogui -c '+SCRIPTPATH+'/fitsandregion2image.py '\
                  + mask_name + ' ' + casa_mask + ' ' + 'None')

    imlow = imlow + 'withmask'
    cmd1 = wsclean + ' -reorder -name ' + imlow + ' -size ' + str(imsizel) + ' ' + str(imsizel) + ' '
    cmd2 = '-scale ' + celll + ' -weight briggs 0.0 -niter ' + str(niterl) + ' '
    cmd3 = '-maxuv-l 2e3 -no-update-model-required -mgain 0.65 -fitbeam -datacolumn DATA -casamask ' + casa_mask  + ' ' + msout

    print cmd1+cmd2+cmd3

    ######### check that no wsclean is running
    cmd = "ps -f -u " + username + " | grep wsclean | grep -v _wsclean.py | grep -v wsclean.parset |grep -v grep |wc -l"
    output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    while output > 0 : # "grep -v grep" to prevent counting the grep command
        time.sleep(2)
        output=numpy.int(Popen(cmd, shell=True, stdout=PIPE).communicate()[0])
    #########
    os.system(cmd1+cmd2+cmd3)




    fits_model = imlow + '-model.fits'
    casa_model = imlow + '.model'

    # convert model fits image to casa .model format
    print 'Converting model to casapy format', fits_model, ' ==> ', casa_model

    modelim=pyrap.images.image(fits_model)
    modelim.saveas(casa_model)

    #os.system('casapy --nogui -c '+SCRIPTPATH+'/fits2image.py '\
    #            + fits_model + ' ' + casa_model)
    # ---------------------
    # create the low-res skymodel

    skymodel = imlow  + '.skymodel'
    os.system('rm -f ' + '.skymodel')
    os.system(SCRIPTPATH+'/casapy2bbs_one_patch_per_cc.py '  + casa_model  + ' ' +  skymodel)


    # ---------------------
    # subtract thelowres cc
    parset = SCRIPTPATH+'/subtractall_lowres_wsclean.parset'
    cmd = 'calibrate-stand-alone --replace-sourcedb --parmdb-name instrument_ap_smoothed '
    cmd = cmd + ms + ' ' + parset + ' ' + skymodel + ' >' + ms + '.lowressubbbslog'
    print cmd
    os.system(cmd)


    # ---------------------
    # merge the skymodels
    finalsky =  ms.split('.')[0] + '.skymodel'
    os.system('cp ' + imhigh+ '.skymodel ' + finalsky)
    os.system("grep -v '#' "+  imlow+ ".skymodel > tmp.sky")
    os.system("cat tmp.sky >>" + finalsky)

    cmd = "sed -i 's/, , , /, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.5e8, [0.0]/g'"
    os.system(cmd + ' ' + finalsky)

    cmd = 'sed -i \"s/# (Name, Type, Patch, Ra, Dec, I, Q, U, V) = format/format = Name, Type, Patch, Ra, Dec, I, Q, U, V, MajorAxis, MinorAxis, Orientation, ReferenceFrequency=\'1.5e+08\', SpectralIndex=\'[]\'/g\"  '
    os.system(cmd + ' ' + finalsky)
