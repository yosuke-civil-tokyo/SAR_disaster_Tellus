import os
import cv2
import pandas as pd
import jismesh.utils as ju
import argparse

Image.MAX_IMAGE_PIXELS = 400000000

from utils import *
from detect_damage import *


def parse_args():
    """Parse command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-ulx', type=float, default=139.775)
    parser.add_argument('-uly', type=float, default=35.683333)
    parser.add_argument('-lrx', type=float, default=139.8375)
    parser.add_argument('-lry', type=float, default=35.641667)
    parser.add_argument('-place', type=str, default='toyosu')
    parser.add_argument('-overlay', type=str, default=None)
    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    region = [args.ulx, args.uly, args.lrx, args.lry]
    place = args.place

    sar_data_dir = './'
    raw_img_dir = sar_data_dir + 'data/raw_sar_L2/'
    clip_raw_dir = sar_data_dir + 'data/clipped/raw/'
    clip_detect_dir = sar_data_dir + 'data/clipped/detect/'
    raw_img_list = os.listdir(raw_img_dir)
    output_dir = sar_data_dir + 'data/output1/'
    mask_dir = sar_data_dir + 'data/mask1/'

    meshlist = obtain_mesh(region)
    df_mesh = pd.DataFrame({'mesh': meshlist})
    df_mesh['ulx'], df_mesh['uly'] = ju.to_meshpoint(df_mesh.mesh, 1, 0)[::-1]
    df_mesh['lrx'], df_mesh['lry'] = ju.to_meshpoint(df_mesh.mesh, 0, 1)[::-1]

    road_mask_img = cv2.imread(mask_dir + 'mask_f.tif')
    h, w, c = road_mask_img.shape
    h = h/5
    w = w/5
    if place=='toyosu':
        road_mask_img = cv2.imread(mask_dir + 'mask_qua_f.tif')
        h, w, c = road_mask_img.shape
        h = h/5
        w = w/5

    meshsize, clipped_img_path, time_table = clip_sarimg(df_mesh=df_mesh, resize_h=h, resize_w=w, place=place)
    print(meshsize)
    with open(sar_data_dir+'data/output/time.txt', "w") as f:
        f.write(time_table[0])
        f.write(time_table[1])

    damaged_area_cord, damaged_area_cord2 = detect(df_mesh=df_mesh, sar_data_dir=sar_data_dir)
    df_damaged = pd.DataFrame(np.concatenate([damaged_area_cord,damaged_area_cord2], 0))
    df_damaged.to_csv(mask_dir+'damaged_cord.csv')

    road_mask_table = pd.read_csv(mask_dir+'pix_to_edge.csv')
    edge_data = pd.read_csv(output_dir+'edge_for_sim.csv')
    edge_data['damage_pix'] = 0

    ulx = min(df_mesh['ulx'])
    uly = max(df_mesh['uly'])
    lrx = max(df_mesh['lrx'])
    lry = min(df_mesh['lry'])
    img_cord = [ulx, uly, lrx, lry]

    edge_data_with_water = distribute_to_road(road_mask_table.values, damaged_area_cord, edge_data, img_cord, h, w, meshsize)
    edge_data_with_water['damage'] = (edge_data_with_water['damage_pix'].values / (edge_data_with_water['Lanes'].values * 3.5 * edge_data_with_water['length'].values / 2)).clip(0, 1)
    edge_data_with_damage = distribute_to_road(road_mask_table.values, damaged_area_cord2, edge_data_with_water, img_cord, h, w, meshsize)
    edge_data_with_damage['damage'] = (edge_data_with_damage['damage_pix'].values / (edge_data_with_damage['Lanes'].values*3.5 * edge_data_with_damage['length'].values/2)).clip(0, 1)

    print('Num of flooded Edges : {}'.format(sum(edge_data_with_water['damage'].values != 0)))
    print('Num of heavily flooded Edges : {}'.format(sum(edge_data_with_water['damage'].values >= 0.5)))
    print('Num of damaged Edges : {}'.format(sum(edge_data_with_damage['damage'].values != 0)))
    print('Num of heavily damaged Edges : {}'.format(sum(edge_data_with_damage['damage'].values >= 0.5)))
    edge_data_with_water.drop('damage_pix', axis=1).to_csv(output_dir + 'edge_for_sim_withflood.csv', index=False)
    edge_data_with_damage.drop('damage_pix', axis=1).to_csv(output_dir+'edge_for_sim_withdamage.csv', index=False)

    # depict the extracted disaster area on RGB image
    if args.overlay:
        clipped_img_path = args.overlay + '{}_MULPAN.tif'.format(place)
        make_img(damaged_area_cord, damaged_area_cord2, img_cord, ori_path=clipped_img_path, tgt_path=sar_data_dir+'data/output/')

    return None

if __name__ == "__main__":
    main()
