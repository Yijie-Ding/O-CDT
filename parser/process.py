from __future__ import print_function

import argparse
import json
import os

import numpy as np
import yaml
from joblib import Parallel, delayed

from feature_parser import FeatureListParser
from onshape_client import OnshapeClient

SUPPORTED_FEATURES = {'newSketch', 'extrude', 'revolve'}
TEST_LINKS = {
    '00000257': 'https://cad.onshape.com/documents/845fb06d7f2f4802a806a600/w/7c68e73133ee4184b4fec95c/e/OMwP46D057q4VnEse6zqPF6G',
}

client = OnshapeClient(logging=False)


def parse_link(link):
    parts = link.split('/')
    return parts[-5], parts[-3], parts[-1]


def process_one(data_id, link, save_dir):
    skipped = (data_id, 0, [], set())
    save_path = os.path.join(save_dir, '{}.json'.format(data_id))
    if os.path.exists(save_path):
        print('[{}] already processed'.format(data_id))
        return skipped

    try:
        parser = FeatureListParser(client, parse_link(link), data_id)
    except Exception as e:
        print('[{}] cannot fetch features: {}'.format(data_id, e))
        return skipped

    unsupported = set(item['message']['featureType'] for item in parser.features) - SUPPORTED_FEATURES
    if unsupported:
        print('[{}] unsupported features: {}'.format(data_id, sorted(unsupported)))
        return data_id, 0, [], unsupported

    try:
        result = parser.parse()
    except Exception as e:
        print('[{}] parsing failed: {}'.format(data_id, e))
        return skipped
    if len(result['sequence']) < 2:
        return skipped

    with open(save_path, 'w') as f:
        json.dump(result, f, indent=1)
    return data_id, len(result['sequence']), parser.detected_bsplines, set()


def save_json(data, path):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def process_batch(link_path, save_dir, n_jobs):
    with open(link_path) as f:
        links = yaml.safe_load(f)
    results = Parallel(n_jobs=n_jobs, verbose=2)(
        delayed(process_one)(data_id, link, save_dir) for data_id, link in links.items())

    counts = np.array([count for _, count, _, _ in results])
    print('valid: {}\ntotal: {}\ndistribution:'.format(np.sum(counts > 0), len(links)))
    for length in np.unique(counts):
        print(length, np.sum(counts == length))

    inventory = {}
    for data_id, _, _, unsupported in results:
        for feature_type in unsupported:
            inventory.setdefault(feature_type, []).append(data_id)
    save_json(inventory, os.path.join(save_dir, 'unsupported_features.json'))
    save_json([spline for _, _, splines, _ in results for spline in splines],
              os.path.join(save_dir, 'detected_bspline.json'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true', help='parse the built-in test examples')
    parser.add_argument('--link_data_folder', type=str, help='folder of ABC Onshape link files (*.yml)')
    parser.add_argument('--n_jobs', type=int, default=20)
    args = parser.parse_args()

    if args.test:
        if not os.path.exists('examples'):
            os.makedirs('examples')
        for data_id, link in TEST_LINKS.items():
            process_one(data_id, link, 'examples')
        return

    link_dir = os.path.normpath(args.link_data_folder)
    for name in sorted(os.listdir(link_dir)):
        link_path = os.path.join(link_dir, name)
        if not os.path.isfile(link_path):
            continue
        batch_id = os.path.splitext(name)[0].split('_')[-1]
        save_dir = os.path.join(os.path.dirname(link_dir), 'processed', batch_id)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        print('processing batch {}'.format(batch_id))
        process_batch(link_path, save_dir, args.n_jobs)


if __name__ == '__main__':
    main()
