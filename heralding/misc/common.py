import logging
import time
import os

from sendfile import sendfile

logger = logging.getLogger(__name__)


def list2dict(list_of_options):
    """Transforms a list of 2 element tuples to a dictionary"""
    d = {}
    for key, value in list_of_options:
        d[key] = value
    return d


def send_whole_file(sock_fd, file_fd):
    offset = 0
    while True:
        sent = sendfile(sock_fd, file_fd, offset, 65536)
        if sent == 0:
            break
        offset += sent


def path_to_ls(fn):
    """ Converts an absolute path to an entry resembling the output of
        the ls command on most UNIX systems."""
    st = os.stat(fn)
    full_mode = 'rwxrwxrwx'
    mode = ''
    file_time = ''
    d = ''
    for i in range(9):
        # Incrementally builds up the 9 character string, using characters from the
        # fullmode (defined above) and mode bits from the stat() system call.
        mode += ((st.st_mode >> (8 - i)) & 1) and full_mode[i] or '-'
        d = (os.path.isdir(fn)) and 'd' or '-'
        file_time = time.strftime(' %b %d %H:%M ', time.gmtime(st.st_mtime))
    list_format = '{0}{1} 1 ftp ftp {2}\t{3}{4}'.format(d, mode, str(st.st_size), file_time, os.path.basename(fn))
    return list_format
