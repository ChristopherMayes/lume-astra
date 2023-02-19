import datetime
import errno
import os
import subprocess
from lume.tools import make_executable, execute, execute2



def runs_script(runscript=[], dir=None, log_file=None, verbose=True):
    """
    Basic driver for running a script in a directory. Will     
    """

    # Save init dir
    init_dir = os.getcwd()

    if dir:
        os.chdir(dir)

    log = []

    for path in execute(runscript):
        if verbose:
            print(path, end="")
        log.append(path)
    if log_file:
        with open(log_file, 'w') as f:
            for line in log:
                f.write(line)

                # Return to init dir
    os.chdir(init_dir)
    return log


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


def native_type(value):
    """
    Converts a numpy type to a native python type.
    See:
    https://stackoverflow.com/questions/9452775/converting-numpy-dtypes-to-native-python-types/11389998
    """
    return getattr(value, 'tolist', lambda: value)()


def isotime():
    """UTC to ISO 8601 with Local TimeZone information without microsecond"""
    return datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).astimezone().replace(
        microsecond=0).isoformat()

    



def make_symlink(src, path):
    """
    Makes a symlink from a source file `src` into a path.
    
    Will not overwrite real files.
    
    Parameters
    ----------
    src: source filename
    path: path to make symlink into
    
    Returns
    -------
    succeess: bool
    
    """
    
    _, file = os.path.split(src)
    
    dest = os.path.join(path, file)
    
    # Replace old symlinks. 
    if os.path.islink(dest):
        os.unlink(dest)
    elif os.path.exists(dest):
        return False
    
    os.symlink(src, dest)
    
    return True

