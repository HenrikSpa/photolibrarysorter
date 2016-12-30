# -*- coding: cp1252 -*-
'''
Copies files from original_folder to outfolder and structures and rename files.

The file date is read from exif or file modification time.
All files are structured under folders named
YEAR_nr_startmonth_endmonth_foton/videos/diverse[_suffix_from_keep_folder_names]

ex:
2005_3_jul-sep_diverse
2016_1_jan-mar_foton,
2016_1_jan-mar_videos,
2016_1_jan-mar_diverse,
2016_1_apr-jun_foton,
...

The monthly groups are 1_jan-mar, 2_apr-jun, 3_jul-sep and 4_okt-dec as specified in method create_folder

Created on 16 feb 2015
@author: HenrikSpa

Config file example:
[general]
original_folder  = E:\photos_before_sorting
outfolder = E:\reformatted_photos
keep_folder_names = Christmas_2014,Christmas_2015
skip_folders = AVF_INFO,some_other_folder
rename = red:reduced,Red:reduced
skip_folders_for_md5sums = AVF_INFO,some_other_folder

Notes:
    * Creating md5sums for the existing photo library takes a very long time currently.
'''
import os
import sys
import time
import datetime
import shutil
import logging
import configparser
from collections import OrderedDict
from md5sums import Md5sums, md5sum

try:
    import exifread
except:
    raise Exception("exifread package not installed")


class Photolibrarysorter(object):
    def __init__(self, original_folder=None, outfolder=None, skip_folders=None, keepname_list=None, rename_dict=None,
                 skip_extensions=None, videolist=None, imglist=None, skip_folders_for_md5sums=None):
        """

        :param original_folder:
        :param outfolder:
        :param skip_folders: List of folder names that should be excluded
        :param keepname_list: List of folder names that should be kept as separate folders
        :param rename_dict: a dict lice {'rename_string_in_foldername_from': 'rename_to', }
        :param skip_extensions: a list of files that should not be copied. ex ['.db', '.thm', '.ctg', '.inp']
        :param videolist: a list of files that should be treated as videos. ex ['.avi', '.mp4', '.3gp', '.mov']
        :param imglist: a list of files that should be treated as images. ex ['.png', '.jpg', '.gif', '.arw']
        :param skip_folders_for_md5sums:
        """

        self.foldername = original_folder
        self.outfolder = outfolder

        if skip_folders is None:
            self.skip_folders = []
        else:
            self.skip_folders = skip_folders

        if keepname_list is None:
            self.keepname_list = []
        else:
            self.keepname_list = keepname_list

        if rename_dict is None:
            self.rename_dict = {}
        else:
            self.rename_dict = rename_dict

        if skip_extensions is None:
            self.skip_extensions = ['.db', '.thm', '.ctg', '.inp']
        else:
            self.skip_extensions = skip_extensions

        if videolist is None:
            self.videolist = ['.avi', '.mp4', '.3gp', '.mov']
        else:
            self.videolist = videolist

        if imglist is None:
            self.imglist = ['.png', '.jpg', '.gif', '.arw']
        else:
            self.imglist = imglist

        if skip_folders_for_md5sums is None:
            self.skip_folders_for_md5sums = []
        else:
            self.skip_folders_for_md5sums = skip_folders_for_md5sums

        # divlist = ['.txt', '.rar', '.zip']

        logging.info('Using arguments:\n' + '\n'.join(
            [': '.join([k, v]) for k, v in [
                ('foldername', self.foldername),
                ('outfolder', self.outfolder),
                ('skip_folders', ', '.join(self.skip_folders)),
                ('keepname_list', ', '.join(self.keepname_list)),
                ('rename_dict', ', '.join([': '.join([_k, _v]) for _k, _v in self.rename_dict.items()])),
                ('skiplist', ', '.join(self.skip_extensions)),
                ('videolist', ', '.join(self.videolist)),
                ('imglist', ', '.join(self.imglist)),
                ('skip_folders_for_md5sums', ', '.join(self.skip_folders_for_md5sums))]]))

    def sort_library(self):
        md5sums = Md5sums()

        logging.info("Checking md5sums for all files in outfolder")
        md5sums.check_md5sums(self.outfolder, self.skip_folders_for_md5sums)
        logging.info("Checking md5sums for all files in outfolder done")

        self.md5sum_set = set([md5sum[0] for md5sum in md5sums.md5sum_set])

        copydict = self.build_copydict()
        copy_files(copydict)

    def build_copydict(self):
        """

        :return:
        """
        # Sets for tracking file extensions
        allexts = set()
        usedexts = set()
        
        copydict = {}

        for root, dirs, files in os.walk(self.foldername, topdown=False):
            for name in files:
                filename = os.path.join(root, name)
                ext = os.path.splitext(filename)[1].lower()
                allexts.add(ext)
                # Continue if file is in unnecessary folder
                folderbrake = False
                for skipfolder in self.skip_folders:
                    if skipfolder in filename:
                        folderbrake = True
                        break
                if folderbrake:
                    continue

                # Skip technical files
                if ext in self.skip_extensions:
                    continue

                # Skip the file if a duplicate has been handled
                filemd5sum = md5sum(filename)

                if filemd5sum in self.md5sum_set:
                    logging.WARNING('Duplicate file found, skipping it: ' + filename)
                    continue
                else:
                    self.md5sum_set.add(filemd5sum)

                # Create a date object from file modified time
                filemtime = get_mtime(filename)
                mtime_date_obj = datetime.datetime.strptime(filemtime, '%Y-%m-%d %H:%M:%S')

                # Additional suffix
                addsuffix = self.folder_suffix(root)

                if ext in self.videolist:
                    foldername = create_folder(self.outfolder, mtime_date_obj, '_videos' + addsuffix)
                    newfilename = date_filename(mtime_date_obj, ext)
                elif ext in self.imglist:
                    # If file is imagefile, then try to use exif data else modified time
                    openfile = open(filename, 'rb')
                    exif_dict = exifread.process_file(openfile)
                    openfile.close()

                    if exif_dict:
                        try:
                            exifdate = exif_dict['EXIF DateTimeOriginal']
                        except KeyError:
                            img_date_obj = mtime_date_obj
                        else:
                            img_date_obj = datetime.datetime.strptime(str(exifdate), '%Y:%m:%d %H:%M:%S')
                    else:
                        img_date_obj = mtime_date_obj

                    # Special date converter for a time when the camera clock was wrong
                    #TODO: This should be an option in some way.
                    #if '20100327' in root:
                    #    img_date_obj = corrdate(img_date_obj)

                    foldername = create_folder(self.outfolder, img_date_obj, '_foton' + addsuffix)
                    newfilename = date_filename(img_date_obj, ext)
                else:
                    foldername = create_folder(self.outfolder, mtime_date_obj, '_diverse' + addsuffix)
                    newfilename = name

                # Command that finally does the copying
                outfile = os.path.join(foldername, newfilename)
                outfile_orgname = outfile
                unhandled = True
                captured_close_in_time_nr = 0
                while unhandled:
                    if outfile in copydict:
                        captured_close_in_time_nr += 1
                        orgname, ext_temp = os.path.splitext(outfile_orgname)
                        outfile = orgname + "_" + str(captured_close_in_time_nr) + ext_temp
                    else:
                        print("outfile: " + outfile + " and infile " + filename)
                        copydict[outfile] = filename
                        usedexts.add(ext)
                        unhandled = False

                logging.info('Oldfile: ' + filename + ' Newfile: ' + outfile)

        logging.info('allexts: ' + '\n'.join(allexts) + '\n')
        logging.info('usedexts: ' + '\n'.join(usedexts) + '\n')
        logging.info('skipped exts: ' + '\n'.join(allexts.difference(usedexts)))

        return copydict

    def folder_suffix(self, root):
        found_folder_names = [self.rename_dict.get(x, x).replace(' ', '_') for x in self.keepname_list if x in root]
        if found_folder_names:
            # Remove duplicates
            found_folder_names = list(OrderedDict.fromkeys(found_folder_names))
            addsuffix = '_' + '_'.join(found_folder_names)
        else:
            addsuffix = ''
        return addsuffix


def copy_files(copydict):
    for copy_to, copy_from in sorted(copydict.items()):
        shutil.copy2(copy_from, copy_to)
        logging.info("File " + copy_from + " copied to " + copy_to)

def corrdate(adate):
    if adate.year == 2006:
        startdate = datetime.datetime(2006, 5, 18, 21, 18, 0)
        enddate = datetime.datetime(2010, 2, 6, 12, 15, 10)
        return adate + (enddate - startdate)
    else:
        return adate

def get_mtime(filename):
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(filename)))

def date_filename(date_obj, ext):
    datename = date_obj.strftime('%Y-%m-%d_%H%M%S')
    return datename + ext

def create_folder(root, date_obj, foldersuffix=''):
    folderyear = date_obj.year
    monthnum = date_obj.month
    if monthnum < 4:
        foldermonth = '1_jan-mar'
    elif monthnum < 7:
        foldermonth = '2_apr-jun'
    elif monthnum < 10:
        foldermonth = '3_jul-sep'
    elif monthnum < 13:
        foldermonth = '4_okt-dec'
    else:
        sys.exit('monthfoldername: The month was more than 12!')

    foldername = os.path.join(root, str(folderyear) + '_' + str(foldermonth) + foldersuffix)
    if not os.path.exists(foldername):
        os.makedirs(foldername)
    return foldername

if __name__ == '__main__':

    configfile = 'E:\\photolibrarysorter_config.txt'

    if os.path.isfile(configfile):
        config = configparser.ConfigParser()
        config.read(configfile)

        original_folder = config["general"]["original_folder"]
        outfolder = config["general"]["outfolder"]

        for dir in [original_folder, outfolder]:
            if not os.path.isdir(dir):
                raise Exception("Directory " + dir + " could not be read.")

        keepname_list = config["general"].get('keep_folder_names', '').split(',')
        skip_folders = config["general"].get('skip_folders', '').split(',')
        skip_folders_for_md5sums = config["general"].get('skip_folders_for_md5sums', '').split(',')
        _rename_dict = [x.split(':') for x in config["general"].get('rename', '').split(',')]
        if _rename_dict:
            rename_dict = dict(_rename_dict)
        else:
            rename_dict = {}

        if 'skip_extensions' not in config["general"]:
            skip_extensions = None
        else:
            skip_extensions = config["general"].get('skip_extensions', '').split(',')

        if 'videolist' not in config["general"]:
            videolist = None
        else:
            videolist = config["general"].get('videolist', '').split(',')

        if 'imglist' not in config["general"]:
            imglist = None
        else:
            imglist = config["general"].get('imglist', '').split(',')
    else:
        raise Exception("No configfile given")

    logdate = time.strftime('%Y-%m-%d_%H%M%S')
    logfilename = os.path.join(outfolder, 'Photolibrarysorter_log_' + logdate + '.txt')
    logging.basicConfig(filename=logfilename, level=logging.INFO)

    photolibrarysorter = Photolibrarysorter(original_folder=original_folder,
                                            outfolder=outfolder,
                                            skip_folders=skip_folders,
                                            keepname_list=keepname_list,
                                            rename_dict=rename_dict,
                                            skip_folders_for_md5sums=skip_folders_for_md5sums,
                                            imglist=imglist,
                                            videolist=videolist,
                                            skip_extensions=skip_extensions)
    photolibrarysorter.sort_library()
