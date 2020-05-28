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
        try:
            fd = open(fpath, "w+")
        except OSError as e:
            print(f"File (%s) open failed with error: %s" % (fpath, os.strerror(e.errno)))
            sys.exit()

        return fd

    '''
    method: write file.
    purpose: write to the file using it's file descriptor.
    parameters: @file descriptor
                @buffer: Write this buffer data into file.
    '''
    def write_file(self, fd, buff):
        try:
            fd.write(buff)
        except OSError as e:
            print(f"File write failed with error: %s" % os.strerror(e.errno))
            sys.exit()

    '''
    method: create file.
    purpose: create the file and return file descriptor.
    parameters: @file descriptor.
    '''
    def close_file(self, fd):
        try:
            fd.close()
        except OSError as e:
            print(f"File close failed with error: %s" % os.strerror(e.errno))
            sys.exit()


