import os, errno, sys

'''
This class will have methods for file IO operations.
'''
class BasicIO:

    '''
    method: open file.
    purpose: open the file and return file descriptor.
    parameters: @file path.
    '''
    def open_file(self, fpath):
        fd = None
        try:
            fd = open(fpath, "w+")
        except OSError as e:
            print("File (%s) open failed with error: %s" % (fpath, os.strerror(e.errno)))

        return fd

    '''
    method: write file.
    purpose: write to the file using it's file descriptor.
    parameters: @file descriptor
                @buffer: Write this buffer data into file.
    '''
    def write_file(self, fd, buff):
        nbytes = 1
        try:
            nbytes = fd.write(buff)
        except OSError as e:
            print("File write failed with error: %s" % os.strerror(e.errno))

        return nbytes

    '''
    method: create file.
    purpose: create the file and return file descriptor.
    parameters: @file descriptor.
    '''
    def close_file(self, fd):
        rc = -1
        try:
            rc = fd.close()
        except OSError as e:
            print("File close failed with error: %s" % os.strerror(e.errno))

        return rc
