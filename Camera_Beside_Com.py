# 进行人脸录入 / face register
# 录入多张人脸 / support multi-faces
import numpy as np
import cv2
import os
import shutil  # 读写文件
import time

import win32com.client
from PIL import ImageDraw, ImageFont
from PIL import Image

action_list = ['look_ahead', 'look_left', 'look_right', 'rise_head', 'bow_head', 'blink', 'open_mouth', 'smile', 'over']
action_map = {'look_ahead': '请看前方', 'blink': '请眨眼', 'open_mouth': '请张嘴',
              'smile': '请笑一笑', 'rise_head': '请抬头',
              'bow_head': '请低头', 'look_left': '请看左边',
              'look_right': '请看右边', 'over': '录入完成'}
people_type_dict = {'0': 'elder', '1': 'employee', '2': 'volunteer'}

# Dlib 正向人脸检测器
# detector = dlib.get_frontal_face_detector()

# OpenCV DNN face detector
detector = cv2.dnn.readNetFromCaffe("data/data_opencv/deploy.prototxt.txt",
                                    "data/data_opencv/res10_300x300_ssd_iter_140000.caffemodel")


class Face_Register:
    def __init__(self, people_type, id):
        self.init = False
        self.path_photos_from_camera = "data/data_faces_from_camera/"
        self.font = cv2.FONT_ITALIC

        self.existing_faces_cnt = 0  # 已录入的人脸计数器
        self.ss_cnt = 0  # 录入 personX 人脸时图片计数器
        self.faces_cnt = 0  # 录入人脸计数器

        # 之后用来控制是否保存图像的 flag
        self.save_flag = 1
        # 之后用来检查是否先按 'n' 再按 's'，即先新建文件夹再保存
        self.press_n_flag = 0
        # 之后用来提示动作的计数器
        self.index = 0

        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0

        self.people_type = people_type_dict[str(people_type)]
        self.id = str(id)

    def speak(self):
        text = action_map[action_list[self.index]]
        speak = win32com.client.Dispatch('Sapi.SpVoice')
        # speak.Voice =  speak.GetVoices('Microsoft Zira')
        speak.Volume = 100
        speak.Rate = 2
        speak.Speak(text)

    # 新建保存人脸图像文件
    def pre_work_mkdir(self):
        if os.path.isdir(self.path_photos_from_camera):
            if os.path.isdir(self.path_photos_from_camera + '/' + self.people_type):
                pass
            else:
                os.mkdir(self.path_photos_from_camera + '/' + self.people_type)
        else:
            os.mkdir(self.path_photos_from_camera)

    # 删除之前存的人脸数据文件夹
    def pre_work_del_old_face_folders(self):
        # 删除之前存的人脸数据文件夹
        folders_rd = os.listdir(self.path_photos_from_camera)
        for i in range(len(folders_rd)):
            shutil.rmtree(self.path_photos_from_camera + folders_rd[i])
        if os.path.isfile("data/features_all.csv"):
            os.remove("data/features_all.csv")

    # 如果有之前录入的人脸, 在之前 person_x 的序号按照 person_x+1 开始录入 (v1)
    # 根据传入的人员类型和 id 录入 (v2)
    def check_existing_faces_cnt(self):
        if os.listdir("data/data_faces_from_camera/"):
            # 获取已录入的最后一个人脸序号
            person_list = os.listdir("data/data_faces_from_camera/")
            person_num_list = []
            for person in person_list:
                person_num_list.append(int(person.split('_')[-1]))
            self.existing_faces_cnt = max(person_num_list)

        # 如果第一次存储或者没有之前录入的人脸, 按照 1 开始录入
        # Start from 1
        else:
            self.existing_faces_cnt = 0

    # 获取处理之后 stream 的帧数
    def update_fps(self):
        now = time.time()
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    # 生成的 cv2 window 上面添加说明文字
    def draw_note(self, img_rd):
        # 添加说明
        # cv2.putText(img_rd, action_map[action_list[index]].encode('utf-8').decode(), (20, 250), self.font, 1,
        #             (0, 255, 0), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "Face Register", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:   " + str(self.fps.__round__(2)), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Faces: " + str(self.faces_cnt), (20, 140), self.font, 0.8, (0, 255, 0), 1, cv2.LINE_AA)
        # cv2.putText(img_rd, "N: Create face folder", (20, 350), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
        # cv2.putText(img_rd, "S: Save current face", (20, 400), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)
        # cv2.putText(img_rd, "Q: Quit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

        font = ImageFont.truetype("simsun.ttc", 30, index=1)
        img_rd = Image.fromarray(cv2.cvtColor(img_rd, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_rd)
        if self.index <= 7:
            draw.text((20, 230), text=action_map[action_list[self.index]].encode('utf-8').decode(), font=font,
                      fill=(0, 255, 0))
        else:
            draw.text((20, 230), text=action_map[action_list[8]].encode('utf-8').decode(), font=font,
                      fill=(0, 255, 0))
        img_rd = cv2.cvtColor(np.array(img_rd), cv2.COLOR_RGB2BGR)
        return img_rd

    # 获取人脸
    def process(self, img_rd):
        self.faces_cnt = 0

        (h, w) = img_rd.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img_rd, (300, 300)), 1.0,
                                     (300, 300), (104.0, 177.0, 123.0))
        detector.setInput(blob)
        faces = detector.forward()

        # 检测到人脸
        if faces.shape[2] != 0:
            # 矩形框
            for i in range(0, faces.shape[2]):
                # 计算矩形框大小
                confidence = faces[0, 0, i, 2]

                # filter out weak detections by ensuring the `confidence` is
                # greater than the minimum confidence
                if confidence < 0.5:
                    continue

                self.faces_cnt += 1

                # compute the (x, y)-coordinates of the bounding box for the
                # object
                box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # 判断人脸矩形框是否超出 480x640
                if endX > 640 or endY > 480 or startX < 0 or startY < 0:
                    # if (endX + ww) > 640 or (endY + hh > 480) or (startX - ww < 0) or (
                    #         startY - hh < 0):
                    cv2.putText(img_rd, "OUT OF RANGE", (20, 300), self.font, 0.8, (0, 0, 255), 1, cv2.LINE_AA)
                    color_rectangle = (0, 0, 255)
                    save_flag = 0
                    print("请调整位置 / Please adjust your position")
                else:
                    color_rectangle = (0, 255, 0)
                    save_flag = 1

                cv2.rectangle(img_rd, tuple([startX, startY]), tuple([endX, endY]), color_rectangle, 2)

        # 生成的窗口添加说明文字
        img_rd = self.draw_note(img_rd)

        self.update_fps()

        if not self.init:
            self.speak()
            self.init = True

        return img_rd

    def take_photo(self, img_rd):
        (h, w) = img_rd.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(img_rd, (300, 300)), 1.0,
                                     (300, 300), (104.0, 177.0, 123.0))
        detector.setInput(blob)
        faces = detector.forward()
        current_face_dir = self.path_photos_from_camera + self.people_type + '/' + self.id
        # 新建存储人脸的文件夹
        if not os.path.exists(current_face_dir):
            # self.existing_faces_cnt += 1
            # current_face_dir = self.path_photos_from_camera + "person_" + str(self.existing_faces_cnt)
            os.makedirs(current_face_dir)
            # print('\n')
            # print("新建的人脸文件夹 / Create folders: ", current_face_dir)
            #
            self.ss_cnt = 0  # 将人脸计数器清零
            # self.index = 0
            self.press_n_flag = 1  # 已经按下 'n'

        # 检测到人脸
        if faces.shape[2] != 0:
            # 矩形框
            for i in range(0, faces.shape[2]):
                # 计算矩形框大小
                confidence = faces[0, 0, i, 2]

                # filter out weak detections by ensuring the `confidence` is
                # greater than the minimum confidence
                if confidence < 0.5:
                    continue

                self.faces_cnt += 1

                # compute the (x, y)-coordinates of the bounding box for the
                # object
                box = faces[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")

                # height = (endY - startY)
                # width = (endX - startX)
                # # hh = int(height / 14)
                # # ww = int(width / 14)

                # 判断人脸矩形框是否超出 480x640
                if endX > 640 or endY > 480 or startX < 0 or startY < 0:
                    # if (endX + ww) > 640 or (endY + hh > 480) or (startX - ww < 0) or (
                    #         startY - hh < 0):
                    cv2.putText(img_rd, "OUT OF RANGE", (20, 300), self.font, 0.8, (0, 0, 255), 1, cv2.LINE_AA)
                    color_rectangle = (0, 0, 255)
                    save_flag = 0
                    print("请调整位置 / Please adjust your position")
                else:
                    color_rectangle = (0, 255, 0)
                    save_flag = 1

                cv2.rectangle(img_rd, tuple([startX, startY]), tuple([endX, endY]), color_rectangle, 2)

                if save_flag:
                    # 保存摄像头中的人脸到本地
                    # 检查有没有先按'n'新建文件夹
                    if self.press_n_flag:
                        self.ss_cnt += 1

                        if self.index <= 7:
                            img_blank = img_rd[startY:endY, startX:endX]
                            cv2.imwrite(current_face_dir + "/img_face_" + str(self.ss_cnt) + ".jpg", img_blank)
                            print("写入本地 / Save into：",
                                  str(current_face_dir) + "/img_face_" + str(self.ss_cnt) + ".jpg")
                        if self.index < len(action_list) - 1:
                            self.index += 1
                        else:
                            self.init = False

                        self.speak()
                    else:
                        print("请先按 'N' 来建文件夹, 按 'S' / Please press 'N' and press 'S'")
            # self.faces_cnt = len(faces)

        # 生成的窗口添加说明文字
        img_rd = self.draw_note(img_rd)

        self.update_fps()

        if not self.init:
            self.index = 0
            self.speak()
            self.init = True

        return img_rd

    def run(self, frame):
        return self.process(frame)
