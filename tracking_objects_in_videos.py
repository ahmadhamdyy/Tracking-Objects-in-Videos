# -*- coding: utf-8 -*-
"""Tracking_Objects_in_Videos.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1HYnFKGLngsKSl_UeHkA3ZtehedRVX-M4
"""

import cv2
import numpy as np
from google.colab.patches import cv2_imshow
import matplotlib.pyplot as plt

from google.colab import drive
drive.mount('/content/gdrive',force_remount=True)

!unzip /content/gdrive/MyDrive/Data/car_landing.zip

video_path = '/content/car2.npy'

video = np.load(video_path)
frames = video.copy()
frames = np.transpose(frames, (2, 0, 1))

cv2_imshow(frames[0])

img = frames[0].copy()
Roi = [50,110,110,51]
bottom_right = (Roi[0] + Roi[1], Roi[2] + Roi[3])

cv2.rectangle(img, (Roi[0], Roi[1]), (Roi[0]+Roi[2], Roi[1]+Roi[3]), (0, 255, 0), 2)  # Green rectangle

cv2_imshow(img)

temp = img[Roi[1]:Roi[1]+Roi[3],Roi[0]:Roi[0]+Roi[2]]
cv2_imshow(temp)

print(frames.shape)

def jacobian(x_shape, y_shape):
    # get jacobian of the template size.
    x = np.array(range(x_shape))
    y = np.array(range(y_shape))
    x, y = np.meshgrid(x, y)
    ones = np.ones((y_shape, x_shape))
    zeros = np.zeros((y_shape, x_shape))

    row1 = np.stack((x, zeros, y, zeros, ones, zeros), axis=2)
    row2 = np.stack((zeros, x, zeros, y, zeros, ones), axis=2)
    jacob = np.stack((row1, row2), axis=2)

    return jacob



def resample_image(image, iteration, resample):
    for i in range(iteration):
        image = resample(image)
    return image



def crop(img, roi):
    return img[roi[0][1]:roi[1][1], roi[0][0]:roi[1][0]]


def affineLKtracker(img, template, rect, p, threshold ):
        d_p_norm = np.inf

        template = crop(template, rect)
        rows, cols = template.shape
        p_prev = p
        iter = 0
        while (d_p_norm >= threshold):
            warp_mat = np.array([[1+p_prev[0], p_prev[2], p_prev[4]], [p_prev[1], 1+p_prev[3], p_prev[5]]])


            warp_img = crop(cv2.warpAffine(img, warp_mat, (img.shape[1],img.shape[0]),flags=cv2.INTER_CUBIC), rect)

            diff = template.astype(int) - warp_img.astype(int)
            if(abs(np.sum(diff)) < 1000):
              break
            # Calculate warp gradient of image
            grad_x = cv2.Sobel(img, cv2.CV_64F, 1, 0, ksize=5)
            grad_y = cv2.Sobel(img, cv2.CV_64F, 0, 1, ksize=5)

            #warp the gradient
            grad_x_warp = crop(cv2.warpAffine(grad_x, warp_mat, (img.shape[1],img.shape[0]),flags=cv2.INTER_CUBIC+cv2.WARP_INVERSE_MAP), rect)
            grad_y_warp = crop(cv2.warpAffine(grad_y, warp_mat, (img.shape[1],img.shape[0]),flags=cv2.INTER_CUBIC+cv2.WARP_INVERSE_MAP), rect)

            # Calculate Jacobian for the
            jacob = jacobian(cols, rows)

            grad = np.stack((grad_x_warp, grad_y_warp), axis=2)
            grad = np.expand_dims((grad), axis=2)

            #calculate steepest descent
            steepest_descents = np.matmul(grad, jacob)
            steepest_descents_trans = np.transpose(steepest_descents, (0, 1, 3, 2))

            # Compute Hessian matrix
            hessian_matrix = np.matmul(steepest_descents_trans, steepest_descents).sum((0,1))

            # Compute steepest-gradient-descent update
            diff = diff.reshape((rows, cols, 1, 1))
            update = (steepest_descents_trans * diff ).sum((0,1))

            # calculate dp and update it
            d_p = np.matmul(np.linalg.pinv(hessian_matrix), update).reshape((-1))

            p_prev += d_p

            d_p_norm = np.linalg.norm(d_p)
            iter += 1

        return p_prev

template = frames[0].copy()
height, width= template.shape

roi = np.array([[40, 100], [180, 171]])   #car

rect_tl_pt = np.array([roi[0][0], roi[0][1], 1])
rect_br_pt = np.array([roi[1][0], roi[1][1], 1])

video_data = np.zeros((414,) + template.shape, dtype=np.uint8)
# num_layers = 0
template_copy = template.copy()
# template = get_template(template, roi)
threshold = 0.0079

for i in range(frames.shape[0]-1):

    image = frames[i+1].copy()
    meanoftemplate = np.mean(template_copy)
    meanofimage = np.mean(image)
    image = (meanoftemplate/meanofimage) * image


    p = np.zeros(6)
    p_prev = p

    p = affineLKtracker(image, template_copy, roi, p, threshold)

    warp_mat = np.array([[1 + p[0], p[2], p[4]], [p[1], 1 + p[3], p[5]]])

    rect_tl_pt_new = (warp_mat @ rect_tl_pt).astype(int)
    rect_br_pt_new = (warp_mat @ rect_br_pt).astype(int)
    if rect_br_pt_new[0]-rect_tl_pt_new[0] < 70 or rect_br_pt_new[1]-rect_tl_pt_new[1]<30:
          rect_br_pt_new = np.array([rect_tl_pt_new[0] + 120, rect_tl_pt_new[1] + 60])

    cv2.rectangle(image, tuple(rect_tl_pt_new), tuple(rect_br_pt_new), (0, 0, 255), 2)
    cv2_imshow(image)
    video_data[i]=image
    template_copy = frames[i+1].copy()
    p_prev = p

    rect_tl_pt = np.array([rect_tl_pt_new[0], rect_tl_pt_new[1], 1])
    rect_br_pt = np.array([rect_br_pt_new[0], rect_br_pt_new[1], 1])

output_file = 'car.avi'
fps = 30  # Frames per second
height, width = video_data.shape[1], video_data.shape[2]

# Create a VideoWriter object
fourcc = cv2.VideoWriter_fourcc(*'XVID')
out = cv2.VideoWriter(output_file, fourcc, fps, (width, height), isColor=False)

# Write each frame to the video file
for frame in video_data:
    out.write(frame)

# Release the VideoWriter object
out.release()