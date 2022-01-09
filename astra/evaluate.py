from .astra import run_astra, run_astra_with_generator, run_astra_with_generator
from .astra_calc import calc_ho_energy_spread
from lume.tools import full_path
import numpy as np
import json
from inspect import getfullargspec
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
    m.update(end_output_data(A.output['stats']))
    
    P = A.particles[-1]  

    # Lost particles have status < -6
    nlost = len(np.where(P['status'] < -6)[0])    
    m['end_n_particle_loss'] = nlost 
    
    # Get live only for stat calcs
    P = P.where(P.status==1)
    
    # No live particles
    if len(P) == 0:
        return {'error':True}



    m['end_total_charge'] = P['charge']
    m['end_higher_order_energy_spread'] = P['higher_order_energy_spread']
    # Old method:
    #m['end_higher_order_energy_spread'] = calc_ho_energy_spread( {'t':P['z'], 'Energy':(P['pz'])*1e-3},verbose=False) # eV
    
    # Remove annoying strings
    if 'why_error' in m:
        m.pop('why_error')
    
    
    return m




# Get defaults for **params in evaluate for each type of simulation
def _get_defaults(run_f, extra=None):
    spec = getfullargspec(run_f)
    d = dict(zip(spec.args, spec.defaults))
    d.pop('settings')
    if extra:
        d.update(extra)
    return d





def evaluate(settings, simulation='astra', archive_path=None, merit_f=None, **params):
    """
    Evaluate astra using possible simulations:
        'astra'
        'astra_with_generator'
        'astra_with_distgen'
    
    Returns a flat dict of outputs. 
    
    If merit_f is provided, this function will be used to form the outputs. 
    Otherwise a default funciton will be applied.
    
    Will raise an exception if there is an error. 
    
    """
    
    # Pick simulation to run
    
    if simulation=='astra':
        A = run_astra(settings, **params)

    elif simulation=='astra_with_generator':
        A = run_astra_with_generator(settings, **params)
        
    elif simulation == 'astra_with_distgen':

        # Import here to limit dependency on distgen
        from .astra_distgen import run_astra_with_distgen
        A = run_astra_with_distgen(settings, **params)
        
    else:
        raise ValueError(f'simulation not recognized: {simulation}')
        
    if merit_f:
        output = merit_f(A)
    else:
        output = default_astra_merit(A)
    
    if output['error']:
        raise ValueError(f'Error returned from Astra evaluate')
    
    fingerprint = A.fingerprint()
    
    output['fingerprint'] = fingerprint
    
    if archive_path:
        path = full_path(archive_path)
        assert os.path.exists(path), f'archive path does not exist: {path}'
        archive_file = os.path.join(path, fingerprint+'.h5')
        A.archive(archive_file)
        output['archive'] = archive_file
        
    return output


# Convenience wrappers, and their full options

# Get all kwargs from run_astra routines. Save these as the complete set of options
EXTRA = {'archive_path':None, 'merit_f':None}
EXTRA2 = {'archive_path':None, 'merit_f':None, 'distgen_input_file':None}
DEFAULTS = {
    'evaluate_astra':                _get_defaults(run_astra, EXTRA ),
    'evaluate_astra_with_generator': _get_defaults(run_astra_with_generator, EXTRA) ,
    'evaluate_astra_with_distgen':   _get_defaults(run_astra, EXTRA2)
}


def evaluate_astra(settings, archive_path=None, merit_f=None, **params):
    """
    Convenience wrapper. See evaluate. 
    """
    return evaluate(settings, simulation='astra', 
                    archive_path=archive_path, merit_f=merit_f, **params)


def old_evaluate_astra_with_generator(settings, archive_path=None, merit_f=None, **params):
    """
    Convenience wrapper. See evaluate. 
    """
    return evaluate(settings, simulation='astra_with_generator', 
                    archive_path=archive_path, merit_f=merit_f, **params)


def evaluate_astra_with_generator(settings,
                                  astra_input_file=None,
                                  generator_input_file=None,
                                  workdir=None, 
                                  astra_bin='$ASTRA_BIN',
                                  generator_bin='$GENERATOR_BIN',
                                  timeout=2500,
                                  verbose=False,
                                  auto_set_spacecharge_mesh=True,
                                  archive_path=None,
                                  merit_f=None):
    """
    Similar to run_astra_with_generator, but returns a flat dict of outputs as processed by merit_f. 
    
    If no merit_f is given, a default one will be used. See:
        astra.evaluate.default_astra_merit
    
    Will raise an exception if there is an error. 
    """

    A = run_astra_with_generator(settings=settings,
                                    astra_input_file=astra_input_file,
                                    generator_input_file=generator_input_file,
                                    workdir=workdir, 
                                    command=astra_bin,
                                    command_generator=generator_bin,
                                    timeout=timeout,
                                    auto_set_spacecharge_mesh=auto_set_spacecharge_mesh,
                                    verbose=verbose)
        
    if merit_f:
        output = merit_f(A)
    else:
        output = default_astra_merit(A)
    
    if output['error']:
        raise ValueError(f'Error returned from Astra evaluate')
    
    fingerprint = A.fingerprint()
    
    output['fingerprint'] = fingerprint
    
    if archive_path:
        path = full_path(archive_path)
        assert os.path.exists(path), f'archive path does not exist: {path}'
        archive_file = os.path.join(path, fingerprint+'.h5')
        A.archive(archive_file)
        output['archive'] = archive_file
        
    return output



