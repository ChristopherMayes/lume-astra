from .tools import make_executable

import os, sys, platform
import urllib.request




ASTRA_URL = {
    'Linux': 'http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/Astra',
    'Darwin_x86_64': 'http://www.desy.de/~mpyflo/Astra_for_Mac_OSX/Astra',
    'Darwin_arm': 'http://www.desy.de/~mpyflo/Astra_for_Mac_M1/Astra',
    'Windows': 'http://www.desy.de/~mpyflo/Astra_for_WindowsPC/Astra.exe'
}
GENERATOR_URL = {
    'Linux':   'http://www.desy.de/~mpyflo/Astra_for_64_Bit_Linux/generator',
    'Darwin_x86_64':  'http://www.desy.de/~mpyflo/Astra_for_Mac_OSX/generator',
    'Darwin_arm': 'http://www.desy.de/~mpyflo/Astra_for_Mac_M1/generator',
    'Windows': 'http://www.desy.de/~mpyflo/Astra_for_WindowsPC/generator.exe'
}



def url_key():
    system = platform.system()
    processor= platform.processor()
    if system == 'Darwin':
        key = f'{system}_{processor}'
    else:
        key = system
    return key
    
    

EXAMPLES_URL = "https://ChristopherMayes.github.io/lume-astra/assets/lume-astra-examples.zip"



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
    key=url_key()
    url=ASTRA_URL[key]
    dest = os.path.abspath(os.path.join(dest_dir, name))

    install_executable(url,  dest, verbose=verbose)
    
    os.environ['ASTRA_BIN'] = dest
    
    if verbose:
        print(f'Installed Astra in for {key} in {dest}, and set $ASTRA_BIN equal to this.')
    
    return dest

def install_generator(dest_dir=None, name='generator', verbose=False):
    """
    Installs Astra's generator from Klaus Floettmann's DESY website for the detected platform.
    
    Sets environmental variable GENERATOR_BIN
    """
    key = url_key()
    url=GENERATOR_URL[key]
    dest = os.path.abspath(os.path.join(dest_dir, name))
    install_executable(url,  dest, verbose=verbose)
    
    os.environ['GENERATOR_BIN'] = dest
    
    if verbose:
        print(f'Installed Astra\'s generator for {key} in {dest}, and set $GENERATOR_BIN equal to this.')    
    
    return dest


def install_examples(location):
    """
    Install lume-astra examples on the informed location.

    Parameters
    ----------
    location : str
        The folder in which to install the examples
    """
    import requests
    import zipfile
    import io
    import os

    loc = os.path.expanduser(os.path.expandvars(location))
    os.makedirs(loc, exist_ok=True)

    response = requests.get(EXAMPLES_URL, stream=True)
    if response.status_code == 200:
        zip_file = zipfile.ZipFile(io.BytesIO(response.content))
        zip_file.extractall(loc)
    else:
        raise RuntimeError(f"Could not download examples archive. Status code was: {response.status_code}")
