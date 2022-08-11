#converts WKT to EsriJson and vise versa

##def GetEsriType(esri):
##    keys = esri.keys()
##    
##    hasM = False
##    hasZ = False
##    
##    if 'hasM' in keys:
##        hasM = esri['hasM']
##    if 'hasZ' in keys:
##        hasZ = esri['hasZ']
##        
##    if hasZ and hasM:
##        return ' ZM'
##    if hasZ:
##        return ' Z'
##    if hasM:
##        return ' M'
##
##    return ''
##         

def EsriToWkt(esri):
    keys = esri.keys()

    #point
    if 'x' in keys:
        if not isinstance(esri['x'], (int, float)):
            return 'POINT EMPTY'
        if 'm' in keys and 'z' in keys:
            return 'POINT ({} {} {} {})'.format(esri['x'], esri['y'], esri['z'], esri['m'])
        if 'm' in keys:
            return 'POINT ({} {} {})'.format(esri['x'], esri['y'], esri['m']) #should all with M include Z? how else would only m and only z be destinguished
        if 'z' in keys:
            return 'POINT ({} {} {})'.format(esri['x'], esri['y'], esri['z'])
                                              
        return 'POINT({} {})'.format(esri['x'], esri['y'])

    #multipoint
    elif 'points' in keys:
        points = []
        for point in esri['points']:
            points.append(' '.join([str(p) for p in point]))

        if len(points) < 1:
            return 'MULTIPOINT EMPTY'
        
        return 'MULTIPOINT ({})'.format(','.join(points))

    #polygon/polyline                          
    elif 'rings' in keys or 'paths' in keys:

        if 'rings' in keys:
            geomType = 'POLYGON'
            esriRings = esri['rings']
        else:
            geomType = 'MULTILINESTRING'
            esriRings = esri['paths']
            
        rings = []
        for ring in esriRings:
            points = []
            for point in ring:
                points.append(' '.join([str(p) for p in point]))
                
            rings.append('({})'.format(','.join(points)))
            
        if len(rings) < 1:
            return '{} EMPTY'.format(geomType)

        return '{} ({})'.format(geomType, ','.join(rings))

    else:
        print("unexpected geometry type")

def GetWktType(num_coordinates):  #Determines if WKT has Z and M based on number of coordinates
    hasZ = num_coordinates > 2    #Check this, might be wrong!!!! should work for z anyway. 
    hasM = num_coordinates > 3

    return hasZ, hasM

def MultipointToEsri(multipoint):    #converts comma separated points with space separated coordinates to 2-d array
    points = multipoint.replace('(', '').replace(')', '').strip()
    points = points.split(',')
    
    esri_points = []
    
    for point in points:
        coordinates = point.strip().split(' ')
        try: 
            coordinates = [float(coordinate) for coordinate in coordinates]  #convert coordinates to floats
        except ValueError:
            print("Error converting WKT point coordinate to integer!")
            print("WKT: {}".format(multipoint))
            raise
        
        esri_points.append(coordinates)   #add each set of coordinates to esri object

    hasZ, hasM = GetWktType(len(coordinates))
    
    return esri_points, hasZ, hasM

def WktToEsri(wkt):
    if 'EMPTY' in wkt:              #catch empty geometry first
        if 'MULTIPOINT' in wkt:
            return {'x': None}
        if 'POINT' in wkt:
            return {'points': []}
        if 'LINESTRING' in wkt:
            return {'paths': []}
        if 'POLYGON' in wkt:
            return {'rings': []}
        
    geomType = wkt.split('(')[0]      #get first word from WKT
    wkt = wkt.replace(geomType, '')   #remove first word from WKT
    geomType = geomType.strip().lower()       #remove whitespace and caps

    esri = {}

    if geomType == 'point':
        coordinates = wkt.replace('(', '').replace(')', '').strip()
        coordinates = coordinates.split(' ')

        coord_names = ['x', 'y', 'z', 'm']

        for (index, coordinate) in enumerate(coordinates):
            try:
                esri[coord_names[index]] = float(coordinate)
            except ValueError:
                print("Error converting WKT point coordinate to integer!")
                print("WKT: {}".format(wkt))
                raise


    elif geomType == 'multipoint':
        esri['points'], esri['hasZ'], esri['hasM'] = MultipointToEsri(wkt)

    elif geomType == 'polygon' or geomType == 'multilinestring' or geomType == 'multipolygon':
        if geomType == 'multilinestring':
            rings_paths = 'paths'
        else:
            rings_paths = 'rings'
            
        rings = wkt.split('),')
    
        esri[rings_paths] = []
        
        for ring in rings:
            esri_rings, esri['hasZ'], esri['hasM'] = MultipointToEsri(ring)
            esri[rings_paths].append(esri_rings)

    elif geomType == 'linestring':
        esri['paths'] = []
        esri_paths, esri['hasZ'], esri['hasM'] = MultipointToEsri(wkt)   #same format as multipoint
        esri['paths'].append(esri_paths)    #needs to be double nested (esri has one format for line and multiline)
            
            

    #missing multipolygon in esri documentation, maybe just adds more rings to same list?

    

    return esri

    
##def WkbToEsri(wkb):
##    geojson = Geometry(wkb).geojson
##    geomType = geojson['type'].lower()
##    coordinates = geojson['coordinates']
##
##    if geomType == 'point':
##        dict_out = {}
##        coords = ['x', 'y', 'z', 'm']
##
##        i = 0;
##        for coordinate in coordinates: 
##            if isinstance(coordinate, (int, float)):
##                dict_out[coords[i]] = coordinate
##
##            i += 1
##
##        return dict_out
##
##    if geomType == 'multipoint':
##        for coordinate in coordinates:
##            pass
##        
##        
##            
##        
        
    
##    #separate type from values
##    split = wkt.split('(')
##    geomType = split.pop(0)
##    values = '({}'.format('('.join(split))
##
##    ext = geomType.split(' ')
##    try:
##        ext[1]
##        hasZ = 'z' in wkt
##        hasM = 'm' in wkt
##    else:
##        hasZ = False
##        hasM = False
##
##    if 'MULTIPOINT' in geomType:
##
##    if 'POINT' in geomType:
##        if hasZ and hasM:


            
    
##geometry ={
##        "hasM": False,
##        "hasZ": True,
##        "rings": [
##            [
##                [
##                    400256.578804272,
##                    4640459.73021187
##                ],
##                [
##                    400343.341193316,
##                    4640363.63900759
##                ],
##                [
##                    400200.17907481,
##                    4640372.7397159
##                ],
##                [
##                    400256.578804272,
##                    4640459.73021187
##                ]
##            ]
##        ]
##    }
##
##geometry2 = {
##  "hasM": True,
##  "hasZ": False,
##  "points": [
##    [
##      1,
##      3,
##      3
##    ],
##    [
##      5,
##      5,
##      5
##    ]]}
##
##geometry3 = {
##  "hasM": True,
##  "paths": [
##    [
##      [-97.06138,32.837,5],
##      [-97.06133,32.836,6],
##      [-97.06124,32.834,7],
##      [-97.06127,32.832,8]
##    ],
##    [
##      [-97.06326,32.759],
##      [-97.06298,32.755]
##    ]
##  ],
##  "spatialReference": {"wkid": 4326}
##}
##
##print WktToEsri('MULTIPOLYGON(((0 1,3 0,4 3,0 4,0 1)), ((3 4,6 3,5 5,3 4)), ((0 0,1 2,3 2,2 1,0 0)))')
###print WkbToEsri("01010000000000000000004AC00000000000000000")
##    
##        
##    
