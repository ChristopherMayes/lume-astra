from .astra import run_astra, run_astra_with_generator, run_astra_with_generator
from .astra_calc import calc_ho_energy_spread
from .tools import full_path
import numpy as np
import json
import os



def end_output_data(output):
    """
    Some outputs are lists. Get the last item. 
    """
    o = {}
    for k in output:
        val = output[k]
        if isinstance(val, str): # Encode strings
            o[k] = val.encode()
        elif np.isscalar(val):
            o[k]=val
        else:
            o['end_'+k]=val[-1]
           
    return o



def default_astra_merit(A):
    """
    merit function to operate on an evaluated LUME-Astra object A. 
    
    Returns dict of scalar values
    """
    # Check for error
    if A.error:
        return {'error':True}
    else:
        m= {'error':False}
    
    # Gather output
    m.update(end_output_data(A.output))
    
    # Load final screen for calc
    A.load_screens(end_only=True)
    screen = A.screen[-1]        
    # TODO: time in screen isn't correct??? 
    m['end_higher_order_energy_spread'] = calc_ho_energy_spread( {'t':screen['z_rel'], 'Energy':(screen['pz_rel'])*1e-3},verbose=False) # eV
    
    # Lost particles have status < -6
    nlost = len(np.where(screen['status'] < -6)[0])    
    m['end_n_particle_loss'] = nlost
    
    # Remove annoying strings
    if 'why_error' in m:
        m.pop('why_error')
    
    
    return m


def evaluate_astra_with_generator(settings, archive_path=None, **run_astra_with_generator_params):
    """
    Simple evaluate astra.
    
    Similar to run_astra_with generator, but returns a flat dict of outputs. 
    
    Will raise an exception if there is an error. 
    
    """
    A = run_astra_with_generator(settings, **run_astra_with_generator_params)
        
    output = default_astra_merit(A)
    
    if output['error']:
        raise
    
    fingerprint = A.fingerprint()
    
    output['fingerprint'] = fingerprint
    
    if archive_path:
        assert os.path.exists(archive_path), f'archive path does not exist: {archive_path}'
        archive_file = full_path(os.path.join(archive_path, fingerprint+'.h5'))
        A.archive(archive_file)
        output['archive'] = archive_file
        
    return output