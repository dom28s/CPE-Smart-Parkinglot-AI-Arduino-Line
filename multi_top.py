import cv2 as cv
import numpy as np
import json
from shapely.geometry import Polygon
from ultralytics import YOLO
import time
import multi_variable
from datetime import datetime
import mysql.connector
from PIL import ImageFont, ImageDraw, Image
from flask import Flask, Response
import gc
import os



def topProgram():
    conn = mysql.connector.connect(
    host="100.124.147.43",
    user="admin",
    password ="admin",
    database="projects"
)
    parkinglot_ID = multi_variable.parkinglot_ID

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM `parkingspace` WHERE `ParkingLot_ID` = %s;", (parkinglot_ID,))
    park = cursor.fetchall()
    
    cursor.execute("SELECT * FROM `camera` WHERE `ParkingLot_ID` = %s AND `Camera_Functions` = 'Detect space';", (parkinglot_ID,))
    cam = cursor.fetchall()

    cursor.execute("    SELECT * FROM `timesetting`;")
    time[0] = cursor.fetchall()

    print(time[0])


    plate_cross =[]

    with open('class_new.json', 'r', encoding='utf-8') as file:
        letter_dic = json.load(file)
        
    model = YOLO('model/yolov8l.pt')

    vdo = cv.VideoCapture(cam[0][1])
    vdo.set(cv.CAP_PROP_BUFFERSIZE,1)
    # vdo = cv.VideoCapture('vdo_from_park/top.mp4')


    frame_counter = 0
    skip_frames = 23

    # cv.namedWindow('Full Scene', cv.WND_PROP_FULLSCREEN)
    # cv.setWindowProperty('Full Scene', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    green = (0, 255, 0)  # Available
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
    

    while True:
        if multi_variable.stop_threads:
            break
        try:
            vdo.grab()
            ret, pic = vdo.retrieve()

            if not ret:
                print('Fail to read, trying to restart || Top')
                vdo = cv.VideoCapture(cam[0][1])
                time.sleep(1)
                continue

            pic_de = pic.copy()
            current_time = datetime.now()
            day = current_time.strftime('%d-%m-%Y')
            hour = current_time.strftime('%H%M')
            sec = current_time.strftime('%S')

            save_dir = f'topCamSave/{day}/'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            filename = f'{hour}.jpg'
            cv.imwrite(f'{save_dir}{filename}', pic_de)
            
            frame_counter += 1
            if frame_counter % (skip_frames + 1) != 0:
                continue
            # if frame_count % 60 == 0:  
            result = model.track(pic_de, conf=0.2, persist=2)

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

            # turn park to poly
            for shape_data in park_data:
                park_polygon = np.array(shape_data['polygon'], np.int32)  # Ensure correct format
                park_poly = Polygon(park_polygon)  
                cv.fillPoly(overlay, [np.array(park_poly.exterior.coords, np.int32)], green)

            for x in result[0].boxes:
                name = result[0].names[int(x.cls)]
                pix = x.xyxy.tolist()[0]
                id = int(x.id)
                cls = int(x.cls)
                car_poly = Polygon([(pix[0], pix[1]),(pix[2], pix[1]),(pix[2], pix[3]),(pix[0], pix[3])])    

                # If not ajan car puttext ID
                if id in car_track['id']:
                    sel_id = car_track['id'].index(id)  # หา index ของ id
                    plate_number = car_track['plate'][sel_id]['plate']  # ดึง plate ตาม index
                    cv.fillPoly(overlay, [np.array(car_poly.exterior.coords, np.int32)], yellow)
                    pic = put_thai_text(pic, plate_number, (int(pix[0]), int(pix[1])),font , (0, 255, 0))
                    # cv.putText(pic, "overlab enter " , (int(pix[0]), int(pix[1])), cv.FONT_HERSHEY_SIMPLEX, 1, purple, 2)
                else:
                    cv.putText(pic, "%s  %.0f" % (str(name), float(x.id)), (int(pix[0]), int(pix[1])), cv.FONT_HERSHEY_SIMPLEX, 1, red, 2)

                # Turn enter to polygon
                enter_inter = polygon_intersection_area(enter_poly, car_poly)
                enter_area = polygon_area(enter_poly)
                enter_percentage = (enter_inter / enter_area) * 100



                # for p in multi_variable.finalword["plate"]:
                #     if time.time() - p["time_added"] >= 60:
                #         multi_variable.finalword["plate"].remove(p)



                # just car NEED TO FIX LATER
                # Check enter intersec
                if enter_percentage >= 10 and id not in car_track['id']:
                    for ajan_value, plate_value in zip(multi_variable.finalword['ajan'], multi_variable.finalword['plate']):
                            
                        car_track['id'].append(id)
                        car_track['is_ajan'].append(ajan_value)  
                        car_track['plate'].append(plate_value)    
                        if plate_value in multi_variable.finalword['plate']:
                            multi_variable.finalword['plate'].remove(plate_value)
                            multi_variable.finalword['ajan'].remove(ajan_value)

                    cv.fillPoly(overlay, [np.array(enter_poly.exterior.coords, np.int32)], red)

                # Parking space occupancy check
                for shape_data in park_data:
                    park_polygon = shape_data['polygon']
                    inter_area = polygon_intersection_area(park_polygon, car_poly)
                    pix_area = polygon_area(park_polygon)
                    
                    if pix_area > 0:  
                        overlap_percentage = (inter_area / pix_area) * 100  
                        if overlap_percentage >= 30 and len(copy_park_data) > 0 and id not in id_inPark:
                            matching_polygon_index = None
                            for index in range(len(copy_park_data)):
                                if copy_park_data[index]['id'] == shape_data['id']:
                                    matching_polygon_index = index
                                    break


                            if matching_polygon_index is not None:
                                green_park -= 1
                                id_inPark.append(id)

                                if car_track["id"] and car_track["is_ajan"]:
                                    for x in car_track["id"]:
                                        if x in id_inPark:
                                            k = car_track['id'].index(x)  
                                            
                                            if k < len(car_track["is_ajan"]):  
                                                if car_track["is_ajan"][k] == True:
                                                    car_color = red
                                                    red_park+=1
                                                    
                                                    break  

                                                if car_track["is_ajan"][k] == False:
                                                    car_color = blue
                                                    blue_park+=1
                                                    break 

                                if id not in car_track["id"]:  
                                    if cls == 2 or cls == 7: 
                                        car_color = blue
                                        blue_park+=1
                                        
                                    else:
                                        yellow_park +=1
                                        car_color = yellow

                                cursor.execute("UPDATE `parkinglot` SET `UnFreeSpace` = %s, `FreeSpace` = %s, `UnknowCar` = %s, `UnknowObj` = %s WHERE `ParkingLot_ID` = %s;", 
                                (red_park,  green_park, blue_park ,yellow_park, parkinglot_ID))
                                
                                conn.commit()

                                cv.fillPoly(overlay, [np.array(park_polygon, np.int32).reshape((-1, 1, 2))], car_color)
                                copy_park_data.pop(matching_polygon_index)  # Remove the polygon from the available list


            alpha = 0.5
            cv.addWeighted(overlay, alpha, pic, 1 - alpha, 0, pic)
            cv.putText(pic, f'Green {str(green_park)}', (50, 50), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA)
            cv.putText(pic, f'Blue {str(blue_park)}', (50, 80), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            cv.putText(pic, f'Red: {str(red_park)}', (50, 120), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            cv.putText(pic, f'Yellow: {str(yellow_park)}', (50, 150), cv.FONT_HERSHEY_SIMPLEX, 1, green, 2, cv.LINE_AA) 
            
            if len(plate_cross ) != 0:
                pic = put_thai_text(pic, str(plate_cross), (50, 180),font,(0, 255, 0))
            pic = put_thai_text(pic, str(multi_variable.finalword['plate']), (50, 180),font,(0, 255, 0))

            ret, buffer = cv.imencode('.jpg', pic)
            frame = buffer.tobytes()

            yield (b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            
            # cv.imshow('Full Scene', pic)
            print(' top pro')
            time.sleep(0.05)
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