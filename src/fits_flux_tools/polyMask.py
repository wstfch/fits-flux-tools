#!/usr/bin/env python
# Author: Xiaohui Sun
#=============================================================================#
# NAME:     polyMask.py                                                       #
#                                                                             #
# PURPOSE:  Script to load a FITS image and allow the user to draw and save   #
#           save polygons to a text file.                                     #
#                                                                             #
# WRITTEN:  Cormac Purcell                                                    #
# MODIFIED: Shengtao Wang                                                     #
#                                                                             #
#=============================================================================#
import argparse
import os, sys, re
from matplotlib.collections import RegularPolyCollection
from matplotlib.collections import PatchCollection
from matplotlib.patches import Polygon
import matplotlib.cm as cm
from matplotlib.widgets import Button, Slider
from matplotlib.pyplot import figure, show
from pylab import *
from astropy.io import fits as pf
import astropy.wcs as wcs 
import numpy as np
import json
matplotlib.use('QtAgg')
#-----------------------------------------------------------------------------#
def main():
    parser = argparse.ArgumentParser(description="Draw source/background polygons on a FITS image and save mask files.")
    parser.add_argument("filename", help="FITS image filename.")
    parser.add_argument("--save_reg", action="store_true", help="Also save DS9 region files (*.image.reg and *.fk5/*.galactic.reg).")

    # Load the FILE file
    args = parser.parse_args()
    fitsName = args.filename
    save_reg = args.save_reg
    [header,xydata]=load_fits_image(fitsName)

    stripHeadKeys = ['PC1_1','PC1_2','PC2_1','PC2_2','PC3_1','PC3_2','PC4_1','PC4_2']
    for key in stripHeadKeys:
        if key in header: del header[key]

    if 'BMAJ' not in header:
        print("Please provide beam information!")
        header['BMAJ'] = float(input("BMAJ in deg: "))
        header['BMIN'] = float(input("BMIN in deg: "))
        header['BPA'] = float(input("BPA in deg: "))

    w = wcs.WCS(header)
    
    # Read the max and min of the data array
    zmin = np.min(xydata[~np.isnan(xydata)])
    zmax = np.max(xydata[~np.isnan(xydata)])
    
    #------------------------ Setup the figure for plotting ------------------#

    # Define a figure on which to plot the image
    fig = figure(figsize=(14, 10))
    axplot = fig.add_subplot(1,1,1)
    axplot.set_title("Click to define a polygon.")
    subplots_adjust(bottom=0.12)

    # Plot the image data and colorbar
    cax = axplot.imshow(xydata, interpolation='nearest', origin='lower',
                        cmap=cm.jet,vmin=zmin,vmax=zmax)
    cbar=colorbar(cax,pad=0.0)

    # Add the buttons to the bottom edge
    axreset = axes([0.18, 0.025, 0.12, 0.04])
    axsave_src = axes([0.35, 0.025, 0.18, 0.04])
    axsave_bkg = axes([0.57, 0.025, 0.22, 0.04])
    breset = Button(axreset, 'Reset')
    bsave_src = Button(axsave_src, 'Save Source')
    bsave_bkg = Button(axsave_bkg, 'Save Background')

    #------------------------ Polygon editor class ---------------------------#

    class ThreePolyEditor:
        """
        Left-click to add a point to the current polygon. Middle-click to delete
        the last point and right-click to close the polygon.
        """
    
        def __init__(self):
            self.mode = 'src'
        
            # Lists to store the vertices of the source, sky background and
            # exclusion-zone polygons
            self.offsetsLol = []     # list of lists storing polygons
            self.offsets = []        # general working array
            self.apertures = []      # completed polygons for plotting
            
            # Working polygon collection (points plotted as small polys)
            self.points = RegularPolyCollection(
                10,
                rotation=0,
                sizes=(50,),
                facecolors = 'white',
                edgecolors = 'black',
                linewidths = (1,),
                offsets = self.offsets,
                transOffset = axplot.transData
                )

        # Handle mouse clicks
        def onclick(self,event):
            
            # Disable click events if using the zoom & pan modes.
            if fig.canvas.widgetlock.locked():
                return

            if event.button==1:
            
                # Left-click on plot = add a point
                if axplot.contains(event)[0] and self.mode != 'done':
                    x = event.xdata
                    y = event.ydata
                    self.offsets.append((x,y))
                    self.points.set_offsets(self.offsets)
                    if len(self.offsets)==1 : axplot.add_collection(self.points)
                    self.update()
                
                # Right-click on wedge = halve the lower colour clip
                if cbar.ax.contains(event)[0]:
                    clims = cax.get_clim()
                    cax.set_clim(clims[0]/2.0,clims[1])
                    self.update()
                
            elif event.button==2:
            
                # Middle-click = delete last created point
                if axplot.contains(event)[0] and len(self.offsets)>0 \
                       and self.mode != 'done':
                    self.offsets.pop(-1)
                    if len(self.offsets)==0:
                        self.points.remove()
                    else:
                        self.points.set_offsets(self.offsets)
                    self.update()
                
                # Middle-click on wedge = reset the colour clip
                if cbar.ax.contains(event)[0]:
                    clims = cax.get_clim()
                    cax.set_clim(zmin,zmax)
                    self.update()
                
            if event.button==3:
            
                # Right-click on plot = complete the polygon
                if  axplot.contains(event)[0] and len(self.offsets)>2 \
                       and self.mode != 'done':
                    cpoly = Polygon(self.offsets, animated=False,linewidth=2.0)
                    cpoly.set_edgecolor('white')
                    cpoly.set_facecolor('none')
                    self.apertures.append(axplot.add_patch(cpoly))
                    self.update('complete')
            
                # Right-click on wedge = halve the upper colour clip
                if cbar.ax.contains(event)[0]:
                    clims = cax.get_clim()
                    cax.set_clim(clims[0],clims[1]/2.0)
                    self.update()

        # Store completed polygons
        def update(self,action=''):

            # When a polygon is complete switch to the next mode
            if action == 'complete':
                self.mode = 'src'
                self.offsetsLol.append(self.offsets)
                self.offsets = []
                
            # When the reset button is complete clear the polygon lists & plot
            elif action == 'reset':
                self.offsets = []
                self.offsetsLol = []
                self.mode = 'src'
                for i in range(len(axplot.collections)):
                    axplot.collections.pop()
                for aperture in self.apertures:
                    aperture.remove()
                self.apertures = []
                cax.set_clim(zmin,zmax)

            # Redraw the canvas
            fig.canvas.draw()

        # Reset the plot and clear polygons
        def doreset(self, event):
            self.update('reset')

        def save_outputs(self, stem):
            if len(self.offsetsLol) != 1:
                print("Please draw exactly one polygon before saving.")
                return

            suffix = '.fits'
            if fitsName.endswith(suffix):
                nameRoot = fitsName[:-len(suffix)]
            else:
                nameRoot = fitsName

            poly = self.offsetsLol[0]
            indices = get_pix_in_poly(poly,xydata)
            mask = np.zeros_like(xydata)
            for x,y in indices:
                if 0 <= y < mask.shape[0] and 0 <= x < mask.shape[1]:
                    mask[y,x]=1.0

            if stem == '.mask.source':
                outName = nameRoot + '.mask_source.fits'
            else:
                outName = nameRoot + '.mask_bakg.fits'

            print("\nSaving mask to file '%s' ... "% outName)
            sys.stdout.flush()
            pf.writeto(outName, mask, header, overwrite=True)
            print("done.")
            sys.stdout.flush()

            if not save_reg:
                return

            # ---------- 1) write to image coord .reg（pixel value，DS9 image，1-based） ----------
            img_reg = nameRoot + f'{stem}.image.reg'
            with open(img_reg, 'w') as f:
                f.write('# Region file format: DS9 version 4.1\n')
                f.write('image\n')  # using DS9 image coord
                pts = ','.join(f'{x+1:.2f},{y+1:.2f}' for x, y in poly)
                f.write(f'polygon({pts})\n')

            # ---------- 2) write to wcs coord .reg（fk5 or galactic） ----------
            ctype1 = header.get('CTYPE1', '').upper()
            ctype2 = header.get('CTYPE2', '').upper()
            if ctype1.startswith('RA') and ctype2.startswith('DEC'):
                world_sys = 'fk5'
            elif ctype1.startswith('GLON') and ctype2.startswith('GLAT'):
                world_sys = 'galactic'
            else:
                world_sys = 'fk5'  # If not sure use fk5（unit：degree）

            wld_reg = nameRoot + f'{stem}.{world_sys}.reg'
            with open(wld_reg, 'w') as f:
                f.write('# Region file format: DS9 version 4.1\n')
                f.write(f'{world_sys}\n')  # fk5 or galactic
                world = w.wcs_pix2world(np.array(poly), 0)  # Nx2 数组
                pts = ','.join(f'{a:.7f},{b:.7f}' for a, b in world)
                f.write(f'polygon({pts})\n')

            print("Saved DS9 region files:")
            print("  ", img_reg)
            print("  ", wld_reg)
            print("done.")

        def dosave_source(self, event):
            self.save_outputs('.mask.source')

        def dosave_background(self, event):
            self.save_outputs('.mask.bakg')

#-----------------------------------------------------------------------------#

    # Make an instance of the poly-editor and bind events to methods
    editor = ThreePolyEditor()
    fig.canvas.mpl_connect('button_press_event', editor.onclick)
    breset.on_clicked(editor.doreset)
    bsave_src.on_clicked(editor.dosave_source)
    bsave_bkg.on_clicked(editor.dosave_background)

    # Draw the plot to the screen
    show()

#-----------------------------------------------------------------------------#
# Query if a point is inside the polygon                                      #
#-----------------------------------------------------------------------------#
def point_in_poly(px,py,poly):

        cn = 0

        i = -1
        j = 0
        while j < len(poly):
            qx, qy = poly[i]
            rx, ry = poly[j]

            if (px, py) == (qx, qy):
                return True

            if (    ((qy <= py) and (ry > py)) or \
                    ((qy > py) and (ry <= py))    ):
                vt = (py - qy) / (ry - qy)
                if (px < qx + vt * (rx - qx)):
                    cn += 1

            i = j
            j += 1

        return cn%2 



#-----------------------------------------------------------------------------#
# Return the indices of the pixels inside a polygon                           #
#-----------------------------------------------------------------------------#
def get_pix_in_poly(poly,array):

    indices = []

    # Get the bounds of the poly vertices
    px = np.array(poly)[:,0]
    py =  np.array(poly)[:,1]
    px_min = int(floor(min(px)))
    px_max = int(ceil(max(px)))
    py_min = int(floor(min(py)))
    py_max = int(ceil(max(py)))
    
    for i in range(px_min,px_max+1):
        for j in range(py_min,py_max+1):
            if point_in_poly(i,j,poly):
                indices.append((i,j))

    return indices
          
#-----------------------------------------------------------------------------#
# Load a fits image and return the data and dimensions                        #
#-----------------------------------------------------------------------------#
def load_fits_image(filename):
    
    # Read the header and image data from the file
    header=pf.getheader(filename)
    data = pf.getdata(filename)
    naxis = len(data.shape)

    # Strip unused dimensions from the data array
    if naxis == 2:
        xydata = data.copy()
        del data
    elif naxis == 3:
        xydata = data[0].copy()
        del data
    elif naxis == 4:
        xydata = data[0][0].copy()
        del data
    elif naxis == 5:
        xydata = data[0][0][0].copy()
        del data
    else:
        print("Data array contains %s axes" % naxis)
        print("This script supports up to 5 axes only.")
        sys.exit(1)

    # Strip unused dimensions from the header
    stripHeadKeys = ['NAXIS','CRVAL','CRPIX','CDELT','CTYPE','CROTA',
                     'CD1_','CD2_','PC1_','PC2_','PC3_','PC4_','CUNIT']
    if naxis >= 3:
        for i in range(3,6):
            for key in stripHeadKeys:
                if (key+str(i)) in header: del header[key+str(i)]
        header['NAXIS'] = 2

    # Determine the coordinate type and the corresponding keyword index
    # Make a note in the header
    ra_regx = re.compile('^RA')
    dec_regx = re.compile('^DEC')
    glon_regx = re.compile('^GLON')
    glat_regx = re.compile('^GLAT')
    for i in range(int(header['NAXIS'])):
        keyword = "CTYPE"+str(i+1)
        if ra_regx.match(header[keyword]): coord_type="EQU"; x_indx=i+1
        if dec_regx.match(header[keyword]): y_indx=i+1
        if glon_regx.match(header[keyword]): coord_type="GAL"; x_indx=i+1
        if glat_regx.match(header[keyword]): y_indx=i+1
    if not x_indx or not y_indx:
        print("Failed to find Equatorial or Galactic axis coordinate types.")
        del data; del header
        sys.exit(1)
    else:
        header['XINDEX'] = x_indx
        header['YINDEX'] = y_indx

    # Convert AIPS clean-beam types to standard BMAJ, BMIN, BPA
    try:
        bmaj = header['CLEANBMJ']
        bmin = header['CLEANBMN']
        bpa = header['CLEANBPA']
        header.update('BMAJ',bmaj)
        header.update('BMIN',bmin)
        header.update('BPA',bpa)
    except Exception:
        print("No AIPS style beam keywords found.")
        
    # Check for PIXSCAL keywords and write to CDELT standard
    try:
        xdelt=(-1)*(header['PIXSCAL'+str(x_indx)])/3600.0
        ydelt=(header['PIXSCAL'+str(y_indx)])/3600.0
        header['CDELT'+str(x_indx)] = xdelt
        header['CDELT'+str(y_indx)] = ydelt
    except Exception:
        pass

    return [header,xydata]

if __name__ == "__main__":
    main()

