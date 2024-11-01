from ultralytics import YOLO
import cv2 as cv
import json
import numpy as np
import time
from datetime import datetime
import os
from PIL import Image
from shapely.geometry import Polygon
import multi_variable
import mysql.connector
import difflib



def plateProgram():
    conn = mysql.connector.connect(
    host="100.124.147.43",
    user="admin",
    password ="admin",
    database="projects"
)
    parkinglot_ID = multi_variable.parkinglot_ID
    cursor = conn.cursor()

    

    cursor.execute("SELECT * FROM `camera` WHERE `ParkingLot_ID` = %s AND `Camera_Functions` = 'Detect License plates';", (parkinglot_ID,))
    cam = cursor.fetchall()

    with open('class_new.json', 'r', encoding='utf-8') as file:
        letter_dic = json.load(file)

    model = YOLO('model/yolo11s.pt')
    modelP = YOLO('model/plate11m.pt')
    modelC = YOLO('model/char11x.pt')

    vdo = cv.VideoCapture(cam[0][1])
    # vdo = cv.VideoCapture('vdo_from_park/plate.mp4')


    # cv.namedWindow('Full Scene', cv.WND_PROP_FULLSCREEN)
    # cv.setWindowProperty('Full Scene', cv.WND_PROP_FULLSCREEN, cv.WINDOW_FULLSCREEN)

    skip_frames = 23
    frame_counter = 0


    car_id = []
    cross_car =[]
    id_cross = set()
    dataword = []
    plateName =''
    datacar_in_park = []
    x_threshold=710


    blue = (255, 0, 0)   # unknown
    yellow = (0, 255, 255)  # undefined occupancy

    carhit = []
    car_hascross=[]
    line2first =[]

    no_regisID=[]
    multi =[]


    def letterCheck(id, timeNow, pic_black):
        dataword, plateName, car_id, id_cross, datacar_in_park
        word = {}
        max = 0
        indexmax = 0
        finalword = ""  # Initialize finalword here

        # Processing dataword
        for x in range(len(dataword)):
            if len(dataword[x]) >= max and dataword[x][0][1] == id:
                max = len(dataword[x])
                indexmax = x
        
        for x in range(len(dataword[indexmax])):
            word[x] = {"x": dataword[indexmax][x][2], "word": [[dataword[indexmax][x][0], 1]]}

        # print("===============================================")
        # print(word)
        # print("===============================================")

        for x in dataword:
            if x[0][1] == id:
                for y in x:
                    for z in range(max):
                        if y[2] > (word[z]["x"] - (word[z]["x"]*0.1)) and y[2] < (word[z]["x"] + (word[z]["x"]*0.1)):
                            o = True
                            for k in range(len(word[z]['word'])):
                                if word[z]['word'][k][0] == y[0]:
                                    word[z]['word'][k][1] += 1
                                    o = False
                                    break
                            if o:
                                word[z]['word'].append([y[0], 1])

        # Construct finalword
        for z in range(max):
            maxd = 0
            inmax = 0
            for k in range(len(word[z]['word'])):
                if word[z]['word'][k][1] > maxd:
                    maxd = word[z]['word'][k][1]
                    inmax = k
            finalword += word[z]['word'][inmax][0]
        
        print(finalword)

        max_per = 0
        best_word = None

        cursor.execute("SELECT * FROM `car`;")
        car_row = cursor.fetchall()

        for db in car_row:
            matcher = difflib.SequenceMatcher(None, db[3], finalword)
            per = matcher.ratio() * 100

            if per > max_per:
                max_per = per
                best_word = db[3]

        print('++++++++++')
        print(finalword)

        if max_per >= 75 and id not in no_regisID:
            finalword = best_word

 
        if max_per < 75 and id not in no_regisID:
            no_regisID.append(id)
            if not os.path.exists('no_regis'):
                with open('no_regis', 'w', encoding='utf-8') as file:
                    file.write(f'{finalword} {timeNow}\n')
            else:
                with open('no_regis', 'a', encoding='utf-8') as file:
                    file.write(f'{finalword} {timeNow}\n')

        if id not in car_hascross:
            car_hascross.append(id)
            if finalword == best_word:
                multi_variable.finalword["plate"].append({"plate": finalword, "time_added": time.time()})
                multi_variable.finalword['ajan'].append(True)
                isAjan=True
            else:
                multi_variable.finalword["plate"].append({"plate": finalword, "time_added": time.time()})
                multi_variable.finalword['ajan'].append(False)
                isAjan =False

            sql = "INSERT INTO `timerecord` (`TimeIn`, `PlateLicense`, `Status`, `ID`, `ParkingLot_ID`) VALUES (%s, %s, %s, %s, %s)"
            new_data = (timeNow, finalword, isAjan,id,multi_variable.parkinglot_ID)
            cursor.execute(sql, new_data)
            conn.commit()

            multi.append(multi_variable.finalword)
            cross_car.append([finalword, timeNow])
            print(cross_car)
            print('\n\n\n\n\n')

            if not os.path.exists('plateSave'):
                with open('plateSave', 'w', encoding='utf-8') as file:
                    for x in range(len(cross_car)):
                        file.write(f'{cross_car[x][0]} {timeNow}\n')
            else:
                with open('plateSave', 'a', encoding='utf-8') as file:
                    file.write(f'{finalword} {timeNow}\n')

            current_time = datetime.now()
            day = current_time.strftime('%d-%m-%Y')
            hour = current_time.strftime('%H%M')
            sec = current_time.strftime('%S')

            save_dir = f'plateCross/{day}/{hour}/'
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)

            filename = f'{finalword}_{hour}_{sec}.jpg'
            ret, pic_save = vdo.read()
            cv.imwrite(f'{save_dir}{filename}', pic_save)

        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
        print(finalword)
        print(f'{max_per} {best_word} \n\n\n\n\n\n\n')
        print('&&&&&&&&&&&&&&&&&&&&&&&&&&&&')
   


    def is_line_intersecting_bbox(car, line1):
        x1, y1, x2, y2 = car
        x3,y3,x4,y4 = line1
        line = (x3, y3), (x4, y4) 
        edges = [
            ((x1, y1), (x2, y1)),  # Top
            ((x2, y1), (x2, y2)),  # Right
            ((x2, y2), (x1, y2)),  # Bottom
            ((x1, y2), (x1, y1))   # Left
        ]

        for edge in edges:
            if do_intersect(edge, line):
                return True
        return False


    def do_intersect(line1, line2):
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        (A, B), (C, D) = line1, line2
        return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)
    

    def apply_otsu_threshold(image):
        gray_image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
        blurred_image = cv.GaussianBlur(gray_image, (5, 5), 0)
        _, binary_image = cv.threshold(blurred_image, 0, 255, cv.THRESH_BINARY + cv.THRESH_OTSU)
        return binary_image


    def bbox_to_polygon(pix):
        return Polygon([
            (pix[0], pix[1]),  # มุมบนซ้าย
            (pix[2], pix[1]),  # มุมบนขวา
            (pix[2], pix[3]),  # มุมล่างขวา
            (pix[0], pix[3])   # มุมล่างซ้าย
        ])


    def create_left_polygon(line2, img_height):
        p1,p2,p3,p4 =line2
        return Polygon([
            (0, 0),             # มุมบนซ้ายของภาพ
            (p1, p2),     # จุดแรกของ line2
            (p3, p4),     # จุดที่สองของ line2
            (0, img_height)     # มุมล่างซ้ายของภาพ
        ])
    
    
    def is_intersecting(car_polygon, left_polygon):
        if car_polygon.intersects(left_polygon):
            intersection_area = car_polygon.intersection(left_polygon).area
            car_area = car_polygon.area
            
            if (intersection_area / car_area) > 0.001:
                return True
        return False
    frame_count = 0


    while True:
        if multi_variable.stop_threads:
            break
        try:
            ret, pic = vdo.read()
            width = vdo.get(cv.CAP_PROP_FRAME_WIDTH)
            height = vdo.get(cv.CAP_PROP_FRAME_HEIGHT)
            timeNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")



            if not ret:
                # break
                print('Fail to read, trying to restart | plate')
                print('\n\n\n\n\n\n\n\n')
                vdo = cv.VideoCapture(cam[0][1])
                time.sleep(1)
                continue
            
            # skip frame
            frame_counter += 1
            if frame_counter % (skip_frames + 1) != 0:
                continue
            frame_counter += 1
            pic_black = pic.copy()
            if frame_count % 120 == 0:  # ประมวลผลทุกๆ 3 เฟรม
                result_model = model.track(pic_black, conf=0.5, persist=3,)



            cv.rectangle(pic_black, (0, 0), (x_threshold, pic.shape[0]), (0, 0, 0), thickness=cv.FILLED)

            line1 = cam[0][3]
            line2 = cam[0][4]
           
            line1 = json.loads(line1)
            line2 = json.loads(line2)


            # cv.line(pic, (line1[0],line1[1]),(line1[2],line1[3]), yellow, 5)
            # cv.line(pic, (line2[0],line2[1]),(line2[2],line2[3]), blue, 5)
      
            result_model = model.track(pic_black, conf=0.5, classes=2, persist=True)

            for e in result_model[0].boxes:
                name = result_model[0].names[int(e.cls)]
                pix = e.xyxy.tolist()[0]
                id = int(e.id)
                
                car = (int(pix[0]), int(pix[1]), int(pix[2]), int(pix[3]))

                car_polygon = bbox_to_polygon(pix)
                left_polygon = create_left_polygon(line2, height)

                # line 2 check dont know why
                if is_intersecting(car_polygon, left_polygon):
                    line2first.append(id)
                    # cv.putText(pic, f"hit 2 : {id}", (1000, 1030), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                    for x in carhit:
                        if x == id:
                            letterCheck(id,timeNow,pic_black)

                            # CAR DETECTION
                crop_car = pic_black[int(pix[1]):int(pix[3]), int(pix[0]):int(pix[2])]
                resultP = modelP(crop_car, conf=0.5)

                            # PLATE DETECTION
                for x in resultP[0].boxes:
                    pname = resultP[0].names[int(x.cls)]
                    ppix = x.xyxy.tolist()[0]

                    crop_plate = crop_car[int(ppix[1]):int(ppix[3]), int(ppix[0]):int(ppix[2])]
                    crop_plate = cv.resize(crop_plate, (320, 320))

                    # binary_image = apply_otsu_threshold(crop_plate)
                    # crop_plate = cv.merge([binary_image] * 3)

                    resultC = modelC(crop_plate, conf=0.5)

                    all_word = []
                    
                                # LETTER DETECTION
                    for y in resultC[0].boxes:
                        cname = resultC[0].names[int(y.cls)]
                        cpix = y.xyxy.tolist()[0]
                        try:
                            if len(letter_dic[str(cname)]) ==1:
                                all_word.append([letter_dic[str(cname)], id, cpix[0]])


                        except KeyError:
                            print("Key not found in data dictionary")

                        print(letter_dic[cname])
    
                    if len(all_word) != 0:
                        for x in range(len(all_word)):
                            for y in range(len(all_word)):
                                if all_word[x][2] < all_word[y][2]:
                                    temp = all_word[y]
                                    all_word[y] = all_word[x]
                                    all_word[x] = temp
                        print(all_word)
                        dataword.append(all_word.copy())
                    print('xxxxxxx')
                    if is_line_intersecting_bbox(car, line1):
                        if id in line2first:
                            continue
                            # cv.putText(pic, f"hit 2 first : {id}", (1000, 1000), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                        elif not id in carhit:
                            carhit.append(id)
            # cv.imshow('Full Scene',pic)
            time.sleep(0.1)
            if cv.waitKey(1) & 0xFF == ord('p'):
                break

        except Exception as e:
            print(f'Error: {e}')

    print('_______ ')

    # for ajan , plate in multi_variable.finalword.items():
    #     print(f'{ajan} ajan in multi')
    #     print(f'{plate }plate in multi')
    print(cross_car)
    print('_______ ')

    vdo.release()
    cv.destroyAllWindows()

if __name__ == "__main__":
    plateProgram()

