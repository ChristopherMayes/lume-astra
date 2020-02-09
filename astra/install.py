from .tools import make_executable

import os, sys, platform
import urllib.request


ASTRA_URL = {
    'Linux': 'http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/Astra',
    'Darwin': 'http://www.desy.de/~mpyflo/Astra_for_Mac_OSX/Astra',
    'Windows': 'http://www.desy.de/~mpyflo/Astra_for_WindowsPC/Astra.exe'
}
GENERATOR_URL = {
    'Linux':   'http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/generator',
    'Darwin':  'http://www.desy.de/~mpyflo/Astra_for_Mac_OSX/generator',
    'Windows': 'http://www.desy.de/~mpyflo/Astra_for_WindowsPC/generator.exe'
}




def install_executable(url, dest, verbose=False):
    """
    Downloads a url into a destination and makes it executable. Will not overwrite.
    """

    if os.path.exists(dest):
        print(os.path.abspath(dest), 'exists, will not overwrite')
    else:
        if verbose:
            print(f'Downloading {url} to {dest}')
        urllib.request.urlretrieve(url, dest)   
        make_executable(dest)
    
    return dest

def install_astra(dest_dir=None, name='Astra', verbose=False):
    """
    Installs Astra from Klaus Floettmann's DESY website for the detected platform.
    
    Sets environmental variable ASTRA_BIN
    """
    system = platform.system()
    url=ASTRA_URL[system]
    dest = os.path.abspath(os.path.join(dest_dir, name))

    install_executable(url,  dest, verbose=verbose)
    
    os.environ['ASTRA_BIN'] = dest
    
    if verbose:
        print(f'Installed Astra in {dest}, and set $ASTRA_BIN equal to this.')
    
    return dest

def install_generator(dest_dir=None, name='generator', verbose=False):
    """
    Installs Astra's generator from Klaus Floettmann's DESY website for the detected platform.
    
    Sets environmental variable GENERATOR_BIN
    """
    system = platform.system()
    url=GENERATOR_URL[system]
    dest = os.path.abspath(os.path.join(dest_dir, name))
    install_executable(url,  dest, verbose=verbose)
    
    os.environ['GENERATOR_BIN'] = dest
    
    if verbose:
        print(f'Installed Astra\'s generator in {dest}, and set $GENERATOR_BIN equal to this.')    
    
    return dest
    
    
