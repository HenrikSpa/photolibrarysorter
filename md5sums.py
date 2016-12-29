import os
import hashlib


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

                filemd5sum = hashlib.md5(filename.encode('utf-8')).hexdigest()
                if filemd5sum in self.md5sum_set:
                    print('Duplicate file found, skipping it: ' + filename)
                    continue
                else:
                    self.md5sum_set.add((filemd5sum, filename))


if __name__ == '__main__':
    md5sums = Md5sums()
    md5sums.check_md5sums('a_path', ['', ''])

    with open('filename', 'w') as f:
        f.write('\n'.join(str(sorted(md5sums.md5sum_set))))