import numpy as np

from pmd_beamphysics import ParticleGroup, pmd_init
from pmd_beamphysics.units import read_dataset_and_unit_h5, write_dataset_and_unit_h5

from .control import ControlGroup
from .parsers import OutputUnits
from .tools import isotime, native_type


def fstr(s):
    """
    Makes a fixed string for h5 files
    """
    return np.bytes_(s)




def astra_init(h5, version=None):
    """
    Set basic information to an open h5 handle
    
    """
    
    if not version:
        from astra import __version__ 
        version = __version__
        
    
    d = {
        'dataType':'lume-astra',
        'software':'lume-astra',
        'version':version,
        'date':isotime()     
    }
    for k,v in d.items():
        h5.attrs[k] = fstr(v)


def opmd_init(h5, basePath='/screen/%T/', particlesPath='./' ):
    """
    Root attribute initialization.
    
    h5 should be the root of the file.
    """
    d = {
        'basePath':basePath,
        'dataType':'openPMD',
        'openPMD':'2.0.0',
        'openPMDextension':'BeamPhysics;SpeciesType',
        'particlesPath':particlesPath    
    }
    for k,v in d.items():
        h5.attrs[k] = fstr(v)
        
        
        
#----------------------------        
# Searching archives

def is_astra_archive(h5, key='dataType', value=np.bytes_('lume-astra')):
    """
    Checks if an h5 handle is a lume-astra archive
    """
    return key in h5.attrs and h5.attrs[key]==value
            
      
def find_astra_archives(h5):
    """
    Searches one 
    """
    if is_astra_archive(h5):
        return ['./']
    else:
        return [g for g in h5 if is_astra_archive(h5[g])]        
        

#----------------------------        
# input
def write_input_h5(h5, astra_input, name='input'):
    """
    
    Writes astra input to h5. 
    
    astra_input is a dict with dicts
    
    See: read_input_h5
    """
    g0 = h5.create_group(name)
    for n in astra_input:
        namelist = astra_input[n]
        g = g0.create_group(n)
        for k in namelist:
            g.attrs[k] = namelist[k]
            
def read_input_h5(h5):
    """
    Reads astra inpu5 from h5
    
    See: write_input_h5
    """
    d = {}
    for g in h5:
        d[g] = dict(h5[g].attrs)
        
        # Convert to native types
        for k, v in d[g].items():
            d[g][k] = native_type(v)
        
    return d

#----------------------------        
# fieldmaps
def write_fieldmap_h5(h5, fieldmap_dict, name='fieldmap'):
    """
    Writes all fieldmaps as simple datasets
    """
    g = h5.create_group(name)
    for k, v in fieldmap_dict.items():
        g[k] = v['data']
        for k2, a in v['attrs'].items():
            g[k].attrs[k2] = a
        
def read_fieldmap_h5(h5):
    d = {}
    for fmap in h5:
        d[fmap] = {}
        d[fmap]['data'] = h5[fmap][:]
        
        # Handle legacy fieldmaps without attrs
        attrs = dict(h5[fmap].attrs)
        if not attrs:
            attrs = {'type': 'astra_1d'}
        d[fmap]['attrs'] = attrs            
            
    return d


#----------------------------        
# output
def write_output_h5(h5, astra_output, name='output'):
    """
    Writes all of astra_output dict to an h5 handle
    
    """
    g = h5.create_group(name)
    
    for name2 in ['stats', 'other']:
        if name2 not in astra_output:
            continue
        
        g2 = g.create_group(name2)
        for key, data in astra_output[name2].items():
            unit = OutputUnits[key]
            write_dataset_and_unit_h5(g2, key, data, unit)
    if 'run_info' in astra_output:
        for k, v in astra_output['run_info'].items():
            g.attrs[k] = v
            
    write_particles_h5(g, astra_output['particles'], name='particles')
            
def read_output_h5(h5):
    """
    Reads a properly archived astra output and returns a dict that corresponds to Astra.output
    """
    
    o = {}
    o['run_info'] = dict(h5.attrs)
    for name2 in ['stats', 'other']:
        if name2 not in h5:
            continue
        g = h5[name2]
        o[name2] = {}
        for key in g:
            expected_unit = OutputUnits[key] # expected unit
            o[name2][key], _ = read_dataset_and_unit_h5(g[key], expected_unit=expected_unit) 
            
    if 'particles' in h5:
        o['particles'] = read_particles_h5(h5['particles'])        
        
    return o

#------------------------------------------
# control groups

def write_control_groups_h5(h5, group_data, name='control_groups'):
    """
    Writes the ControlGroup object data to the attrs in
    an h5 group for archiving. 
    
    See: read_control_groups_h5
    """
    if name:
        g = h5.create_group(name)
    else:
        g = h5
        
    for name, G in group_data.items():
        g.attrs[name] = fstr(G.dumps())



def read_control_groups_h5(h5, verbose=False):
    """
    Reads ControlGroup object data
    
    See: write_control_groups_h5
    """
    group_data = {}
    for name in h5.attrs:
        dat = h5.attrs[name]
        G = ControlGroup()
        G.loads(dat)
        group_data[name] = G
        
        if verbose:
            print('h5 read control_groups:', name, '=', G)
        
    return group_data


#----------------------------        
# particles
        
def write_particles_h5(h5, particles, name='particles'):
    """
    Write all screens to file, simply named by their index
    
    See: read_particles_h5
    """
    g = h5.create_group(name)
    
    # Set base attributes
    opmd_init(h5, basePath=name+'/%T/', particlesPath='/' )
    
    # Loop over screens
    for i, particle_group in enumerate(particles):
        name = str(i)        
        particle_group.write(g, name=name)  
        
        
def read_particles_h5(h5):
    """
    Reads particles from h5
    
    See: write_particles_h5
    """
    # This should be a list of '0', '1', etc.
    # Cast to int, sort, reform to get the list order correct.
    ilist = sorted([int(x) for x in list(h5)])
    glist = [str(i) for i in ilist]
    
    return [ParticleGroup(h5=h5[g]) for g in glist]          
