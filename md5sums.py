import os
import hashlib
from operator import itemgetter


class Md5sums(object):
    def __init__(self):
        self.md5sum_set = set()

    def check_md5sums(self, foldername, skip_folders):
        for root, dirs, files in os.walk(foldername, topdown=False):
            for name in files:
                filename = os.path.join(root, name)
                # Continue if file is in unnecessary folder
                folderbrake = False
                for skip_folder in skip_folders:
                    if skip_folder in filename:
                        folderbrake = True
                        continue
                if folderbrake:
                    continue

                filemd5sum = md5sum(filename)
                if filemd5sum in self.md5sum_set:
                    print('Duplicate file found, skipping it: ' + filename)
                    continue
                else:
                    self.md5sum_set.add((filemd5sum, filename))

def md5sum(filename):
    """
    http://pythoncentral.io/hashing-files-with-python/

    :param filename:
    :return: the md5sum
    """
    BLOCKSIZE = 65536
    hasher = hashlib.md5()
    with open(filename, 'rb') as afile:
        buf = afile.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(BLOCKSIZE)
    return hasher.hexdigest()

if __name__ == '__main__':
    md5sums = Md5sums()
    md5sums.check_md5sums('a_folder', [])

    with open('E:\\dev\\result_file.txt', 'w') as f:
        f.write('\n'.join([' '.join(x) for x in (sorted(md5sums.md5sum_set, key=itemgetter(1)))]))