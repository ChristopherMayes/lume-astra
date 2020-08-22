from astra.fieldmaps import find_fieldmap_ixlist, fieldmap_data, load_fieldmaps
from pmd_beamphysics.units import nice_array, nice_scale_prefix
import numpy as np
import os


from pmd_beamphysics.units import nice_array



import matplotlib.pyplot as plt


# Suggested for notebooks:
#import matplotlib
#matplotlib.rcParams['figure.figsize'] = (16,4)
#%config InlineBackend.figure_format = 'retina'


def old_plot_fieldmaps(astra_input, sections=['cavity', 'solenoid'], fieldmap_dict = {}, verbose=False):
    """
    Plots Cavity and Solenoid fielmaps.
    
    TODO: quadrupoles
    
    """
    
    if fieldmap_dict:
        fmaps = fieldmap_dict
    else:
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
    

    
def add_fieldmaps_to_axes(astra_object, axes, bounds=None,
                           sections=['cavity', 'solenoid'],
                          include_labels=True):
    """
    Adds fieldmaps to an axes.
    
    """

    astra_input = astra_object.input
    
    verbose=astra_object.verbose
    
    if astra_object.fieldmap:
        fmaps = astra_object.fieldmap
    else:    
        fmaps = load_fieldmaps(astra_input, sections=sections, verbose=verbose)
    ax1 = axes
    
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
    
    if bounds:
        ax1.set_xlim(bounds[0], bounds[1])        
        
        
def plot_fieldmaps(astra_object, include_labels=True,  xlim=None, figsize=(12,4), **kwargs):
    """
    Simple fieldmap plot
    """

    fig, axes = plt.subplots(figsize=figsize, **kwargs)

    add_fieldmaps_to_axes(astra_object, axes, bounds=xlim, include_labels=include_labels,
                           sections=['cavity', 'solenoid'])
    

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
    
    add_fieldmaps_to_axes(astra_object, axs[-1], bounds=(xmin, xmax),
                           sections=['cavity', 'solenoid'],
                          include_labels=True)
    
    
def plot_stats_with_layout(astra_object, ykeys=['sigma_x', 'sigma_y'], ykeys2=['sigma_z'], 
                           xkey='mean_z', xlim=None, 
                           nice=True, 
                           include_layout=False,
                           include_labels=True, 
                           include_particles=True, 
                           include_legend=True, **kwargs):
    """
    Plots stat output multiple keys.
    
    If a list of ykeys2 is given, these will be put on the right hand axis. This can also be given as a single key. 
    
    Logical switches, all default to True:
        nice: a nice SI prefix and scaling will be used to make the numbers reasonably sized.
        
        include_legend: The plot will include the legend
        
        include_layout: the layout plot will be displayed at the bottom
        
        include_labels: the layout will include element labels. 
        
    Copied almost verbatim from lume-impact's Impact.plot.plot_stats_with_layout

    """
    I = astra_object # convenience
    
    if include_layout:
        fig, all_axis = plt.subplots(2, gridspec_kw={'height_ratios': [4, 1]}, **kwargs)
        ax_layout = all_axis[-1]        
        ax_plot = [all_axis[0]]
    else:
        fig, all_axis = plt.subplots( **kwargs)
        ax_plot = [all_axis]

    # collect axes
    if isinstance(ykeys, str):
        ykeys = [ykeys]

    if ykeys2:
        if isinstance(ykeys2, str):
            ykeys2 = [ykeys2]
        ax_plot.append(ax_plot[0].twinx())

    # No need for a legend if there is only one plot
    if len(ykeys)==1 and not ykeys2:
        include_legend=False
    
    #assert xkey == 'mean_z', 'TODO: other x keys'
        
    X = I.stat(xkey)
    
    # Only get the data we need
    if xlim:
        good = np.logical_and(X >= xlim[0], X <= xlim[1])
        X = X[good]
    else:
        xlim = X.min(), X.max()
        good = slice(None,None,None) # everything
    
    # Try particles within these bounds
    Pnames = []
    X_particles = []
    
    if include_particles:
        try:
            for pname in range(len(I.particles)): # Modified from Impact
                xp = I.particles[pname][xkey]
                if xp >= xlim[0] and xp <= xlim[1]:
                    Pnames.append(pname)
                    X_particles.append(xp)
            X_particles = np.array(X_particles)
        except:
            Pnames = []
    else:
        Pnames = []
        
    # X axis scaling    
    units_x = str(I.units(xkey))
    if nice:
        X, factor_x, prefix_x = nice_array(X)
        units_x  = prefix_x+units_x
    else:
        factor_x = 1   
    
    # set all but the layout
    for ax in ax_plot:
        ax.set_xlim(xlim[0]/factor_x, xlim[1]/factor_x)          
        ax.set_xlabel(f'{xkey} ({units_x})')    
    

    # Draw for Y1 and Y2 
    
    linestyles = ['solid','dashed']
    
    ii = -1 # counter for colors
    for ix, keys in enumerate([ykeys, ykeys2]):
        if not keys:
            continue
        ax = ax_plot[ix]
        linestyle = linestyles[ix]
        
        # Check that units are compatible
        ulist = [I.units(key) for key in keys]
        if len(ulist) > 1:
            for u2 in ulist[1:]:
                assert ulist[0] == u2, f'Incompatible units: {ulist[0]} and {u2}'
        # String representation
        unit = str(ulist[0])
        
        # Data
        data = [I.stat(key)[good] for key in keys]        
        
        
        
        if nice:
            factor, prefix = nice_scale_prefix(np.ptp(data))
            unit = prefix+unit
        else:
            factor = 1

        # Make a line and point
        for key, dat in zip(keys, data):
            #
            ii += 1
            color = 'C'+str(ii)
            ax.plot(X, dat/factor, label=f'{key} ({unit})', color=color, linestyle=linestyle)
            
            # Particles
            if Pnames:
                try:
                    Y_particles = np.array([I.particles[name][key] for name in Pnames])
                    ax.scatter(X_particles/factor_x, Y_particles/factor, color=color) 
                except:
                    pass     
        ax.set_ylabel(', '.join(keys)+f' ({unit})')            
        #if len(keys) > 1:
        
    # Collect legend
    if include_legend:
        lines = []
        labels = []
        for ax in ax_plot:
            a, b = ax.get_legend_handles_labels()
            lines += a
            labels += b
        ax_plot[0].legend(lines, labels, loc='best')        
    
    # Layout   
    if include_layout:
        
        # Gives some space to the top plot
        #ax_layout.set_ylim(-1, 1.5)          
        
        if xkey == 'mean_z':
            #ax_layout.set_axis_off()
            ax_layout.set_xlim(xlim[0], xlim[1])
        else:
            ax_layout.set_xlabel('mean_z')
            xlim = (0, I.stop)
        add_fieldmaps_to_axes(I,  ax_layout, bounds=xlim, include_labels=include_labels)      