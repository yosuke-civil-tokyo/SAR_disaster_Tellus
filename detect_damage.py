import subprocess
import os

import cv2
from PIL import Image, ImageDraw
from utils import *


# the class for image
class Composite:
    def __init__(self, img_before, img_after, cord, thresh=100):
        # note that input is a pair of SAR images (gray scale)
        self.sar_img_before = cv2.imread(img_before, cv2.IMREAD_GRAYSCALE)
        self.sar_img_after = cv2.imread(img_after, cv2.IMREAD_GRAYSCALE)
        self.cord = cord

        self.h = self.sar_img_before.shape[0]
        self.w = self.sar_img_before.shape[1]

        self.thres_filter = 20
        # lee_filter2 takes longer than lee_filter
        self.sar_img_before = self.lee_filter2(self.sar_img_before)
        self.sar_img_after = self.lee_filter2(self.sar_img_after)

        self.composite_img = np.zeros((self.h, self.w, 3))
        self.composite_img[:, :, 0] = self.sar_img_before
        self.composite_img[:, :, 1] = self.sar_img_before
        self.composite_img[:, :, 2] = self.sar_img_after

        self.thresh = thresh
        print('thresh : {}'.format(self.thresh))
        self.damaged_pix, self.damaged_pix2 = self.from_matrix_to_vec()

        self.process()


    def lee_filter(self, img):
        img_mean = uniform_filter(img, (5, 5))
        img_sqr_mean = uniform_filter(img ** 2, (5, 5))
        img_variance = img_sqr_mean - img_mean ** 2

        overall_variance = variance(img)

        img_weights = img_variance / (img_variance + overall_variance)
        img_output = img_mean + img_weights * (img - img_mean)
        return img_output

    def lee_filter2(self, img):
        img_padding = cv2.copyMakeBorder(img, 1, 1, 1, 1, cv2.BORDER_REFLECT)
        mean_all = cv2.filter2D(img, -1, np.ones((5, 5))/(5**2))
        var_all = np.zeros((self.h, self.w))
        for i in range(1, self.h+1):
            for j in range(1, self.w+1):
                var_all[i-1, j-1] = self.lee_var(img_padding[i-1:i+2, j-1:j+2], mean_all[i-1,j-1])

        var_common = np.mean(heapq.nsmallest(5, var_all.flatten()))
        var_all[var_all==0] = 1
        k_var = (var_all.astype(int) - var_common.astype(int)) / var_all
        k_var[var_all<self.thres_filter] = 1
        hosei = np.multiply(k_var, (img.astype(int) - mean_all.astype(int)))
        img_filtered = mean_all.astype(int) + hosei

        return img_filtered


    # store the (x, y) of pixels judged 'damaged'
    def from_matrix_to_vec(self):
        damaged_pix = np.array(np.where((self.composite_img[:,:,0]-self.composite_img[:,:,2]>=self.thresh)&(self.composite_img[:,:,2]<60))).T
        damaged_pix2 = np.array(np.where((self.composite_img[:, :, 2]-self.composite_img[:, :, 0]>=self.thresh)&(self.composite_img[:,:,0]<30))).T
        
        print('damage detected in {} pix'.format(len(damaged_pix)))
        return damaged_pix, damaged_pix2

    def convert_cord(self, damaged_cord, damaged_cord2):
        for y, x in self.damaged_pix:
            x_cord, y_cord = pix_to_cord([x,y], self.cord, self.h, self.w)
            damaged_cord.append([x_cord, y_cord])
        for y, x in self.damaged_pix2:
            x_cord, y_cord = pix_to_cord([x,y], self.cord, self.h, self.w)
            damaged_cord2.append([x_cord, y_cord])

        return damaged_cord, damaged_cord2

    def lee_var(self, img_clip, mean_val):
        return np.mean((img_clip-mean_val)*(img_clip-mean_val))

    def process(self):
        # the post-process for obtaining area
        # Now skipped is OK
        return None
    
# a function for detection
def detect(df_mesh, sar_data_dir):
    raw_img_dir = sar_data_dir + 'data/raw_sar_L2/'
    clip_raw_dir = sar_data_dir + 'data/clipped/raw/'
    clip_detect_dir = sar_data_dir + 'data/clipped/detect/'
    clipped_img_before = [os.path.join(clip_raw_dir, img) for img in os.listdir(clip_raw_dir) if img.startswith('Before')][0]
    clipped_img_after = [os.path.join(clip_raw_dir, img) for img in os.listdir(clip_raw_dir) if img.startswith('After')][0]

    damaged_cord = []
    damaged_cord2 = []

    for index, row in df_mesh.iterrows():
        code = int(row['mesh'])
        active_dir = clip_raw_dir + str(code) + '/'
        os.makedirs(active_dir, exist_ok=True)
        ulx, uly, lrx, lry = row['ulx'], row['uly'], row['lrx'], row['lry']
        print('Now analyzing mesh {}'.format(code))

        subprocess.call('gdal_translate -projwin {} {} {} {} {} {}'.format(ulx, uly, lrx, lry, clipped_img_before,
                                                                           active_dir + 'raw_before.tif').split())
        subprocess.call('gdal_translate -projwin {} {} {} {} {} {}'.format(ulx, uly, lrx, lry, clipped_img_after,
                                                                           active_dir + 'raw_after.tif').split())

        composite_img_class = Composite(active_dir+'raw_before.tif', active_dir+'raw_after.tif', [ulx,uly,lrx,lry])
        cv2.imwrite(active_dir+'processed_before.png', composite_img_class.sar_img_before)
        cv2.imwrite(active_dir+'processed_after.png', composite_img_class.sar_img_after)
        cv2.imwrite(active_dir+'detect.png', composite_img_class.composite_img)
        damaged_cord, damaged_cord2 = composite_img_class.convert_cord(damaged_cord, damaged_cord2)

    return np.array(damaged_cord), np.array(damaged_cord2)

