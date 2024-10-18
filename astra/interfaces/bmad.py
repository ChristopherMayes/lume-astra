
from pmd_beamphysics import FieldMesh
from pmd_beamphysics.fields.analysis import accelerating_voltage_and_phase
from astra.parsers import find_max_pos
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
    
    # v=c voltage NOT GOOD IN INJECTORS
    z0 = fmap['data'][:,0]
    Ez0 = fmap['data'][:,1]
    Ez0 = Ez0/np.abs(Ez0).max() * emax # Normalize
    voltage, _ = accelerating_voltage_and_phase(z0, Ez0, freq)
    
    z_start = pos + z0.min()
    L = round(np.ptp(z0), 9)
    
    # Fill in name
    name = name.format(ix=ix)
    
    # Attributes
    attrs = dict(
        rf_frequency = freq,
        phi0 = phi0,
    )
    if emax == 0:
        attrs['voltage'] = 0 
    else:
        attrs['autoscale_amplitude'] = False
        attrs['field_autoscale'] = emax

    if keyword in ['e_gun', 'lcavity']:
        attrs["L"] = L
        
    if superimpose:
        offset = ref_offset + pos
        attrs['offset'] = ref_offset + pos
        attrs['superimpose'] = True
        attrs['ele_origin'] = ele_origin        
    

    
    dat = {
        'attrs': attrs,
        'ele_key': keyword,
        'ele_name': name,
    }
    
    dat['line'] = ele_line(dat)
    
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
    L = round(np.ptp(z0), 9)   
    
    # Prevent wapping (will fix in Bmad in the future)
    if z_start < 0:
        z_start = 0
        L += z_start
        
    # Fill in name
    name = name.format(ix=ix)
    
    
    attrs = {}
    if keyword == 'solenoid':
        attrs['L'] = L
    else:
        attrs['bs_field'] = bmax
        
    if superimpose:
        attrs['superimpose'] = True
        attrs['ele_origin']  = ele_origin
        attrs['offset'] = ref_offset + pos
    
    info = f"""! B_max = {bmax} T
! \int B dL = B_max * {BL} m
! \int B^2 dL = B_max^2 * {B2L} m
! Hard edge L = {L_hard} m
! Hard edge B = {B_hard} T"""

    
    dat = {
        'attrs': attrs,
        'ele_key': keyword,
        'ele_name': name,
        'info': info
    }
    
    dat['line'] = ele_line(dat)
    
    return dat


def ele_line(ele_dat):
    lines = []
    lines.append(f'{ele_dat["ele_name"]}: {ele_dat["ele_key"]}')
    if "info" in ele_dat:
        lines.append(ele_dat["info"])
    for k, v in ele_dat["attrs"].items():
        lines.append(f"    {k} = {v}")
    line = ',\n  '.join(lines)    
    return line
    
    
    
    
# ------------------    
# PyTao

def ele_info(tao, ele_id):
    """
    Returns a dict of element attributes from ele_head and ele_gen_attribs
    """
    edat = tao.ele_head(ele_id)
    edat.update(tao.ele_gen_attribs(ele_id))
    s = edat['s']
    L = edat['L']
    edat['s_begin'] = s-L
    edat['s_center'] = (s + edat['s_begin'])/2    
    
    return edat

def tao_create_astra_fieldmap_ele(tao,
                            ele_id,
                                 *,
                            cache=None):
    
    # Ele info from Tao
    edat = ele_info(tao, ele_id)
    ix_ele =  edat['ix_ele'] 
    ele_key = edat['key'].upper() 
    
    # FieldMesh
    grid_params = tao.ele_grid_field(ix_ele, 1, 'base', as_dict=False)
    field_file = grid_params['file'].value  
    
    short_fieldmap_name = edat['name']+'_fieldmap.dat'
    if cache is None:
        field_mesh = FieldMesh(field_file)  
        # Convert to 1D fieldmap
        fieldmap = field_mesh.to_astra_1d()
        fieldmap['attrs']['eleAnchorPt'] = field_mesh.attrs['eleAnchorPt']     
    else:
        # Check for existence
        if field_file in cache:
            # Already found
            fieldmap = cache[field_file]      
            short_fieldmap_name = cache['short_fieldmap_name:'+field_file]
        else:
            # New fieldmap, add to cache
            field_mesh = FieldMesh(field_file)
            fieldmap = field_mesh.to_astra_1d()
            # Add anchor
            fieldmap['attrs']['eleAnchorPt'] = field_mesh.attrs['eleAnchorPt'] 
            cache[field_file] = fieldmap
            cache['short_fieldmap_name:'+field_file] = short_fieldmap_name

        
    eleAnchorPt = fieldmap['attrs']['eleAnchorPt']

    # Frequency
    freq = edat.get('RF_FREQUENCY', 0)
    #assert np.allclose(freq, field_mesh.frequency), f'{freq} != {field_mesh.frequency}'   
    
    # Master parameter
    master_parameter = grid_params['master_parameter'].value
    if master_parameter == '<None>':
        master_parameter = None    
    
    # Find z_anchor
    if eleAnchorPt == 'beginning':
        z_anchor = edat['s_begin']
    elif eleAnchorPt == 'center':
        z_anchor = edat['s_center'] 
    else:
        raise NotImplementedError(f'{eleAnchorPt} not implemented')   
        
    # Phase and scale
    if ele_key == 'SOLENOID':
        assert  master_parameter is not None
        scale = edat[master_parameter]   
        
        bfactor = np.abs(fieldmap['data'][:,1]).max() 
        if not np.isclose(bfactor, 1):
            scale *= bfactor
            
        astra_ele = {
         'astra_type': 'solenoid',
         'file_bfield': short_fieldmap_name,
         's_pos': z_anchor,
         'maxb': scale,
         's_xoff': edat['X_OFFSET'],
         's_yoff': edat['Y_OFFSET'],
         's_smooth': 0,
         's_higher_order': True}         
        
        
    elif ele_key in ('E_GUN', 'LCAVITY'):
        if master_parameter is None:
            scale = edat['FIELD_AUTOSCALE']
        else:
            scale = edat[master_parameter]

        efactor = np.abs(fieldmap['data'][:,1]).max()              
        if not np.isclose(efactor, 1):
            scale *= efactor       
            
        phi0_user = sum([edat['PHI0'], edat['PHI0_ERR'] ])   
        
        astra_ele = {
         'astra_type': 'cavity', # This will be later extracted
         'file_efield': short_fieldmap_name,
         'c_pos': z_anchor,
         'maxe': -scale/1e6,
         'nue': freq/1e9,
         'phi': phi0_user * 360,
         'c_xoff': edat['X_OFFSET'],
         'c_yoff': edat['Y_OFFSET'],            
         'c_smooth': 0,
         'c_higher_order': True}          
        
    return astra_ele, {short_fieldmap_name: fieldmap}

def tao_create_astra_quadrupole_ele(tao,
                            ele_id):
    
    edat = ele_info(tao, ele_id)
    
    astra_ele = {
        'q_pos': edat['s_center'],
        'q_grad': -edat['B1_GRADIENT'],
        'q_length': edat['L'],
    }
    
    return astra_ele


def tao_create_astra_lattice_and_fieldmaps(tao,
                                            fieldmap_eles='E_GUN::*,SOLENOID::*,LCAVITY::*', 
                                            quadrupole_eles = 'quad::*',
                                          ):
    """
    Create LUME-Astra style lattice (input namelists) and fieldmaps from a PyTao Tao instance.
    
    
    Parameters
    ----------
    tao: Tao object
    
    fieldmap_eles: str, default = 'E_GUN::*,SOLENOID::*,LCAVITY::*'
        Bmad match string to find fieldmap elements
        
        
    Returns
    -------
    dict with of dict with keys:
        'cavity'
        'solenoid'
        'fieldmap'
    
    """
    
    # Extract elements to use
    ele_ixs = tao.lat_list(fieldmap_eles, 'ele.ix_ele', flags='-array_out -no_slaves')    
    
    # Form lattice and fieldmaps
    cache = {}
    fieldmaps = {}
    cavity = []
    solenoid = []
    for ix_ele in ele_ixs:
        astra_ele, fieldmap_dict = tao_create_astra_fieldmap_ele(tao,
            ele_id=ix_ele,
            cache=cache)    

        fieldmaps.update(fieldmap_dict)
        
        astra_type = astra_ele.pop('astra_type')
        if astra_type == 'cavity':      
            cavity.append(astra_ele) 
        elif astra_type == 'solenoid':
            solenoid.append(astra_ele)
            
            
    # Quadrupoles
    quad_ix_eles = tao.lat_list(quadrupole_eles, 'ele.ix_ele', flags='-array_out -no_slaves')
    quadrupole = []
    for ele_id in quad_ix_eles:
        quadrupole.append(tao_create_astra_quadrupole_ele(tao, ele_id))
            
    # convert to dicts
    cavity_dict = {'lefield':True}
    for ix, ele in enumerate(cavity): 
        for key in ele:
            cavity_dict[f"{key}({ix+1})"] = ele[key]
            
    solenoid_dict = {'lbfield':True}
    for ix, ele in enumerate(solenoid): 
        for key in ele:
            solenoid_dict[f"{key}({ix+1})"] = ele[key]            
            
    quadrupole_dict = {'lquad':True}
    for ix, ele in enumerate(quadrupole): 
        for key in ele:
            quadrupole_dict[f"{key}({ix+1})"] = ele[key]              

    return {'cavity': cavity_dict,
            'solenoid': solenoid_dict,
            'quadrupole': quadrupole_dict,
            'fieldmap': fieldmaps}


def astra_from_tao(tao, cls=None):
    """
    Create a complete Astra object from a running Pytao Tao instance.

    Parameters
    ----------
    tao: Tao object

    Returns
    -------
    astra_object: Astra
        Converted Astra object
    """    
    
    # Create blank object
    if cls is None:
        from astra import Astra as cls
    A = cls() # This has some defaults.
    
    # Check for cathode start
    if len(tao.lat_list('e_gun::*', 'ele.ix_ele')) > 0:
        cathode_start = True  
    else:
        cathode_start = False  
        
    # Special settings for cathode start.
    # TODO: pass these in more elegantly.
    if cathode_start:        
        A.input['output']['cathodes'] = True
        A.input['charge']['lmirror'] = True
    else:
        A.input['output']['cathodes'] = False
        
    # Get elements
    res = tao_create_astra_lattice_and_fieldmaps(tao)
    A.fieldmap.update(res.pop('fieldmap'))
    A.input.update(res)        
    
    # Update zstop
    zmax = find_max_pos(A.input)
    A.input['output']['zstop'] = zmax + 1 # Some padding
    
    return A