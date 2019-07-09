from django.shortcuts import render, redirect
from django.http import HttpResponse, StreamingHttpResponse
from .models import *
from .forms import LazypixelForm
from django.conf import settings
import os
import re
import base64
import cv2
import numpy as np
import threading
import random
import string


class Swapper:
    def __init__(self, flat, cap):
        self.frame_count_float = 0
        self.frame_count = 0
        self.flat = flat
        self.height = len(cap)
        self.width = len(cap[0])
        self.cap = cap.copy().reshape((-1, 3))
        self.in_process = True
        self.thread = threading.Thread(target=self.swap, args=())
        self.thread.start()

    def swap(self):
        while self.frame_count < len(self.flat):
            self.cap[self.frame_count] = self.flat[self.frame_count].copy()
            if self.frame_count < len(self.flat):
                self.frame_count_float += 0.1
                self.frame_count = int(self.frame_count_float)
        self.in_process = False

    def read(self):
        frame = self.cap.copy().reshape((self.height, self.width, 3))
        return frame


class VideoCamera(object):
    def __init__(self):
        self.cap2 = np.zeros((240, 320, 3), np.uint8)

    def get_frame(self):
        ret, jpeg = cv2.imencode('.jpg', self.cap2)
        return jpeg.tobytes()

    def update(self):
        while self.swapper.in_process:
            self.cap2 = self.swapper.read()

    def click(self, old, new):
        self.cap1 = old
        self.cap2 = new
        print(len(self.cap1))
        gray = cv2.cvtColor(self.cap1, cv2.COLOR_BGR2GRAY)
        flat_gray = gray.flatten()
        index1 = np.argsort(flat_gray)
        gray = cv2.cvtColor(self.cap2, cv2.COLOR_BGR2GRAY)
        flat_gray = gray.flatten()
        index2 = np.argsort(flat_gray)
        flat_cap1 = self.cap1.copy().reshape((-1, 3))
        flat_cap2 = self.cap2.copy().reshape((-1, 3))
        flat_cap2[index2] = flat_cap1[index1]
        self.swapper = Swapper(flat_cap2, self.cap2)

        threading.Thread(target=self.update, args=()).start()


def gen(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')


def randstr(string_length=10):
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(string_length))


def cvimage(encoded_data):
    nparr = np.fromstring(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
    return img


def randomPick():
    n = Lazypixels.objects.count()
    rand = random.randint(1, n)
    pick = Lazypixels.objects.get(id=rand)
    return pick.image


cam = VideoCamera()


def liveStream(request):
    global cam
    try:
        return StreamingHttpResponse(gen(cam), content_type="multipart/x-mixed-replace;boundary=frame")
    except:
        pass


def index(request):
    global left_image
    global unique_id
    global left_cv
    if not request.method == 'POST':
        unique_id = randstr()
        left_image = randomPick()
        left_path = settings.BASE_DIR.replace('\\', '/') + str(left_image)
        print(left_path)
        left_cv = cv2.imread(left_path)
        print(left_image)
    else:
        data = request.POST.dict()['image']
        imgstr = re.search(r'base64,(.*)', data).group(1)
        img = cvimage(imgstr)
        img_path = '/media/' + unique_id + '.jpg'
        cv2.imwrite(settings.BASE_DIR.replace('\\', '/') + img_path, img)
        new_data = Lazypixels(image=img_path)
        new_data.save()
        cam.click(left_cv, img)
    return render(request, 'lazypixels/index.html', {'leftImage': left_image})
