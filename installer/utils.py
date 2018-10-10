from contextlib import contextmanager
import grp
import os
import pwd
import errno

def mkdir_p(path, mode=0777):
    ''' Creates the directory and any subdirectories listed in path '''
    try:
        os.makedirs(path, mode)
    except OSError as exc:
        if exc.errno != errno.EEXIST or not os.path.isdir(path):
            raise

def chown_R(fd, user=None, group=None):
    if user is not None:
        uid = pwd.getpwnam(user).pw_uid
    else:
        uid = -1
    if group is not None:
        gid = grp.getgrnam(group).gr_gid
    else:
        gid = -1
    if os.path.isfile(fd):
        os.chown(fd, uid, gid)
    elif os.path.isdir(fd):
        for root, dirs, files in os.walk(os.path.realpath(fd)):
            for directory in dirs:
                os.chown(os.path.join(root, directory), uid, gid)
            for name in files:
                file_path = os.path.join(root, name)
                os.chown(file_path, uid, gid)

@contextmanager
def pushd(new_dir):
    '''
        Mimic's Bash's pushd executable; Adds new_dir to the directory stack
        Usage:
        with pushd(some_dir):
            print os.getcwd() # "some_dir"
            some_actions
        print os.getcwd() # "starting_directory"
    '''
    previous_dir = os.getcwd()
    os.chdir(new_dir)
    yield
    os.chdir(previous_dir)
