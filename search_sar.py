import requests, json
import argparse

def parse_args():
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("TOKEN", type=str, help="your Tellus API TOKEN")
    parser.add_argument("--Palsar_Type", type=str, default="L2.1", help="Specify L2.1 or L1.1")
    parser.add_argument("--start_datetime", type=str, default="2017-04-21", help="search start datetime")
    parser.add_argument("--end_datetime", type=str, default="2021-12-30", help="search end datetime")
    parser.add_argument("--lat", type=float, default=139.692101, help="search center latitude")
    parser.add_argument("--lon", type=float, default=35.689634, help="search center longitude") 
    args = parser.parse_args()

    return args


def make_config(args):
    config = {}
    config['TOKEN'] = args.Token

    if args.Palsar_Type == "L2.1":
        # Palsar-2, L2.1
        config['datasetId'] = 'b0e16dea-6544-4422-926f-ad3ec9a3fcbd'
    elif args.Palsar_Type == "L1.1":
        # Palsar-2, L1.1
        config['datasetId'] = '1a41a4b1-4594-431f-95fb-82f9bdc35d6b'
    else:
        # Palsar-2, L2.1
        config['datasetId'] = 'b0e16dea-6544-4422-926f-ad3ec9a3fcbd'
        print("Specify L2.1 or L1.1, for now using L2.1")
    
    config['query']={
        'start_datetime': {'gte': args.start_datetime},
        'end_datetime': {'lte': args.end_datetime}
    }
    config['sortby'] = [
                 {'field': 'properties.end_datetime', 'direction':'desc'}
             ]
    
    config['intersects'] = make_inter(args.lat, args.lon)

    return config


def make_inter(lat, lon):
    lat_plus = lat + 0.01
    lon_plus = lon + 0.01

    intersects = {
        'type': 'Polygon', 'coordinates': [
            [
                [lat, lon],
                [lat_plus, lon],
                [lat_plus, lon_plus],
                [lat, lon_plus],
                [lat, lon]
            ]
        ]
    }
    return intersects


def search_palsar2_l11(config, paginate=None, next_url=''):
    if len(next_url) > 0:
        url = next_url
    else:
        url = 'https://www.tellusxdp.com/api/traveler/v1/datasets/{}/data-search/'.format(config['dataset_id'])
    headers = {
        "Authorization": "Bearer " + config['TOKEN'],
        'Content-Type': 'application/json'
    }

    payloads = {}
    if config['intersects'] is not None:
        payloads['intersects'] = config['intersects']
    if config['query'] is not None:
        payloads['query'] = config['query']
    if isinstance(config['sortby'], list):
        payloads['sortby'] = config['sortby']
    if paginate is not None:
        payloads['paginate'] = paginate
    r = requests.post(url, headers=headers, data=json.dumps(payloads))

    if not r.status_code == requests.codes.ok:
        r.raise_for_status()
    return r.json()


def main():
    args = parse_args()
    config = make_config(args)
    lat = config.lat
    lon = config.lon

    ret = search_palsar2_l11(config)

    for i in ret['features']:
        geo = i['geometry']['coordinates']
        pro = i['properties']
        lon_min = min([geo[0][i][0] for i in range(4)])
        lat_min = min([geo[0][i][1] for i in range(4)])
        lon_max = max([geo[0][i][0] for i in range(4)])
        lat_max = max([geo[0][i][1] for i in range(4)])
        if lat > lat_min and lat < lat_max and lon > lon_min and lon < lon_max:
            print(i['id'], pro['palsar2:beam'], pro['sat:relative_orbit'], pro['tellus:sat_frame'], pro['start_datetime'])


if __name__ == "__main__":
    main()