import datetime
import errno
import os
import subprocess
import sys
import traceback

def execute(cmd, cwd=None):
    """
    
    Constantly print Subprocess output while process is running
    from: https://stackoverflow.com/questions/4417546/constantly-print-subprocess-output-while-process-is-running
    
    # Example usage:
        for path in execute(["locate", "a"]):
        print(path, end="")
        
    Useful in Jupyter notebook
    
    """
    popen = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True, cwd=cwd)
    if os.name == 'nt':
        # When running Astra with Windows it requires us to Press return at the end of execution
        popen.stdin.write("\n")
        popen.stdin.flush()
        popen.stdin.close()
    for stdout_line in iter(popen.stdout.readline, ""):
        yield stdout_line
    popen.stdin.close()
    popen.stdout.close()
    return_code = popen.wait()
    if return_code:
        raise subprocess.CalledProcessError(return_code, cmd)


# Alternative execute
def execute2(cmd, timeout=None, cwd=None):
    """
    Execute with time limit (timeout) in seconds, catching run errors. 
    """

    output = {'error': True, 'log': ''}
    try:
        p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                           timeout=timeout, cwd=cwd)
        output['log'] = p.stdout
        output['error'] = False
        output['why_error'] = ''
    except subprocess.TimeoutExpired as ex:
        output['log'] = ex.stdout + '\n' + str(ex)
        output['why_error'] = 'timeout'
    except:
        #exc_tuple = sys.exc_info()
        error_str = traceback.format_exc()         
        output['log'] = 'unknown run error'
        output['why_error'] = error_str
    return output


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


def make_executable(path):
    """
    https://stackoverflow.com/questions/12791997/how-do-you-do-a-simple-chmod-x-from-within-python
    """
    mode = os.stat(path).st_mode
    mode |= (mode & 0o444) >> 2  # copy R bits to X
    os.chmod(path, mode)


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

