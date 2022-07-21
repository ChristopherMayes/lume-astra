

from pmd_beamphysics.fields.analysis import accelerating_voltage_and_phase
import numpy as np
import os


def bmad_cavity(astra_object, ix,
                name='CAV{ix}',
                keyword='lcavity',
                superimpose=True,
                ele_origin='center', 
                ref_offset = 0):
    """
    
    Parameters
    ----------
    
    astra_object : Astra class

    name : str
        Name of the element. This can be

    ix : int
        Cavity element index in the astra input, as in `c_pos(3)` for ix=3

    
    keyword : str
        Element keyword
            'e_gun' : make a Bmad e_gun element
            'lcavity' : make an Bmad lcavity element
            'some_existing_ele' : use a pre-defined Bmad element
    
    
    superimpose : bool
        Use superposition in Bmad to place the element. Default = True    
    
    ref_offset : float
        Addition offset to be used for superposition
    
    Returns
    -------
    
    line : str
        Bmad line text (may contain \\n)
    
    
    """
    cav = astra_object.input['cavity']
    
    pos = cav[f'c_pos({ix})'] #m
    freq = cav[f'nue({ix})'] * 1e9 # Hz
    emax = cav[f'maxe({ix})']*1e6 # V/m
    _, fieldmap = os.path.split(cav[f'file_efield({ix})'])
    fmap = astra_object.fieldmap[fieldmap]
    phi0 = cav[f'phi({ix})']/360
    
    # v=c voltage
    z0 = fmap['data'][:,0]
    Ez0 = fmap['data'][:,1]
    Ez0 = Ez0/np.abs(Ez0).max() * emax # Normalize
    voltage, _ = accelerating_voltage_and_phase(z0, Ez0, freq)
    
    z_start = pos + z0.min()
    L = round(z0.ptp(), 9)
    
    # Fill in name
    name = name.format(ix=ix)
    
    lines = []
    lines.append(f'{name}: {keyword}')
    lines.append(f'rf_frequency = {freq}, voltage = {voltage}, phi0 = {phi0}')
    
    if keyword in ['e_gun', 'lcavity']:
        lines.append(f'L = {L}')

    if superimpose:
        lines.append(f'superimpose, ele_origin = {ele_origin}, offset = {ref_offset + pos}')
    
    line = ',\n  '.join(lines)
    
    dat = {
        'line': line,
        'z_end': z_start + L
    }
    
    return dat


def bmad_solenoid(astra_object, ix,
                  name='SOL{ix}',
                  keyword='solenoid',
                  superimpose=True,
                  ele_origin='center', 
                  ref_offset = 0):
    """
    
    
    Returns
    -------
    
    
    """
    sol = astra_object.input['solenoid']
    
    pos = sol[f's_pos({ix})'] #m
    bmax = sol[f'maxb({ix})'] # T
    _, fieldmap = os.path.split(sol[f'file_bfield({ix})'])
    fmap = astra_object.fieldmap[fieldmap]    

    z0 = fmap['data'][:,0]
    Bz0 = fmap['data'][:,1]
    Bz0 = Bz0/Bz0.max()

    BL  = np.trapz(Bz0, z0)
    B2L = np.trapz(Bz0**2, z0)
    
    L_hard = BL**2/B2L
    B_hard = B2L/BL * bmax
    
    z_start = pos + z0.min()
    L = round(z0.ptp(), 9)   
    
    # Prevent wapping (will fix in Bmad in the future)
    if z_start < 0:
        z_start = 0
        L += z_start
        
    # Fill in name
    name = name.format(ix=ix)
    
    lines = []
    lines.append(f'{name}: {keyword}')
    # Some useful info
    lines.append(f'! B_max = {bmax} T')
    lines.append(f'! \int B dL = B_max * {BL} m')
    lines.append(f'! \int B^2 dL = B_max^2 * {B2L} m')
    lines.append(f'! Hard edge L = {L_hard} m')
    lines.append(f'! Hard edge B = {B_hard} T')
    
    if keyword == 'solenoid':
        lines.append(f'L = {L}')    
    else:
        lines.append(f'bs_field = {bmax}')
    
    if superimpose:
        lines.append(f'superimpose, ele_origin = {ele_origin}, offset = {ref_offset + pos}')
    

    
    line = ',\n  '.join(lines)
    
    dat = {
        'line': line,
        'L_hard': L_hard,
        'B_hard': B_hard,
        'z_end': z_start + L
    }
    
    return dat