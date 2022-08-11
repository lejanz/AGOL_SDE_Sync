def CleanAttributes(dict_in):
    #turns all keys to lower case, removes unwanted attributes
    dict_in = {k.lower(): v for k, v in dict_in.items()}

    remove_keys = ['sde_state_id', 'objectid']
    dict_in = {k: v for k, v in dict_in.items() if k not in remove_keys}

    return dict_in

def CleanDelta(dict_in, srid):
    #cleans attributes and adds srid to geometry
    dict_in['attributes'] = CleanAttributes(dict_in['attributes'])
    dict_in['geometry']['spatialReference'] = {'wkid': srid}

    return dict_in

def CleanJson(deltas, srid):
    for (index, add) in enumerate(deltas['adds']):
        deltas['adds'][index] = CleanDelta(add, srid)

    for (index, update) in enumerate(deltas['updates']):
        deltas['updates'][index] = CleanDelta(update, srid)

    return deltas