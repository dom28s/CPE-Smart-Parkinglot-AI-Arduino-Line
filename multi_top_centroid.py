import cv2 as cv
import numpy as np
import json
from shapely.geometry import Polygon
from ultralytics import YOLO
import time
import multi_variable
from datetime import datetime,timedelta
import mysql.connector
from PIL import ImageFont, ImageDraw, Image
from flask import Flask, Response
import gc
from centroid_tracker import CentroidTracker
import os




def topProgram():
    conn = mysql.connector.connect(
    host="100.124.147.43",
    user="admin",
    password ="admin",
    database="projects"
)

    cursor = conn.cursor()
    parkinglot_ID = multi_variable.parkinglot_ID

    cursor.execute("SELECT * FROM `parkingspace` WHERE `ParkingLot_ID` = %s;", (parkinglot_ID,))
    park = cursor.fetchall()
    
    cursor.execute("SELECT * FROM `camera` WHERE `ParkingLot_ID` = %s AND `Camera_Functions` = 'Detect space';", (parkinglot_ID,))
    cam = cursor.fetchall()

    

    plate_cross =[]

    with open('class_new.json', 'r', encoding='utf-8') as file:
        letter_dic = json.load(file)
        
    model = YOLO('model/yolo11l.pt')

    vdo = cv.VideoCapture(cam[0][1])
    # vdo = cv.VideoCapture('vdo_from_park/top.mp4') 
    # vdo = cv.VideoCapture('vdo_from_park/person.mp4') 


    frame_counter = 0
    skip_frames = 23

    # cv.namedWindow('Full Scene', cv.WND_PROP_FULLSCREEN)
    # cv.setWindowProperty('Full Scene', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    green = (0, 255, 0)
    red = (0, 0, 255)    # Occupied
    yellow = (0, 255, 255)  # Obstacle
    blue = (255,0,0) #บุคคลภายนอก
    purple = (128, 0, 128)

    font = ImageFont.truetype("THSarabunNew.ttf", 48)


    park_data = []
    enter_data = []
   
    frame_count = 0

    car_track = {
        "is_ajan":[],
        "plate":[],
        "id":[]
    }

    car = {
        "name": [],
        "cls": [],
        "bbox": [],
        "id": [],
        "polygon" : []
    }


    tracker = CentroidTracker(maxDisappeared=10)


    def polygon_area(polygon):
        """ Calculate the area of a polygon """
        return Polygon(polygon).area
    

    def polygon_intersection_area(polygon1, polygon2):
        """ Calculate the intersection area of two polygons """
        poly1 = Polygon(polygon1)
        poly2 = Polygon(polygon2)
        intersection = poly1.intersection(poly2)
        return intersection.area
    

    def load_from_sql():
        data = []       
        for row in park:
            if row[2] != None:
                data.append(row)
            
            else:
                enter_data.append(json.loads(row[4]))
        for row in data:
            id_value = row[0]
            point_value = eval(row[2]) if row[2] != '' else []
            park_data.append({"id": id_value, "polygon": point_value})
        return enter_data,park_data
    
    
    def put_thai_text(image, text, position, font, color):
        try:
            image_pil = Image.fromarray(image)  # No need for color conversion if the image is BGR already
            draw = ImageDraw.Draw(image_pil)
            draw.text(position, text, font=font, fill=color)
            image = np.array(image_pil)
            
            del draw
            del image_pil

        except Exception as e:
            print(f"Error in put_thai_text: {e} || in top program")
            cv.putText(image, str(text), (int(position[0]), int(position[1])), cv.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        return image
    
    

    enter_data,park_data=load_from_sql()
    cursor.execute("UPDATE `parkinglot` SET `AllSpace` = %s WHERE `ParkingLot_ID` = %s;", (len(park_data), parkinglot_ID))
    

    default_time = 5*60
    last_saved_time = time.time()

    def save_image(pic):
        # ดึงวันเวลาเพื่อสร้างชื่อไดเรกทอรีและชื่อไฟล์
        now = datetime.now()
        day = now.strftime('%d-%m-%Y')
        hour = now.strftime('%H%M')

        # สร้างไดเรกทอรีถ้าไม่มีอยู่
        save_dir = f'topCamSave/{day}/'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # บันทึกภาพ
        filename = f'{hour}.jpg'
        cv.imwrite(f'{save_dir}{filename}', pic)
        print(f"บันทึกภาพ: {save_dir}{filename}")



    while True:
        if multi_variable.stop_threads:
            break
        try:
            ret, pic = vdo.read()
            if not ret:
                # break
                print('Fail to read, trying to restart')
                vdo = cv.VideoCapture(cam[0][1])
                time.sleep(1)
                continue

            conn = mysql.connector.connect(
            host="100.124.147.43",
            user="admin",
            password ="admin",
            database="projects"
        )


            pic_de = pic.copy()
            current_time = time.time()


            cursor = conn.cursor()
            cursor.execute("SELECT SQL_NO_CACHE time FROM timesetting WHERE ParkingLot_ID = %s;", (parkinglot_ID,))
            time_set = cursor.fetchone()

            # ตรวจสอบว่าได้ผลลัพธ์หรือไม่ และแปลงค่าถ้าจำเป็น
            if time_set is None:
                print(time_set)
                time_set = default_time  # ใช้ค่าเริ่มต้นถ้าไม่มีข้อมูลในฐานข้อมูล
            else:
                time_set = time_set[0]*60  # ดึงค่าแรกจาก tuple (ผลลัพธ์ของ cursor.fetchone()) และใช้เป็นเวลา

            current_time = time.time()  # เก็บเวลา ณ ปัจจุบัน
            if current_time - last_saved_time >= time_set:  # ใช้ time_set ในการเปรียบเทียบ
                save_image(pic_de)  # บันทึกภาพ
                last_saved_time = current_time  # อัปเดตเวลาที่บันทึกล่าสุด

            frame_counter += 1
            if frame_counter % (skip_frames + 1) != 0:
                continue
            result = model(pic_de, conf=0.5,classes = [0,1,2,3,5,7])

            overlay = pic.copy()
            copy_park_data = park_data.copy()
            id_inPark = []
            green_park = len(park_data)
            blue_park = 0
            red_park =0
            yellow_park =0

            # turn enter to polygon
            enter_poly = Polygon(enter_data[0])  
            cv.fillPoly(overlay, [np.array(enter_poly.exterior.coords, np.int32)], purple)


            # เคลียร์ข้อมูลใน car ก่อนเริ่มต้นเฟรมใหม่
            car["bbox"] = []
            car["cls"] = []
            car["name"] = []
            car["id"] = []  

            boxes = []

            for x in result[0].boxes:
                name = result[0].names[int(x.cls)]
                pix = x.xyxy.tolist()[0]
                cls = int(x.cls)

                boxes.append((int(pix[0]), int(pix[1]), int(pix[2]), int(pix[3])))
                car["bbox"].append(pix)
                car["cls"].append(cls)
                car["name"].append(name)

            objects = tracker.update(boxes)

            # เตรียมตัวแปร temp_id เพื่อเก็บ id ชั่วคราวที่จับคู่ได้
            temp_id = [-1] * len(car["bbox"])  

            # วนลูปใน objects.items() และจับคู่กับ bbox ที่เก็บใน car["bbox"]
            for (objectID, centroid) in objects.items():
                # จับคู่ bbox กับ centroid โดยการหาค่าที่ใกล้เคียงที่สุด
                for i, bbox in enumerate(car["bbox"]):
                    bbox_center_x = int((bbox[0] + bbox[2]) / 2)
                    bbox_center_y = int((bbox[1] + bbox[3]) / 2)

                    # ถ้าศูนย์กลางของ bbox กับ centroid ใกล้เคียงกันมาก ให้ถือว่าตรงกัน
                    if abs(bbox_center_x - centroid[0]) < 5 and abs(bbox_center_y - centroid[1]) < 5:
                        temp_id[i] = objectID  # จับคู่ id ไว้ชั่วคราว
                        break  # จับคู่เสร็จแล้ว ออกจากลูปย่อย


            car["id"] = temp_id
 
            for x in range(len(car["id"])):
                # print(x)
                if car["id"][x] != -1:  

                    if car["id"][x] in car_track['id']: 
                        plate_index = car_track["id"].index(car["id"][x])  
                        # print(car_track['is_ajan'])
                        if car_track["is_ajan"][0] == True:
                            # print('rrrrrrrrrrrrrrrrrrrrrrrrr')

                            overlay = put_thai_text(overlay, f"{str(car_track['plate'][plate_index]['plate'])}", 
                                                    (int(car["bbox"][x][0]), int(car["bbox"][x][1]) + 30), 
                                                    font, green)
                        else:
                            # print('ggggggggggggggggggggggggggggg')
                            overlay = put_thai_text(overlay, f"{str(car_track['plate'][plate_index]['plate'])}", 
                                                    (int(car["bbox"][x][0]), int(car["bbox"][x][1]) + 30), 
                                                    font, red)
                            
                            
                    elif car['cls'][x] == 2 or car['cls'][x] == 7:  # ถ้าไม่พบ ID แต่เป็นรถหรือรถบรรทุก
                        cv.putText(pic, f'ID: {car["id"][x]}', (int(car["bbox"][x][0]), int(car["bbox"][x][1]) - 10), 
                                cv.FONT_HERSHEY_SIMPLEX, 1, green, 2)
                        
                    else:  # ถ้าไม่ใช่รถหรือรถบรรทุก
                        cv.putText(overlay, f'ID: {car["id"][x]} {car["name"][x]}', (int(car["bbox"][x][0]), int(car["bbox"][x][1]) - 10), 
                                cv.FONT_HERSHEY_SIMPLEX, 1, yellow, 2)
            #     else:
            #         print(f"ID: {car['id'][x]} not matched")

            # print("=====================================")

            
            # print(car['id'])

            for idx in range(len(car['id'])):  

                bbox = car['bbox'][idx]  
                bbox_polygon = [[bbox[0], bbox[1]],  # top-left corner
                                [bbox[2], bbox[1]],  # top-right corner
                                [bbox[2], bbox[3]],  # bottom-right corner
                                [bbox[0], bbox[3]]]  # bottom-left corner
                
                # Calculate the intersection area between enter_poly and the bbox_polygon
                enter_inter = polygon_intersection_area(enter_poly, Polygon(bbox_polygon))
                # print('Intersection calculated')
                
                enter_area = polygon_area(enter_poly)
                enter_percentage = (enter_inter / enter_area) * 100
                
                # Check the car's class
                if car['cls'][idx] == 2 or car['cls'][idx] == 7:
                    # print(car['name'][idx])
                    # print(f'id :{car["id"][idx]} class : {car["cls"][idx]}')  # ใช้ car['id'][idx] เพื่อระบุ id จริง
                    # print('xxxxxxxxxxx')
                    # print('\n')
                    
                    # Check if the car is already tracked and if it intersects with the enter_poly
                    if enter_percentage >= 10 and car['id'][idx] not in car_track['id'] and car["cls"][idx] in [2, 7]:
                        for ajan_value, plate_value in zip(multi_variable.finalword['ajan'], multi_variable.finalword['plate']):
                            car_track['id'].append(car['id'][idx])  # เพิ่ม car['id'][idx] แทนที่จะเป็น idx
                            car_track['is_ajan'].append(ajan_value)
                            car_track['plate'].append(plate_value)
                            # print(f'{car["id"][idx]} {car["name"][idx]} enter')
                            
                            if plate_value in multi_variable.finalword['plate']:
                                multi_variable.finalword['plate'].remove(plate_value)
                                multi_variable.finalword['ajan'].remove(ajan_value)

                        cv.fillPoly(overlay, [np.array(enter_poly.exterior.coords, np.int32)], red)
                
            #     print(car_track)


            # print('zzzzzzzzzzzzzzzzzzzzzzzzzz')
            
            for shape_data in park_data:
                park_polygon = np.array(shape_data['polygon'], np.int32)  # Ensure correct format
                park_poly = Polygon(park_polygon)  
                car_target = True

                for id in car['id']:
                    bbox = car['bbox'][car['id'].index(id)]
                    
                    car_poly = [[bbox[0], bbox[1]],  # top-left corner
                                [bbox[2], bbox[1]],  # top-right corner
                                [bbox[2], bbox[3]],  # bottom-right corner
                                [bbox[0], bbox[3]]]  # bottom-left corner

                    # Calculate intersection area and percentage
                    park_inter = polygon_intersection_area(park_poly, car_poly)
                    park_area = polygon_area(park_poly)
                    park_percentage = (park_inter / park_area) * 100 

                    if park_percentage > 30 and len(copy_park_data) > 0 and id not in id_inPark:
                        matching_polygon_index = None
                        for index in range(len(copy_park_data)):
                            if copy_park_data[index]['id'] == shape_data['id']:
                                matching_polygon_index = index
                                break

                        if matching_polygon_index is not None:
                            green_park -= 1
                            id_inPark.append(id)

                            # Determine the car color based on the tracking data
                            car_color = None
                            if len(car_track["id"]) > 0 and len(car_track["is_ajan"]) > 0:
                                for x in car_track["id"]:
                                    if x in id_inPark:
                                        k = car_track['id'].index(x)  
                                        
                                        if k < len(car_track["is_ajan"]):  
                                            if car_track["is_ajan"][k] == True:
                                                car_color = red
                                                red_park += 1
                                                break  

                                            if car_track["is_ajan"][k] == False:
                                                car_color = blue
                                                blue_park += 1
                                                break 

                            # If the ID is not in the tracking data
                            if id not in car_track["id"]:  
                                if car["cls"][car["id"].index(id)] in [2, 7]: 
                                    car_color = blue
                                    blue_park += 1
                                else:
                                    yellow_park += 1
                                    car_color = yellow

                            # Ensure that car_color is set before updating the database
                            if car_color is not None:
                                cv.fillPoly(overlay, [np.array(park_polygon, np.int32).reshape((-1, 1, 2))], car_color)
                                copy_park_data.pop(matching_polygon_index)  # Remove the polygon from the available list
                                car_target = False
                                break
                                
                if car_target:
                    cv.fillPoly(overlay, [np.array(park_polygon, np.int32).reshape((-1, 1, 2))], green)

            
            
            # print('yyyyyyyyyyyyyyyyyyyy')

                    

            alpha = 0.5
            cv.addWeighted(overlay, alpha, pic, 1 - alpha, 0, pic)
            cv.putText(pic, f'Green {str(green_park)}', (50, 50), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA)
            cv.putText(pic, f'Blue {str(blue_park)}', (50, 80), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            cv.putText(pic, f'Red: {str(red_park)}', (50, 120), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            cv.putText(pic, f'Yellow: {str(yellow_park)}', (50, 150), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            cursor.execute("UPDATE `parkinglot` SET `UnFreeSpace` = %s, `FreeSpace` = %s, `UnknowCar` = %s, `UnknowObj` = %s WHERE `ParkingLot_ID` = %s;", 
                                (red_park, green_park, blue_park, yellow_park, parkinglot_ID))
            conn.commit()
            if len(plate_cross ) != 0:
                pic = put_thai_text(pic, str(plate_cross), (50, 180),font,green)
            pic = put_thai_text(pic, str(multi_variable.finalword['plate']), (50, 180),font,green)

            ret, buffer = cv.imencode('.jpg', pic)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            # cv.imshow('Full Scene', pic)
            print(' top pro')
            del pic
            del pic_de
            del overlay
            gc.collect()
            if cv.waitKey(1) & 0xFF == ord('q'):
                multi_variable.stop_threads = True  # ตั้งค่า flag
                break

        except Exception as e:
            print(f'Error: {e}  || in except top program')
            print('\n\n\n\n\n\n\n')
            print(car_track)

    vdo.release()
    cv.destroyAllWindows()



if __name__ == "__main__":
    topProgram()