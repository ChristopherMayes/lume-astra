"""
Tools for loading fieldmap data
"""
import numpy as np
import re
import os
import glob

# Prefix helpers

POS_PREFIX = {'cavity':'c_pos', 'solenoid':'s_pos'}
def pos_(section='cavity', index=1):
    prefix = POS_PREFIX[section]
    
    return f'{prefix}({index})'

FILE_PREFIX = {'cavity':'file_efield', 'solenoid':'file_bfield'}

def file_(section='cavity', index=1):
    prefix = FILE_PREFIX[section]
    
    return f'{prefix}({index})'

MAX_PREFIX = {'cavity':'maxe', 'solenoid':'maxb'}
def max_(section='cavity', index=1):
    prefix =MAX_PREFIX[section]
    
    return f'{prefix}({index})'


def find_fieldmap_ixlist(astra_input, section='cavity'):
    """
    
    Looks for the appropriage file_efield(i) and extracts the integer i
    """
    
    dat = astra_input[section]
    prefix = FILE_PREFIX[section]
    ixlist = []
    for k in astra_input[section]:
        if k.startswith(prefix):
            m = re.search(r"\(([0-9]+)\)", k)
            ix = int(m.group(1))
            ixlist.append(ix)
    return ixlist

def load_fieldmaps(astra_input, search_paths=[], fieldmap_dict={}, sections=['cavity', 'solenoid'], verbose=False, strip_path=False):
    """
    Loads all found fieldmaps into a dict with the filenames as keys
    """
    fmap = {}
    for sec in sections:
        
        if sec not in astra_input:  
            continue
        
        ixlist = find_fieldmap_ixlist(astra_input, sec) 
        for ix in ixlist:
            k = file_(section=sec, index=ix)
            file = astra_input[sec][k]

            # Skip 3D fieldmaps. These are symlinked
            if os.path.split(file)[1].lower().startswith('3d_'):
                continue
            
            if file not in fmap:
                # Look inside dict
                if file in fieldmap_dict:
                    if verbose:
                        print(f'Fieldmap inside dict: {file}')
                    fmap[file] = fieldmap_dict[file]
                    continue
                    
                if verbose:
                    print(f'Loading fieldmap file {file}')                    
                
                # Look in search path
                if not os.path.exists(file):
                    if verbose:
                        print(f'{file} not found, searching:')
                    for path in search_paths:
                        _, file = os.path.split(file)
                        tryfile = os.path.join(path, file)
                                         
                        if os.path.exists(tryfile):
                            if verbose:
                                print('Found:', tryfile)
                            file = tryfile
                            break
                            
                            
                    # Set input
                    astra_input[sec][k] = file
                    
                fmap[file] = parse_fieldmap(file)
           
    # Loop again
    if strip_path:
        # Make a secondary dict with the shorter names. 
        # Protect against /path1/dat1, /path2/dat1 overwriting
        fmap2 = {}
        translate = {}
        for k in fmap:
            _, k2 = os.path.split(k)
            i=0 # Check for uniqueness
            while k2 in fmap2:
                i+=1
                k2 = f'{k2}_{i}'
            # Collect translation
            translate[k] = k2
            fmap2[k2] = fmap[k] 

        for sec in sections:
            ixlist = find_fieldmap_ixlist(astra_input, sec) 
            for ix in ixlist:
                k = file_(section=sec, index=ix)
                file = astra_input[sec][k]
                astra_input[sec][k] = translate[file]

        return fmap2
                
    else:
        return fmap
   

def write_fieldmaps(fieldmap_dict, path):
    """
    Writes fieldmap dict to path
    
    """
    assert os.path.exists(path)
    
    for k, fmap in fieldmap_dict.items():
        file = os.path.join(path, k)
        
        # Remove any previous symlinks
        if os.path.islink(file):
            os.unlink(file)        
        
        write_fieldmap(file, fmap)

def write_fieldmap(fname, fmap):
    
    attrs = fmap['attrs']
    ftype = attrs['type']
    if ftype == 'astra_tws':
        header = f"{attrs['z1']} {attrs['z2']} {attrs['n']} {attrs['m']}"
        np.savetxt(fname, fmap['data'], header=header, comments='')
    elif ftype == 'astra_1d':
        np.savetxt(fname, fmap['data'])
    else:
        raise ValueError(f'Unknown fieldmap type: {ftype}')        
        
    
def parse_fieldmap(filePath):
    """
    Parses 1D fieldmaps, including TWS fieldmaps. 
    
    See p. 70 in the Astra manual for TWS
    
    Returns a dict of:
        attrs
        data
        
    See: write_fieldmap
    
    """
    
    header = list(map(float, open(filePath).readline().split()))
    
    attrs = {}
    
    if len(header) == 4:
        attrs['type'] = 'astra_tws'
        attrs['z1'] = header[0]
        attrs['z2'] = header[1]
        attrs['n']  = int(header[2])
        attrs['m']  = int(header[3])
        data = np.loadtxt(filePath, skiprows=1)
    else:
        attrs['type'] = 'astra_1d'
        data = np.loadtxt(filePath)
        
    return dict(attrs=attrs, data=data)




def fieldmap_data(astra_input, section='cavity', index=1, fieldmaps={}, verbose=False):
    """
    Loads the fieldmap in absolute coordinates.
    
    If a fieldmaps dict is given, thes will be used instead of loading the file.
    
    Returns tuple:
        attrs, data
    
    """
    
    adat = astra_input[section] # convenience pointer
    
    # Position
    k = pos_(section, index)
    if k in adat:
        offset = adat[k]
    else:
        offset = 0
        
    file = adat[file_(section, index)]
    
    # TODO: 3D fieldmaps
    if os.path.split(file)[1].lower().startswith('3d_'):
        return None
    
    # Scaling
    k = max_(section, index)
    if k in adat:
        scale = adat[k]
    else:
        scale = 1
    
    
    if file in fieldmaps:
        fmap = fieldmaps[file].copy()
    else:
        print(f'loading from file {file}')
        fmap = parse_fieldmap(file)
            
    dat = fmap['data'].copy()    
    
    # TWS special case 
    # From the manual: 
    # field map can be n times periodically repeated by specifying C_numb( ) = n.
    if section == 'cavity':
        # Look for this key
        k2 = f'c_numb({index})'
        if k2 in astra_input[section]:
            n_cell = astra_input[section][k2]
            
            if n_cell > 1:
                zfull, Ezfull = expand_tws_fmap(fmap, n_cell)
                dat = np.array([zfull, Ezfull]).T

    
    dat[:,0] += offset
    dat[:,1] *= scale/max(abs(dat[:,1]))

    #print(dat[:,0].min())
    
    return dat




def expand_tws_fmap(fmap, n_cell):
    """
    Expands periodic TWS fieldmap data over a number of repeating cells:
    |Entrance | Cells | Exit | -> |Entrance | Cells| ...|Cells| Exit | 
              z0     z1                     --- n_repeat ----
    Takes care not to overlap points.
    
    The the body of the fieldmap has: 
        m_cells_in_body  = fmap['attrs']['m']
    So:
        n_repeat = int(n_cell / m_cells_in_body)
    
    Returns
    -------
    z, Ez : tuple of arrays
    
    """

    z0, Ez0 = fmap['data'].T
    zmin = z0.min()
    zmax = z0.max()
    # Beg and end of cell
    z1 = fmap['attrs']['z1']
    z2 = fmap['attrs']['z2']
    m_cells_in_body = fmap['attrs']['m']
    # Approximate spacing
    dz = np.mean(np.diff(z0))
    Lentrance = z1-zmin
    Lexit = zmax-z2
    Lcell = z2-z1
    
    #
    n_repeat = int(n_cell / m_cells_in_body)
    
    # Z arrays to be used to construct the full map
    zentrance = np.linspace(zmin, z1, int(round(Lentrance/dz+1)))
    zcell     = np.linspace(z1, z2,   int(round(Lcell/dz+1)))
    zexit     = np.linspace(z2, zmax, int(round(Lexit/dz+1))) 
    
    Ezentrance = np.interp(zentrance, z0, Ez0)
    Ezcell = np.interp(zcell, z0, Ez0)
    Ezexit = np.interp(zexit, z0, Ez0)    
    
    # Collect data, not overlapping points
    ztot =  [zentrance[:-1]]
    Eztot = [Ezentrance[:-1]]
    for i in range(n_repeat):
        ztot.append(zcell[:-1] + i*Lcell)
        Eztot.append(Ezcell[:-1])
    ztot.append(zexit + (n_repeat-1)*Lcell)
    Eztot.append(Ezexit)
    
    return np.concatenate(ztot), np.concatenate(Eztot)


def fieldmap3d_filenames(base_filename):
    """
    Returns a list of existing 3D fieldmap filenames corresponding to a base filename.
    
    Example: 
        fieldmap3d_filenames('3D_7500Vchopmap') returns:
        ['/abs/path/to/3D_7500Vchopmap.ey', ...]

    """

    _, name = os.path.split(base_filename)
    assert name.lower().startswith('3d_')

    flist = glob.glob(base_filename+'.*')
    
    files = []
    for file in flist:
        for ext in ['.ex', '.ey', '.ez', '.bx', '.by', 'bz']:
            if file.lower().endswith(ext):
                files.append(os.path.abspath(file))
    return files
