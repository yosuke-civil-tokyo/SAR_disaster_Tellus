"""
functions for processing file, image and  mesh
"""
import os
import numpy as np
import pandas as pd
import heapq
import subprocess
import cv2
from PIL import Image, ImageDraw
from osgeo import gdal, gdalconst, gdal_array
import datetime
import jismesh.utils as ju
from scipy.ndimage.filters import uniform_filter
from scipy.ndimage.measurements import variance


# clip the SAR image with the extent of mesh specified by the mesh-list
def clip_sarimg(df_mesh, resize_h, resize_w, place):
    sar_data_dir = './'
    raw_img_dir = sar_data_dir + 'data/raw_sar_L2/'
    clip_raw_dir = sar_data_dir + 'data/clipped/raw/'
    raw_img_list = os.listdir(raw_img_dir)

    time_disaster = datetime.datetime(year=2019, month=10, day=12, hour=00)
    ulx = min(df_mesh['ulx'])
    uly = max(df_mesh['uly'])
    lrx = max(df_mesh['lrx'])
    lry = min(df_mesh['lry'])
    print('area of interest')
    print(ulx, uly, lrx, lry)

    table = []
    time_table = []
    for raw_img_folder in raw_img_list:
        raw_img_folder_dir = os.path.join(raw_img_dir, raw_img_folder)
        summary_dict = pd.read_csv(os.path.join(raw_img_folder_dir, 'summary.txt'), delimiter='=', header=None, index_col=0).squeeze('columns').to_dict()
        time_data = summary_dict.get('Img_SceneCenterDateTime')
        time_time = datetime.datetime.strptime(time_data[:-4], '%Y%m%d %H:%M:%S')
        time_table.append(time_data)
        if (time_time - time_disaster).days >= 0:
            time_str = 'AfterDisaster_' + time_data.replace(' ', '')
        else:
            time_str = 'BeforeDisaster_' + time_data.replace(' ', '')
        pixel_data = summary_dict.get('Pds_PixelSpacing')
        name_data = summary_dict.get('Pdi_L21ProductFileName01')
        dir_data = os.path.join(raw_img_folder_dir, name_data)

        tif = gdal.Open(dir_data, gdalconst.GA_ReadOnly)
        print(tif.GetProjection())
        print(tif.GetGeoTransform())
        dir_warped_data = dir_data[:-4] + '_warped.tif'
        subprocess.call('gdalwarp -s_srs EPSG:32654 -t_srs EPSG:4326 {} {}'.format(dir_data, dir_warped_data).split())
        # subprocess.call('gdalwarp -s_srs EPSG:4338 -t_srs EPSG:4326 {} {}'.format(dir_data, dir_warped_data).split())

        try:
            clipped_img_path = clip_raw_dir + time_str + '_' + pixel_data + '.tif'
            subprocess.call('gdal_translate -projwin {} {} {} {} {} {}'.format(
                ulx, uly, lrx, lry, dir_warped_data, clipped_img_path).split())
            table.append([name_data, time_data, pixel_data, True])
            os.remove(dir_warped_data)

            tgt_dir, tgt_name = os.path.split(clipped_img_path)
            tgt_name, ext = os.path.splitext(tgt_name)

            subprocess.call('gdal_translate -outsize {} {} {} {}'.format(
                resize_w, resize_h, clipped_img_path, os.path.join(tgt_dir, tgt_name + '_masksize' + '.tif')).split())
            os.remove(clipped_img_path)

        except:
            print('mesh is not in {}'.format(name_data))
            table.append([name_data, time_data, pixel_data, False])

    with open(clip_raw_dir+'summary.txt', 'w') as f:
        for row in table:
            f.write("%s\n" % row)

    print('clipping complete')
    return float(pixel_data), os.path.join(tgt_dir, tgt_name + '_masksize' + '.tif'), time_table


# save image with the provided geo-referrence
# overlay the detected disaster on the RGB image
def make_img(cord1, cord2, img_cord, ori_path, tgt_path):
    img_raw = Image.open(ori_path)
    w1, h1 = img_raw.size
    exif_r = img_raw.getexif()
    for k, v in exif_r.items():
        if k == 34853:
            print(v)
    img_out1 = Image.new(mode="RGB", size=(img_raw.width, img_raw.height), color=(0,0,0))
    draw_point1 = ImageDraw.Draw(img_out1)
    img_out2 = Image.new(mode="RGB", size=(img_raw.width, img_raw.height), color=(0, 0, 0))
    draw_point2 = ImageDraw.Draw(img_out2)
    img_out3 = Image.new(mode="RGB", size=(img_raw.width, img_raw.height), color=(0, 0, 0))
    draw_point3 = ImageDraw.Draw(img_out3)
    print('cord1')
    for row in cord1:
        pix = cord_to_pix(row, img_cord, h1, w1)
        draw_point1.rectangle((pix[0]-10, pix[1]-10, pix[0]+10, pix[1]+10), fill=(0, 250, 250))
        draw_point3.rectangle((pix[0]-10, pix[1]-10, pix[0]+10, pix[1]+10), fill=(0, 250, 250))
    print('cord2')
    for row in cord2:
        pix = cord_to_pix(row, img_cord, h1, w1)
        draw_point2.rectangle((pix[0]-10, pix[1]-10, pix[0]+10, pix[1]+10), fill=(250, 0, 0))
        draw_point3.rectangle((pix[0]-10, pix[1]-10, pix[0]+10, pix[1]+10), fill=(250, 0, 0))

    img_out1.save(tgt_path + 'water.tif', exif=exif_r)
    img_out2.save(tgt_path+'ground.tif', exif=exif_r)
    img_raw.save(tgt_path+'disaster.tif', exif=exif_r)

    return None


# 3次メッシュのリストから4次メッシュリストに変換(データサイズの問題)
def make_meshlist(mesh_8bits):
    mesh_9bits = [int(mesh*10 + i) for mesh in mesh_8bits for i in range(1, 5)]
    return pd.DataFrame({'mesh' : mesh_9bits})


# メッシュは日本4次メッシュ(約500m四方)を想定
# 隣のメッシュを取得する, hw=1:東隣, hw=-1:南隣
def neibour_mesh(mesh_code, hw):
    y, x = ju.to_meshpoint(mesh_code, (hw*0.5), 1+(hw*0.5))
    return ju.to_meshcode(y, x, 4)


# 指定範囲内のメッシュリスト
def obtain_mesh(cord):
    ulx = cord[0] + 0.0001
    uly = cord[1] - 0.0001
    lrx = cord[2] - 0.0001
    lry = cord[3] + 0.0001
    ulm = ju.to_meshcode(uly, ulx, 4)
    llm = ju.to_meshcode(lry, ulx, 4)
    urm = ju.to_meshcode(uly, lrx, 4)
    lrm = ju.to_meshcode(lry, lrx, 4)

    h, w = (0, 0)
    tmp_m = ulm
    while(tmp_m!=llm):
        tmp_m = neibour_mesh(tmp_m, -1)
        h += 1

    tmp_m = ulm
    while (tmp_m!=urm):
        tmp_m = neibour_mesh(tmp_m, 1)
        w += 1

    mesh_list = [ulm]
    parent_m = ulm
    tmp_m = parent_m
    for j in range(w):
        tmp_m = neibour_mesh(tmp_m, 1)
        mesh_list.append(tmp_m)
    for i in range(h):
        parent_m = neibour_mesh(parent_m, -1)
        tmp_m = parent_m
        mesh_list.append(tmp_m)
        for j in range(w):
            tmp_m = neibour_mesh(tmp_m, 1)
            mesh_list.append(tmp_m)

    return mesh_list

# 緯度経度を画像のピクセル座標に変換
def cord_to_pix(in_cord, img_cord, img_h, img_w):
    # in_cord = [x, y]
    # img_cord = [ulx, uly, lrx, lry]
    x_pix = img_w * ((in_cord[0] - img_cord[0]) / (img_cord[2] - img_cord[0]))
    y_pix = img_h * ((in_cord[1] - img_cord[1]) / (img_cord[3] - img_cord[1]))

    return int(x_pix), int(y_pix)


# 画像のピクセル座標を緯度経度に変換
def pix_to_cord(in_pix, img_cord, img_h, img_w):
    # in_pix = [x, y]
    # img_cord = [ulx, uly, lrx, lry]
    x_cord = img_cord[0] + (img_cord[2]-img_cord[0])*(in_pix[0]/img_w)
    y_cord = img_cord[1] + (img_cord[3]-img_cord[1])*(in_pix[1]/img_h)

    return x_cord, y_cord


# 画像のサイズを統一する関数
def resize(img_tgt_path, h, w):
    tgt_dir, tgt_name = os.path.split(img_tgt_path)
    tgt_name, ext = os.path.splitext(tgt_name)
    img_tgt = cv2.imread(img_tgt_path)
    img_resized = cv2.resize(img_tgt, (h, w))

    cv2.imwrite(tgt_dir+'/'+tgt_name+'_resized'+ext, img_resized)


# 道路に対して集計を行う関数
def distribute_to_road(mask_table, feat_table, edge_table, img_cord, img_h, img_w, meshsize):
    #mode = 'disaster' or 'vehicle'
    for i, j in feat_table:
        x, y = cord_to_pix([i,j], img_cord, img_h, img_w)
        pix = np.where((mask_table[:,0]==y)&(mask_table[:,1]==x))
        if len(pix[0])!=0:
            road_id = mask_table[pix][0][2]
            edge_table.loc[edge_table['edge_id']==road_id, 'damage_pix'] += (meshsize*meshsize)

    return edge_table

