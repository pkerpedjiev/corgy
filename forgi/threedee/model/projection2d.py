from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import (ascii, bytes, chr, dict, filter, hex, input,
                      int, map, next, oct, open, pow, range, round,
                      str, super, zip)
from future.builtins.disabled import (apply, cmp, coerce, execfile,
                             file, long, raw_input, reduce, reload,
                             unicode, xrange, StandardError)

import forgi.threedee.utilities.vector as ftuv
import collections as col
import numpy as np
import itertools as it
import networkx as nx
import warnings, math
import copy

### The following functions are from http://code.activestate.com/recipes/117225-convex-hull-and-diameter-of-2d-point-sets/
### Used under the PSF License
### convex hull (Graham scan by x-coordinate) and diameter of a set of points
### David Eppstein, UC Irvine, 7 Mar 2002
def orientation(p,q,r):
    '''Return positive if p-q-r are clockwise, neg if ccw, zero if colinear.'''
    return (q[1]-p[1])*(r[0]-p[0]) - (q[0]-p[0])*(r[1]-p[1])

def hulls(Points):
    '''Graham scan to find upper and lower convex hulls of a set of 2d points.'''
    U = []
    L = []
    Points.sort(key=lambda x:(x[0],x[1]))
    for p in Points:
        while len(U) > 1 and orientation(U[-2],U[-1],p) <= 0: U.pop()
        while len(L) > 1 and orientation(L[-2],L[-1],p) >= 0: L.pop()
        U.append(p)
        L.append(p)
    return U,L

def rotatingCalipers(Points):
    '''Given a list of 2d points, finds all ways of sandwiching the points
between two parallel lines that touch one point each, and yields the sequence
of pairs of points touched by each pair of lines.'''
    U,L = hulls(Points)
    i = 0
    j = len(L) - 1
    while i < len(U) - 1 or j > 0:
        yield U[i],L[j]
        
        # if all the way through one side of hull, advance the other side
        if i == len(U) - 1: j -= 1
        elif j == 0: i += 1
        
        # still points left on both lists, compare slopes of next hull edges
        # being careful to avoid divide-by-zero in slope calculation
        elif (U[i+1][1]-U[i][1])*(L[j][0]-L[j-1][0]) > \
                (L[j][1]-L[j-1][1])*(U[i+1][0]-U[i][0]):
            i += 1
        else: j -= 1

def diameter(Points):
    '''Given a list of 2d points, returns the pair that's farthest apart.'''
    diam,pair = max([((p[0]-q[0])**2 + (p[1]-q[1])**2, (p,q))
                     for p,q in rotatingCalipers(Points)])
    return pair


#### END David Eppstein



def rotate2D(vector, angle):
    """
    Rotate a vector in 2D space (i.e. a point) around the origin (0,0) by angle.

    :param vector: A sequence of length 2
    :param angle: the angle for rotation
    :returns: a tuple (x,y) of new coordinates.
    """
    angle=math.radians(angle)
    x=vector[0]*math.cos(angle)-vector[1]*math.sin(angle)
    y=vector[0]*math.sin(angle)+vector[1]*math.cos(angle)
    return np.array((x,y))

def bresenham(start,end):
    """
    Rasterize a line from start to end onto a grid with grid-width 1.

    :param start: A sequence of length 2, containing the x,y coordinates of the start of the line
    :param start: A sequence of length 2, containing the x,y coordinates of the end of the line
    :returns: A list of tuples (x,y), where x and y are integers.
    """
    #See e.g. http://stackoverflow.com/a/32252934/5069869
    # or https://de.wikipedia.org/wiki/Bresenham-Algorithmus#C-Implementierung
    if start==end:
      return [start]
    points=[]
    dx=end[0]-start[0]
    dy=end[1]-start[1]
    x,y=start
    if dx==0: sx=0
    else: sx=dx/abs(dx)
    if dy==0: sy=0
    else: sy=dy/abs(dy)
    dx=abs(dx)
    dy=abs(dy)
    if dx>dy:
      err=dx/2.
      while x!=end[0]:
        #print(x,y)
        points.append((x,y))
        err-=dy
        if err<0:
          y+=sy
          err+=dx
        x+=sx
    else:
      err=dy/2.
      while y!=end[1]:
        #print(x,y)
        points.append((x,y))
        err-=dx
        if err<0:
          x+=sx
          err+=dy
        y+=sy
    points.append((x,y))
    #if abs(dx)>1 or abs(dy)>1:
      #print(start, end, points)
    return points


class Projection2D(object):
    """A 2D Projection of a CoarseGrainRNA unto a 2D-plane"""
    def __init__(self, cg, proj_direction, rotation=0):
        """
        @param cg:  an CoarseGrainRNA object with 3D coordinates for every element
                    .. note:: The projection is generated from this cg, but it is not associated with it after construction.
                              Thus future changes of the cg are not reflected in the projection.
        @param proj_direction: a vector (in 3D space) in the direction of projection. 
                               The length of this vector is not used.
        @param rotate: Degrees. Rotate the projection by this amount.
        
        """        
        #: The projected coordinates of all stems
        self._coords=dict()

        self._cross_points=None
        self._proj_graph=None

        #Calculate orthonormal basis of projection plane.
        proj_direction=np.array(proj_direction, dtype=np.float)
        _, unit_vec1, unit_vec2=ftuv.create_orthonormal_basis(proj_direction)
        self._unit_vec1=unit_vec1
        self._unit_vec2=unit_vec2
        self._proj_direction=proj_direction
        self._project(cg)
        

        #Rotate and translate projection into a standard orientation
        points=list(self.points)
        v1,v2=diameter(points)
        #: The longest distance between any two points of the projection.
        self.longest_axis=ftuv.vec_distance(v1,v2)

        v1=np.array(v1)
        v2=np.array(v2)
        for key,edge in self._coords.items():
            self._coords[key]=(edge[0]-v1/2-v2/2, edge[1]-v1/2-v2/2)
        rot=math.atan2(*(v2-v1))
        rot=math.degrees(rot)
        self.rotate(rot)
        xmean=np.mean([ x[0] for p in self._coords.values() for x in p])
        ymean=np.mean([ x[1] for p in self._coords.values() for x in p])
        for key,edge in self._coords.items():
            self._coords[key]=(edge[0]-(xmean,ymean), edge[1]-(xmean,ymean))

        #From this, further rotate if requested by the user.
        if rotation!=0:
            self.rotate(rotation)

    ### Functions modifying the projection in place ###
    def rotate(self, angle):
        """
        Rotate the projection in place around the origin (0,0)

        :param angle: Rotation angle in degrees.
        """
        self._proj_graph=None
        for key,edge in self._coords.items():
            self._coords[key]=(rotate2D(edge[0], angle), rotate2D(edge[1], angle))

    def condense_points(self, cutoff=1):
        """
        Condenses several projection points that are within a range of less than cutoff into
        one point. This function modifies this Projection2D object.
  
        ..note: The result depends on the ordering of the dictionary holding the nodes and might thus be pseudorandomly

        :param cutoff: Two point with a distance smaller than cuttoff are contracted. A value below 20 is reasonable.
        """
        if cutoff<=0: return
        while self._condense_one(cutoff):
            pass
        self.proj_graph.remove_edges_from(self.proj_graph.selfloop_edges())

    def condense(self, cutoff):
        """
        Condenses points that are within the cutoff of another point or edge (=line segment) into a new point.
        This function modifies this Projection2D object.
        
        The contraction of two points works like documented in condense_points(self, cutoff).
        If a node is close to a line segment, a new point is generated between this node and the line segment. 
        Then the original line and the original node are deleted and all connections attached to the new point.
  
        ..note: The result depends on the ordering of the dictionary holding the nodes and might thus be pseudorandomly

        
        :param cutoff: Two point with a distance smaller than cuttoff are contracted. A value below 20 is reasonable.
        """
        if cutoff<=0: return
        self.condense_points(cutoff)
        while self._condense_pointWithLine_step(cutoff):
            self.condense_points(cutoff)
    ### Properties ###
    @property
    def proj_direction(self):
        """A vector describing the direction of the projection"""
        return self._proj_direction

    @property
    def crossingPoints(self):
        """
        All points, where 2 segments intersect
        
        A list of triples (key1, key2, coordinate), where coordinate is a 2D vector.
        """
        if self._cross_points is None:
            self._cross_points=col.defaultdict(list)
            for key1, key2 in it.combinations(self._coords, 2):
              for cr in ftuv.seg_intersect(self._coords[key1], self._coords[key2]):
                self._cross_points[key1].append((cr, key2))
                self._cross_points[key2].append((cr, key1))
        return self._cross_points
    @property
    def proj_graph(self):
        """A graph describing the projected RNA.

        This graph is stored as a networkx graph object.
        """
        if self._proj_graph is None:
            self._build_proj_graph()
        return self._proj_graph
    @property
    def points(self):
        """
        All points that are at the ends of coarse-grain elements. 
        This does not include points where coarse grain elements intersect in the projection.

        :returns: A generator yielding all points.
        """
        return ( p for x in self._coords.values() for p in x )

    ### Function returning descriptors of the projection, mostly independent on the resolution ###
    def get_largest_axis(self):
        """
        Return the largest length between any two points.
        """
        return self.longest_axis

    ### Function returning descriptors of the projection, dependent on the resolution ###    
    def get_bounding_box(self, margin=0.):
        """
        Returns the coordinates for a box that contains all points of the 2D projection.

        :param margin: increase the bounding box in every direction by this margin.
        :returns: left, right, bottom, top
        """
        points=[ p for x in self._coords.values() for p in x ]
        #print("P", points)
        left=min(x[0] for x in points)-margin
        right=max(x[0] for x in points)+margin
        bottom=min(x[1] for x in points)-margin
        top=max(x[1] for x in points)+margin
        #print "BB",  left, right, bottom, top
        return left, right, bottom, top

    def get_bounding_square(self, margin=0.):
        """
        Returns the coordinates for a square that contains all points of the 2D projection.

        :param margin: increase the bounding box in every direction by this margin.
        :returns: left, right, bottom, top
        """
        bb=self.get_bounding_box()
        length=max([bb[1]-bb[0],bb[3]-bb[2]])/2+margin
        x=(bb[0]+bb[1])/2
        y=(bb[2]+bb[3])/2
        return x-length, x+length, y-length, y+length

    def get_branchpoint_count(self, degree=None):
        """
        Returns the number of branchpoint.

        Note: This measure is sensitive to the resolution of a projection.
              In an AFM image, one might not see all branching points.
    
        :param degree: If degree is None, count all points with degree>=3
                       Else: only count (branch)points of the given degree
        """
        if degree is None:
            return len([x for x in nx.degree(self.proj_graph).values() if x>=3])
        else:
            return len([x for x in nx.degree(self.proj_graph).values() if x==degree])

    def get_cyclebasis_len(self):
        """
        Returns the number of cycles of length>1 in the cycle basis.
        """
        return len([x for x in nx.cycle_basis(self.proj_graph) if len(x)>1])

    def get_total_length(self):
        """
        Returns the sum of the lengths of all edges in the projection graph.      

        Note: This measure is sensitive to the resolution of a projection.
              In an AFM image, one might not see all cycles.
        """
        l=0
        for edge in self.proj_graph.edges_iter():
            l+=ftuv.vec_distance(edge[0], edge[1])
        return l

    def get_longest_arm_length(self):
        """
        Get the length of the longest arm.

        An arm is a simple path from a node of degree!=2 to a node of degree 1, if all the other 
        nodes on the path have degree 2.

        Note: This measure is sensitive to the resolution of a projection 
              the same way the length of a coastline is sensitive to the resoltuion.
        returns: The length and a tuple of points (leaf_node, corresponding_branch_point)
        """
        lengths={}
        target={}
        for leaf, degree in nx.degree(self.proj_graph).items():        
            if degree!=1: continue              
            lengths[leaf]=0          
            previous=None
            current=leaf
            while True:
              next=[ x for x in self.proj_graph[current].keys() if x != previous ]
              assert len(next)==1
              next=next[0]
              lengths[leaf]+=ftuv.vec_distance(current, next)
              if self.proj_graph.degree(next)!=2:
                  break
              previous=current
              current=next
            target[leaf]=next
        best_leaf=max(lengths, key=lambda x: lengths[x])
        return lengths[best_leaf], (best_leaf, target[best_leaf])

    def get_leaf_leaf_distances(self):
        """
        Get a list of distances between any pair of leaf nodes.
        The distances are measured in direct line, not along the path

        returns: a list of floats (lengths in Angstrom)
        """
        lengths=[]
        leaves=[ leaf for leaf in self.proj_graph.nodes() if self.proj_graph.degree(leaf)==1]
        for leaf1, leaf2 in it.combinations(leaves, 2):
            lengths.append(ftuv.vec_distance(leaf1, leaf2))
        lengths.sort(reverse=True)
        return lengths
    def get_some_leaf_leaf_distances(self):
        """
        Get a list of distances between some pairs of leaf nodes.
        The distances are measured in direct line, not along the path

        returns: a list of floats (lengths in Angstrom)
        """
        lengths=[]
        leaves=[ leaf for leaf in self.proj_graph.nodes() if self.proj_graph.degree(leaf)==1]
        for leaf1, leaf2 in it.combinations(leaves, 2):
            lengths.append((ftuv.vec_distance(leaf1, leaf2), leaf1, leaf2))
        lengths.sort(reverse=True,key=lambda x: x[0])
        newlengths=[]
        visited=set()
        for l, leaf1, leaf2 in lengths:
            if leaf1 in visited or leaf2 in visited: continue
            newlengths.append(l)
            visited.add(leaf1)
            visited.add(leaf2)
        return newlengths
    def get_maximal_path_length(self):
        """
        Get the maximal path length from all simple paths that traverses the projection graph from 
        one leave node to another.

        Note: This measure is sensitive to the resolution of a projection 
              the same way the length of a coastline is sensitive to the resoltuion.
        """
        maxl=0
        for i, node1 in enumerate(self.proj_graph.nodes_iter()):
            for j, node2 in enumerate(self.proj_graph.nodes_iter()):
                if j<=i: continue
                all_paths=nx.all_simple_paths(self.proj_graph, node1, node2)
                for path in all_paths:
                    l=self._get_path_length(path)
                    if l>maxl: maxl=l
        return maxl

    ### Functions for graphical representations of the projection ###
    def rasterize(self, resolution=50, bounding_square=None, warn=True):
        """
        Rasterize the projection to a square image of the given resolution.
        Uses the Bresenham algorithm for line rasterization.

        :param resolution: The number of pixels in each direction.
        :param bounding_square: Rasterize onto the given square. 
                                If None, automatically get a bounding_square that shows the whole projection
        :param warn:  If True, raise a warning if parts of the projection are not inside the given bounding square.

        :returns: A r(esolution x resulution) numpy 2D array. The values are floats from 0.0 (black) to 1.0 (white).
                  This array can be directly plotted using matplotlib: pyplot.imshow(array, cmap='gray', interpolation='none')
        """
        if bounding_square is None:
            bounding_square=self.get_bounding_square()
        box=bounding_square
        steplength=(box[1]-box[0])/resolution
        image=np.zeros([resolution+1,resolution+1], dtype=np.float32)
        for start, end in self.proj_graph.edges_iter():             
            label=self.proj_graph.edge[start][end]["label"]           
            start=(int((start[0]-box[0])/steplength), int((start[1]-box[2])/steplength))
            end=(int((end[0]-box[0])/steplength), int((end[1]-box[2])/steplength))        
            points=bresenham(start, end)
            if label.startswith("s"):
                weight=1
                #print("W", label, start, end, "Points", points, weight)
            else:
                weight=0.3
            for p in points:
                try:
                    image[p[0],p[1]]=min(1,image[p[0],p[1]]+weight)
                except IndexError:
                    if warn: warnings.warn("WARNING during rasterization of the 2D Projection: Parts of the projection are cropped off.")
        return np.rot90(image)

    def plot(self, ax=None, show=False, margin=5, 
                   linewidth=None, add_labels=False,
                   line2dproperties={}, xshift=0, yshift=0,
                   show_distances=[], print_distances=False):
        """
        Plots the 2D projection

        :param ax: The axes to draw to. You can get it by calling `fig, ax=matplotlib.pyplot.subplots()`
        :param show: If true, the matplotlib.pyplot.show() will be called at the end of this function.
        :param margin: A numeric value. The margin around the plotted projection inside the (sub-)plot.
        :param linewidth: The width of the lines projection.
        :param add_labels: Display the name of the corresponding coarse grain element in the middle of each segment in the projection.
                           Either a bool or a set of labels to display.
        :param line2dproperties: A dictionary. Will be passed as **kwargs to the constructor of `matplotlib.lines.Line2D`
                                 See http://matplotlib.org/api/lines_api.html#matplotlib.lines.Line2D
        :param xshift, yshift: Shift the projection by the given amount inside the canvas.
        :param show_distances: A list of tuples of strings, e.g. [("h1","h8"),("h2","m15")]. 
                               Show the distances between these elements in the plot
        :param print_distances: Bool. Print all distances from show_distances at the side of the plot
                                instead of directly next to the distance
        """
        # In case of ssh without -X option, a TypeError might be raised during the import of pyplot.
        # This probably depends on the version of some library.
        # This is also the reason why we import matplotlib only in the plot function.
        text=[]
        try:
            if ax is None or show:
                import matplotlib.pyplot as plt
            import matplotlib.lines as lines
            import matplotlib.transforms as mtransforms
            import matplotlib.text as mtext
            import matplotlib.font_manager as font_manager
        except TypeError as e:
          warnings.warn("Cannot plot projection. Maybe you could not load Gtk (no X11 server available)? During the import of matplotlib the following Error occured:\n {}: {}".format(type(e).__name__, e))
          return
        except ImportError as e:
          warnings.warn("Cannot import matplotlib. Do you have matplotlib installed? The following error occured:\n {}: {}".format(type(e).__name__, e))
          return
        class MyLine(lines.Line2D):
            """
            Copied and modified from http://matplotlib.org/examples/api/line_with_text.html,
            which is part of matplotlib 1.5.0 (Copyright (c) 2012-2013 Matplotlib Development Team; All Rights Reserved).
            Used under the matplotlib license: http://matplotlib.org/users/license.html
            """
            def __init__(self, *args, **kwargs):
                # we'll update the position when the line data is set
                fm=font_manager.FontProperties(size="large", weight="demi")
                self.text = mtext.Text(0, 0, '', fontproperties=fm)
                lines.Line2D.__init__(self, *args, **kwargs)

                # we can't access the label attr until *after* the line is
                # inited
                self.text.set_text(self.get_label())

            def set_figure(self, figure):
                self.text.set_figure(figure)
                lines.Line2D.set_figure(self, figure)

            def set_axes(self, axes):
                self.text.set_axes(axes)
                lines.Line2D.set_axes(self, axes)

            def set_transform(self, transform):
                # 2 pixel offset
                texttrans = transform + mtransforms.Affine2D().translate(2, 2)
                self.text.set_transform(texttrans)
                lines.Line2D.set_transform(self, transform)

            def set_data(self, x, y):
                if len(x):
                    self.text.set_position(((x[0]+x[-1])/2, (y[0]+y[-1])/2))
                lines.Line2D.set_data(self, x, y)

            def draw(self, renderer):
                # draw my label at the end of the line with 2 pixel offset
                lines.Line2D.draw(self, renderer)
                self.text.draw(renderer)

        if "linewidth" in line2dproperties and linewidth is not None:
            warnings.warn("Got multiple values for 'linewidth' (also present in line2dproperties)")
        if linewidth is not None:
            line2dproperties["linewidth"]=linewidth
        if "solid_capstyle" not in line2dproperties:
            line2dproperties["solid_capstyle"]="round"

        if ax is None:
            try:
                fig, ax = plt.subplots(1, 1)            
            except Exception as e:
                warnings.warn("Cannot create Axes  or Figure. You probably have no graphical display available. The Error was:\n {}: {}".format(type(e).__name__, e))
                return      
        lprop=copy.copy(line2dproperties)
        for s,e in self.proj_graph.edges_iter():
            if "color" not in line2dproperties:
                label=self.proj_graph.edge[s][e]["label"]
                if label.startswith("s"):
                  lprop["color"]="green"
                elif label.startswith("i"):
                  lprop["color"]="gold"
                elif label.startswith("h"):
                  lprop["color"]="blue"
                elif label.startswith("m"):
                  lprop["color"]="red"
                elif label.startswith("f") or label.startswith("t"):
                  lprop["color"]="blue"
                else:
                  lprop["color"]="black"
            if add_labels!=False and (add_labels==True or self.proj_graph.edge[s][e]["label"] in add_labels):
                lprop["label"]=self.proj_graph.edge[s][e]["label"]
                #Every label only once
                if isinstance(add_labels, set):
                    add_labels.remove(lprop["label"])
            else:
                lprop["label"]=""
            #line=lines.Line2D([s[0], e[0]],[s[1],e[1]], **lprop) 
            line=MyLine([s[0]+xshift, e[0]+xshift],[s[1]+yshift,e[1]+yshift], **lprop) 
            ax.add_line(line)

        for s,e in show_distances:
            st=(self._coords[s][0]+self._coords[s][1])/2
            en=(self._coords[e][0]+self._coords[e][1])/2
            d=ftuv.vec_distance(st,en)
            if print_distances:
                line=MyLine([st[0]+xshift, en[0]+xshift],[st[1]+yshift,en[1]+yshift], color="orange",linestyle="--")
                text.append("{:3} - {:3}: {:5.2f}".format(s,e,d))
            else:
                line=MyLine([st[0]+xshift, en[0]+xshift],[st[1]+yshift,en[1]+yshift], label=str(round(d,1)), color="orange",linestyle="--")
            ax.add_line(line)

        #line.text.set_zorder(1000000)
        ax.axis(self.get_bounding_square(margin))
        fm=font_manager.FontProperties(["monospace"], size="x-small")
        ax.text(0.01,0.05,"\n".join(["Distances:"]+text), transform=ax.transAxes, fontproperties=fm)
        out = ax.plot()
        if show:
            plt.show()
            return
        return out

    ### Private functions ###
    def _build_proj_graph(self):
        """
        Generate a graph from the 2D projection. 
  
        This is implemented as a networkx.Graph with the coordinates as nodes.
        """
        proj_graph=nx.Graph()
        for key, element in self._coords.items():
            crs=self.crossingPoints
            sortedCrs=ftuv.sortAlongLine(element[0], element[1], [x[0] for x in crs[key]])     
            oldpoint=None
            for point in sortedCrs:
                point=(point[0], point[1]) #Tuple, to be hashable
                if oldpoint is not None:
                    proj_graph.add_edge(oldpoint, point, attr_dict={"label": key})                 
                oldpoint=point
        self._proj_graph=proj_graph
        self.condense_points(0.00000000001) #To avoid floating point problems

    def _project(self, cg):
        """
        Calculates the 2D coordinates of all coarse grained elements by vector rejection.
        Stores them inside self._coords
        """
        self._coords=dict()
        #Project all coordinates to this plane
        for key, val in cg.coords.items():
            start=np.array([np.dot(self._unit_vec1,val[0]), np.dot(self._unit_vec2,val[0])])
            end=np.array([np.dot(self._unit_vec1,val[1]), np.dot(self._unit_vec2,val[1])])
            self._coords[key]=(start, end)

    def _condense_one(self, cutoff):
        """
        Condenses two adjacent projection points into one.
        :returns: True if a condensation was done, False if no condenstaion is possible.
        """        
        for i,node1 in enumerate(self.proj_graph.nodes_iter()):
            for j, node2 in enumerate(self.proj_graph.nodes_iter()):
                if j<=i: continue                
                if ftuv.vec_distance(node1, node2)<cutoff:
                    newnode=ftuv.middlepoint(node1, node2)
                    #self.proj_graph.add_node(newnode)
                    for neighbor in self.proj_graph.edge[node1].keys():
                        self.proj_graph.add_edge(newnode, neighbor, attr_dict=self.proj_graph.edge[node1][neighbor])
                    for neighbor in self.proj_graph.edge[node2].keys():
                        self.proj_graph.add_edge(newnode, neighbor, attr_dict=self.proj_graph.edge[node2][neighbor])
                    if newnode!=node1: #Equality can happen because of floating point inaccuracy
                        self.proj_graph.remove_node(node1)
                    if newnode!=node2:
                        self.proj_graph.remove_node(node2)
                    return True
        return False

    def _condense_pointWithLine_step(self, cutoff):
        """
        Used by self.condense(cutoff) as a single condensation step of a point with a line segment.
        """
        for i,source in enumerate(self.proj_graph.nodes_iter()):
            for j,target in enumerate(self.proj_graph.nodes_iter()):
                if j>i and self.proj_graph.has_edge(source,target):
                    for k, node in enumerate(self.proj_graph.nodes_iter()):
                        if k==i or k==j:
                            continue
                        nearest=ftuv.closest_point_on_seg( source, target, node)
                        nearest=tuple(nearest)
                        if nearest==source or nearest==target: 
                            continue   
                        if (ftuv.vec_distance(nearest, node)<cutoff):
                            newnode=ftuv.middlepoint(node, tuple(nearest))
                            attr_dict=self.proj_graph.edge[source][target]
                            self.proj_graph.remove_edge(source, target)
                            if source!=newnode:
                                self.proj_graph.add_edge(source, newnode, attr_dict=attr_dict)
                            if target!=newnode:
                                self.proj_graph.add_edge(target, newnode, attr_dict=attr_dict)             
                            if newnode!=node: #Equality can happen because of floating point inaccuracy
                                for neighbor in self.proj_graph.edge[node].keys():
                                    attr_dict=self.proj_graph.edge[node][neighbor]
                                    self.proj_graph.add_edge(newnode, neighbor, attr_dict=attr_dict)
                                self.proj_graph.remove_node(node)
                            return True
        return False

    def _get_path_length(self, path):
        """
        :param path: a list of nodes
        """
        l=0
        for i in range(len(path)-1):
            l+=ftuv.vec_distance(path[i], path[i+1])
        return l














        
