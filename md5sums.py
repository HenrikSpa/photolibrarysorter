import os
import hashlib


class Md5sums(object):
    def __init__(self):
        self.md5sum_set = set()

    def check_md5sums(self, foldername):

        skipfolders = ['AVF_INFO', 'Bilder_från_MaPa']

        for root, dirs, files in os.walk(foldername, topdown=False):
            for name in files:
                filename = os.path.join(root, name)

                # Continue if file is in unnecessary folder
                folderbrake = False
                for skipfolder in skipfolders:
                    if skipfolder in filename:
                        folderbrake = True
                        continue
                if folderbrake:
                    continue

                filemd5sum = hashlib.md5(filename.encode('utf-8')).hexdigest()
                if filemd5sum in self.md5sum_set:
                    print('Duplicate file found, skipping it: ' + filename)
                    continue
                else:
                    self.md5sum_set.add((filemd5sum, filename))


if __name__ == '__main__':
    md5sums = Md5sums()
    md5sums.check_md5sums("H:\Foton_reformatted")

    with open('H:\Foton_test\Foton_reformatted_md5sum.txt', 'w') as f:
        f.write('\n'.join(str(sorted(md5sums.md5sum_set))))