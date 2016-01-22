from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)
from future.builtins.disabled import (apply, cmp, coerce, execfile,
                             file, long, raw_input, reduce, reload,
                             unicode, xrange, StandardError)

import sys, random, math
import itertools as it
import collections as col

import numpy as np
import matplotlib.pyplot as plt

import forgi.threedee.model.coarse_grain as ftmc
import forgi.threedee.model.projection2d as ftmp
import forgi.threedee.utilities.vector as ftuv

#The CONDENSE constant is used to simulate a reduced resolution. 
#The algorithm for doing so is work in progress.
#For now, a value less than 20 is reasonable.
CONDENSE=0

if __name__=="__main__":
    #This script expects a list of *.cg/ *.coord files as command line arguments (and nothing else)
    files=sys.argv[1:]

    #Uncomment the following line to display the files in a random order.
    #random.shuffle(files)

    #Prepare the pyplot figure
    totalFigures=len(files)
    figuresPerLine=int(math.ceil(math.sqrt(totalFigures)))
    fig, ax=plt.subplots(int(math.ceil(totalFigures/figuresPerLine)),figuresPerLine, squeeze=False)
    
    #Uncomment the following line to change the background color of the figure (not the plot).
    #fig.patch.set_facecolor('black')

    #Plot one projection per file.
    for i, file_ in enumerate(files):
        #get the subplot axes (Note: axes != axis in matplotlib)
        current_axes=ax[i//figuresPerLine, i%figuresPerLine]

        #Parse the file
        cg=ftmc.CoarseGrainRNA(file_)

        # Random projection direction. Change to direction=[1.,1.,0.] to set a specific direction
        direction=[ 0.45453935,  0.35148226, -0.81844634]#ftuv.get_random_vector()

        #Generate the projection object
        proj=ftmp.Projection2D(cg, direction, rotation=180)   

        #Simulate a reduced resolution of the image.     
        proj.condense(CONDENSE)

        elems=["h5", "h6", "m15", "m12", "h1" ]
        comb=list(it.combinations(elems, 2))
        #Plot the projection #
        proj.plot(ax[i//figuresPerLine, i%figuresPerLine], margin=15, linewidth=5, add_labels=set(elems), line2dproperties={"color":"gray", "linestyle":"-"},
                  show_distances=comb, print_distances=True)

        #Uncomment to set a substring of the filename as a title
        #current_axes.set_title(file[-15:])

        #Hide the x- and y axis.
        current_axes.get_xaxis().set_visible(False)
        current_axes.get_yaxis().set_visible(False)

        #Uncomment the following lines to print the projection direction and the filename in the plot.
        current_axes.text(0.01,0.01,"Projection direction: ({},{},{})".format(round(direction[0],3), round(direction[1],3), round(direction[2],3)), transform=current_axes.transAxes)
        current_axes.text(0.01,0.97,"File: {}".format(file_), transform=current_axes.transAxes)
        #Uncomment the following line to change the backgroundcolor of the plot area.
        #current_axes.set_axis_bgcolor('black')

    
    #Hide additional subplots with no projection on them.
    for i in range(len(files),int(math.ceil(totalFigures/figuresPerLine))*figuresPerLine):
        ax[i//figuresPerLine, i%figuresPerLine].axis('off')

    # Reduce the space outside of the plots and between the subplots.
    plt.subplots_adjust(left=0.025, right=0.975, bottom=0.025, top=0.975, wspace=0.05, hspace=0.05)
    
    #Show the plot and clear it from the internal memory of matplotlib.
    plt.show()