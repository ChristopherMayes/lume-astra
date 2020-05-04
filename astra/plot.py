from astra.fieldmaps import find_fieldmap_ixlist, fieldmap_data, load_fieldmaps
import numpy as np
import os


from pmd_beamphysics.units import nice_array



import matplotlib.pyplot as plt


# Suggested for notebooks:
#import matplotlib
#matplotlib.rcParams['figure.figsize'] = (16,4)
#%config InlineBackend.figure_format = 'retina'


def plot_fieldmaps(astra_input, sections=['cavity', 'solenoid'], fieldmaps = {}, verbose=False):
    """
    Plots Cavity and Solenoid fielmaps.
    
    TODO: quadrupoles
    
    """
    fmaps = load_fieldmaps(astra_input, sections=sections, verbose=verbose)
    
    assert len(sections) == 2, 'TODO: more general'
    
    fig, ax0 = plt.subplots()
    
    # Make RHS axis for the solenoid field. 
    ax1 = ax0.twinx()  
    ax = [ax0, ax1]
    
    ylabel = {'cavity': '$E_z$ (MV/m)', 'solenoid':'$B_z$ (T)'}
    color = {'cavity': 'green', 'solenoid':'blue'}
    
    for i, section in enumerate(sections):
        a = ax[i]
        ixlist = find_fieldmap_ixlist(astra_input, section)
        for ix in ixlist:
            dat = fieldmap_data(astra_input, section=section, index=ix, fieldmaps=fmaps, verbose=verbose)
            label = f'{section}_{ix}'
            c = color[section]
            a.plot(*dat.T, label=label, color=c)
        a.set_ylabel(ylabel[section])
    ax0.set_xlabel('$z$ (m)')
    
    # TODO: is this the correct thing to return?
    return fig



def plot_stats(astra_object, keys=['norm_emit_x', 'sigma_z'], sections=['cavity', 'solenoid'], fieldmaps = {}, verbose=False):
    """
    Plots stats, with fieldmaps plotted from seections. 
    
    TODO: quadrupoles
    
    """
    
    astra_input = astra_object.input
    
    fmaps = load_fieldmaps(astra_input, sections=sections, verbose=verbose)
    
    assert len(sections) == 2, 'TODO: more general'
    
    nplots = len(keys) + 1
    
    fig, axs = plt.subplots(nplots)
    
    # Make RHS axis for the solenoid field. 
    
    
    xdat = astra_object.stat('mean_z')
    xmin = min(xdat)
    xmax = max(xdat)
    for i, key in enumerate(keys):
        ax = axs[i]
        unit = astra_object.units(key)
        ydat = astra_object.stat(key)
        
        ndat, factor, prefix = nice_array(ydat)
        label = f'{key} ({prefix}{unit})'
        ax.set_ylabel(label)
        ax.set_xlim(xmin, xmax)
        ax.plot(xdat, ndat)
    

    ax1 = axs[-1]
    
    ax1rhs = ax1.twinx()  
    ax = [ax1, ax1rhs]
    
    ylabel = {'cavity': '$E_z$ (MV/m)', 'solenoid':'$B_z$ (T)'}
    color = {'cavity': 'green', 'solenoid':'blue'}
    
    for i, section in enumerate(sections):
        a = ax[i]
        ixlist = find_fieldmap_ixlist(astra_input, section)
        for ix in ixlist:
            dat = fieldmap_data(astra_input, section=section, index=ix, fieldmaps=fmaps, verbose=verbose)
            label = f'{section}_{ix}'
            c = color[section]
            a.plot(*dat.T, label=label, color=c)
        a.set_ylabel(ylabel[section])
    ax1.set_xlabel('$z$ (m)')
    ax1.set_xlim(xmin, xmax)
    
    return fig