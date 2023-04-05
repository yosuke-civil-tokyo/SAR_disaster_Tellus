import requests, json
import argparse
import os


"""
change the base path if access url of tellus API has changed
"""
BASE_PATH = "https://www.tellusxdp.com"

def parse_args():
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("TOKEN", type=str, help="your Tellus API TOKEN")
    parser.add_argument("data_id", type=str, help="data id obtained from search_sar.py")
    parser.add_argument("-p", "--Palsar_Type", type=str, default="L2.1", help="specify L2.1 or L1.1")
    parser.add_argument("-print", "--print_detail", type=str, default="True", help="print the data detail or not")
    args = parser.parse_args()

    return args

def make_config(args):
    config = {}
    config['TOKEN'] = args.TOKEN
    config['dataId'] = args.data_id
    config['print_detail'] = args.print_detail

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

    return config

def get_datasets_by_id(config, payload={}):
    url = '{}/api/traveler/v1/datasets/{}/'.format(BASE_PATH, config['datasetId'])
    headers = {
        'Authorization': 'Bearer ' + config['TOKEN'],
        'content-type': 'application/json'
    }
    r = requests.get(url, headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        raise ValueError('status error({}).'.format(r.status_code))
    
    return json.loads(r.content)


def get_dataset_data_by_id(config, payload={}):
    url = '{}/api/traveler/v1/datasets/{}/data/{}/'.format(BASE_PATH, config['datasetId'], config['dataId'])
    headers = {
        'Authorization': 'Bearer ' + config['TOKEN'],
        'content-type': 'application/json',
    }
    r = requests.get(url, headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        raise ValueError('status error({}).'.format(r.status_code))
    return json.loads(r.content)


def get_dataset_data_files(config, payload={}):
    url = '{}/api/traveler/v1/datasets/{}/data/{}/files/'.format(BASE_PATH, config['datasetId'], config['dataId'])
    headers = {
        'Authorization': 'Bearer ' + config['TOKEN'],
        'content-type': 'application/json',
    }
    r = requests.get(url, headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        raise ValueError('status error({}).'.format(r.status_code))
    return json.loads(r.content)


def dataset_download(config, fileId, payload={}):
    url = '{}/api/traveler/v1/datasets/{}/data/{}/files/{}/download-url/'.format(BASE_PATH, config['datasetId'], config['dataId'], fileId)
    headers = {
        'Authorization': 'Bearer ' + config['TOKEN'],
        'content-type': 'application/json'
    }
    r = requests.post(url, headers=headers, data=json.dumps(payload))
    if r.status_code != 200:
        raise ValueError('status error({}).'.format(r.status_code))
    return json.loads(r.content)


def main():
    args = parse_args()
    config = make_config(args)
    data_dir = 'data/raw_sar_L2/' + config['dataId']

    os.makedirs(data_dir, exist_ok=True)

    if config['print_detail'] == "True":
        ret = get_datasets_by_id(config)
        print(ret)
        ret = get_dataset_data_by_id(config)
        print(ret)
        ret = get_dataset_data_files(config)
        print(ret)

    ret = get_dataset_data_files(config)
    for file in ret.get('results'):
        fileId = file.get('id')
        fileName = file.get('name')
        download_bool = file.get('is_downloadable')

        print('Now {} downloading'.format(fileName))

        if download_bool:
            ret_download = dataset_download(config, fileId)
            url = ret_download.get('download_url')
            r = requests.get(url, stream=True)

            with open(data_dir + '/' + fileName, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
                        f.flush()

if __name__ == "__main__":
    main()