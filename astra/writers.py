import numpy as np


def write_astra_particles_h5(h5, name, astra_data, species='electron'):
    # Write particle data at a screen in openPMD BeamPhysics format
    # https://github.com/DavidSagan/openPMD-standard/blob/EXT_BeamPhysics/EXT_BeamPhysics.md
    
    g = h5.create_group(name)
    
    g.attrs['speciesType'] = species
    
    #g.attrs['totalCharge'] = np.sum(astra_data[''])
    
    n_particle = len(astra_data['x'])
    
    # Position
    g['position/x']=astra_data['x'] # in meters
    g['position/y']=astra_data['y']
    g['position/z']=astra_data['z_rel']
    g['position'].attrs['unitSI'] = 1.0
    g['position'].attrs['unitDimension']=(1., 0., 0., 0., 0., 0., 0.) # m
    
    
    # positionOffset (Constant record)
    # Just z
    g2 = g.create_group('positionOffset/z')
    g2.attrs['value'] = astra_data['z_ref']
    g2.attrs['shape'] = (n_particle)
    g2.attrs['unitSI'] =  g['position'].attrs['unitSI']
    g2.attrs['unitDimension'] = g['position'].attrs['unitDimension']
    
    # momenta
    g['momentum/px']=astra_data['px'] # m*c*gamma*beta_x in eV/c
    g['momentum/py']=astra_data['py']
    g['momentum/pz']=astra_data['pz_rel']
    g['momentum'].attrs['unitSI']= 5.34428594864784788094e-27 # eV/c in J/(m/s) =  kg*m / s
    g['momentum'].attrs['unitDimension']=(1., 1., -1., 0., 0., 0., 0.) # kg*m / s
    
    # momentumOffset (Constant record)
    # Just pz
    g2 = g.create_group('momentumOffset/pz')
    g2.attrs['value'] = astra_data['pz_ref']
    g2.attrs['shape'] = (n_particle)
    g2.attrs['unitSI'] = g['momentum'].attrs['unitSI']
    g2.attrs['unitDimension'] = g['momentum'].attrs['unitDimension']
    
    # Time
    g['time'] = astra_data['t_rel']
    g['time'].attrs['unitSI'] = 1.0 # s
    g['time'].attrs['unitDimension'] = (0., 0., 1., 0., 0., 0., 0.) # s
    
    # Time offset (Constant record)
    g2 = g.create_group('timeOffset')
    g2.attrs['value'] = astra_data['t_ref']
    g2.attrs['shape'] = (n_particle)
    g2.attrs['unitSI'] = g['time'].attrs['unitSI']
    g2.attrs['unitDimension'] = g['time'].attrs['unitDimension']
    
    # Weights
    g['weight'] = astra_data['qmacro']
    g['weight'].attrs['unitSI'] = 1.0
    g['weight'].attrs['unitDimension']=(0., 0., 1, 1., 0., 0., 0.) # Amp*s = Coulomb
    
    
    # Status
    g['particleStatus'] = astra_data['status']
    
    


# Write input file to dataset
def write_input_h5(h5, astra_input, name='input'):
    """
    astra_input is a dict with dicts
    Writes 
    """
    g0 = h5.create_group(name)
    for n in astra_input:
        namelist = astra_input[n]
        g = g0.create_group(n)
        for k in namelist:
            g.attrs[k] = namelist[k]

    
def write_output_h5(h5, astra_output, name='output'):
    """
    Writes scalar data as attributes, otherwise makes datasets
    """
    g = h5.create_group(name)
    for key in astra_output:
        val = astra_output[key]
        if np.isscalar(val):
            g.attrs[key] = val
        else:
            g[key] = val    
    
def write_screens_h5(h5, astra_screens, name='screen'):
    """
    Write all screens to file, simply named by their index
    """
    g = h5.create_group(name)
    for i in range(len(astra_screens)):
        name = str(i)        
        write_astra_particles_h5(g, name, astra_screens[i])    
        
        
        
        
        