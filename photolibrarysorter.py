# -*- coding: cp1252 -*-
'''
Created on 16 feb 2015

@author: HenrikSpa

Known bugs:
* The md5sum of the original and the name formatted file differs. No idea why.
'''
import hashlib
import os
import exifread
import sys
import time
import datetime
import shutil
import logging
import ConfigParser
from collections import OrderedDict
from md5sums import Md5sums



class Photolibrarysorter(object):
    def __init__(self, original_folder, outfolder, skip_folders=None, keepname_list=None, rename_dict=None,
                 skiplist=None, videolist=None, imglist=None):
        """

        :param original_folder:
        :param outfolder:
        :param skip_folders: List of folder names that should be excluded
        :param keepname_list: List of folder names that should be kept as separate folders
        :param rename_dict: a dict lice {'rename_string_in_foldername_from': 'rename_to', }
        :param skiplist: a list of files that should not be copied. ex ['.db', '.thm', '.ctg', '.inp']
        :param videolist: a list of files that should be treated as videos. ex ['.avi', '.mp4', '.3gp', '.mov']
        :param imglist: a list of files that should be treated as images. ex ['.png', '.jpg', '.gif', '.arw']
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

        if skiplist is None:
            self.skiplist = ['.db', '.thm', '.ctg', '.inp']
        else:
            self.skiplist = skiplist

        if videolist is None:
            self.videolist = ['.avi', '.mp4', '.3gp', '.mov']
        else:
            self.videolist = videolist

        if imglist is None:
            self.imglist = ['.png', '.jpg', '.gif', '.arw']
        else:
            self.imglist = imglist

        # divlist = ['.txt', '.rar', '.zip']

    def sort_library(self):
        logdate = time.strftime('%Y-%m-%d_%H%M%S')
        logfilename = os.path.join(self.outfolder, 'Photolibrarysorter_log_' + logdate + '.txt')
        logging.basicConfig(filename=logfilename, level=logging.INFO)

        md5sums = Md5sums()
        md5sums.check_md5sums(self.outfolder)

        self.md5sum_set = set([md5sum[0] for md5sum in md5sums.md5sum_set])

        # Sets for tracking file extensions
        self.allexts = set()
        self.usedexts = set()

        self.copydict = self.build_copydict()
        copy_files(self.copydict)

    def build_copydict(self):
        """

        :return:
        """
        copydict = dict()

        for root, dirs, files in os.walk(self.foldername, topdown=False):
            for name in files:
                filename = os.path.join(root, name)
                ext = os.path.splitext(filename)[1].lower()
                self.allexts.add(ext)
                # Continue if file is in unnecessary folder
                folderbrake = False
                for skipfolder in self.skip_folders:
                    if skipfolder in filename:
                        folderbrake = True
                        continue
                if folderbrake:
                    continue

                # Skip technical files
                if ext in self.skiplist:
                    continue

                # Skip the file if a duplicate has been handled
                filemd5sum = hashlib.md5(filename.encode('utf-8')).hexdigest()

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
                    if '20100327' in root:
                        img_date_obj = corrdate(img_date_obj)

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
                        self.usedexts.add(ext)
                        unhandled = False

                logging.info('Oldfile: ' + filename + ' Newfile: ' + outfile)

        logging.info('allexts: ' + '\n'.join(self.allexts) + '\n')
        logging.info('usedexts: ' + '\n'.join(self.usedexts) + '\n')
        logging.info('skipped exts: ' + '\n'.join(self.allexts.difference(self.usedexts)))

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
    for copy_to, copy_from in copydict.items():
        shutil.copy2(copy_from, copy_to)


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


def copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)


def read_config(filename):
    Config = ConfigParser.ConfigParser()
    Config.read(filename)


if __name__ == '__main__':
    configfile = 'G:\\photolibrarysorter_config.txt'

    if os.path.isfile(configfile):
        config = read_config(configfile)

        original_folder = config.getstring("default", "original_folder")
        outfolder = config.getstring("default", "outfolder")

        if config.items('keepname_list'):
            keepname_list = [k for k, v in config.items('keepname_list')]
        else:
            keepname_list = []
            
        if config.items('skip_folders'):
            skip_folders = [k for k, v in config.items('skip_folders')]
        else:
            skip_folders = []

        if config.items('skip_folders'):
            skip_folders = [k for k, v in config.items('skip_folders')]
        else:
            skip_folders = []

        if config.items('rename'):
            rename = {k: v for k, v in config.items('rename')}
        else:
            rename_dict = {}
    else:
        raise Exception("No configfile given")

    photolibrarysorter = Photolibrarysorter(original_folder,
                                            outfolder,
                                            skip_folders,
                                            keepname_list,
                                            rename_dict)
    photolibrarysorter.sort_library()
