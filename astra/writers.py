import numpy as np




def fstr(s):
    """
    Makes a fixed string for h5 files
    """
    return np.string_(s)



def opmd_init(h5, basePath='/screen/%T/', particlesPath='/' ):
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



def write_astra_particles_h5(h5, name, astra_data, species='electron'):
    """
    Write particle data at a screen in openPMD BeamPhysics format
    https://github.com/DavidSagan/openPMD-standard/blob/EXT_BeamPhysics/EXT_BeamPhysics.md
    """

    g = h5.create_group(name)
      
    n_particle = len(astra_data['x'])
    # Indices of good particles
    good = np.where(astra_data['status'] == 5)
    
    #-----------
    # Attributes
    g.attrs['speciesType'] = fstr(species)
    g.attrs['numParticles'] = n_particle
    g.attrs['chargeLive'] = abs(np.sum(astra_data['qmacro'][good])) # Make positive
    g.attrs['chargeUnitSI'] = 1
    #g.attrs['chargeUnitDimension']=(0., 0., 1, 1., 0., 0., 0.) # Amp*s = Coulomb
    g.attrs['totalCharge'] = abs(np.sum(astra_data['qmacro'])) 
   
    #---------
    # Datasets
    
    # Position
    g['position/x']=astra_data['x'] # in meters
    g['position/y']=astra_data['y']
    g['position/z']=astra_data['z_rel']
    for component in ['position/x', 'position/y', 'position/z', 'position']: # Add units to all components
        g[component].attrs['unitSI'] = 1.0
        g[component].attrs['unitDimension']=(1., 0., 0., 0., 0., 0., 0.) # m
    
    
    # positionOffset (Constant record)
    # Just z
    g2 = g.create_group('positionOffset/z')
    g2.attrs['value'] = astra_data['z_ref']
    g2.attrs['shape'] = (n_particle)
    g2.attrs['unitSI'] =  g['position'].attrs['unitSI']
    g2.attrs['unitDimension'] = g['position'].attrs['unitDimension']
    
    # momenta
    g['momentum/x']=astra_data['px'] # m*c*gamma*beta_x in eV/c
    g['momentum/y']=astra_data['py']
    g['momentum/z']=astra_data['pz_rel']
    for component in ['momentum/x', 'momentum/y', 'momentum/z', 'momentum']: 
        g[component].attrs['unitSI']= 5.34428594864784788094e-28 # eV/c in J/(m/s) =  kg*m / s
        g[component].attrs['unitDimension']=(1., 1., -1., 0., 0., 0., 0.) # kg*m / s
    
    # momentumOffset (Constant record)
    # Just pz
    g2 = g.create_group('momentumOffset/z')
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
    # The standard defines 1 as a live particle, but astra uses 1 as a 'passive' particle
    # and 5 as a 'standard' particle. 2 is not used. 
    # To preserve this information, make 1->2 and then 5->1
    
    status = astra_data['status'].copy()
    where_1 = np.where(status==1)
    where_5 = good # was defined above
    status[where_1] = 2
    status[where_5] = 1
    g['particleStatus'] = status
    g['particleStatus'].attrs['unitSI'] = 1.0
    g['particleStatus'].attrs['unitDimension']=(0., 0., 0, 0., 0., 0., 0.) # Dimensionless
    


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
    
    # Set base attributes
    opmd_init(h5, basePath='/'+name+'/%T/', particlesPath='/' )
    
    # Loop over screens
    for i in range(len(astra_screens)):
        name = str(i)        
        write_astra_particles_h5(g, name, astra_screens[i])   
        
         
        
        
        
        
        