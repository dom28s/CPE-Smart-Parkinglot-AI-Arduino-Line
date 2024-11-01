import threading
import multi_plate
import multi_top
import multi_top_centroid
import multi_variable
import cv2 as cv
import time
from flask import Flask, Response, render_template

# ตัวแปรสำหรับหยุดเธรด
multi_variable.stop_threads = False

app = Flask(__name__)

@app.route('/video_feed')
def video_feed():
    return Response(multi_top_centroid.topProgram(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Home route
@app.route('/')
def home():
    try:
        # เปิดไฟล์ plateSave.txt และอ่านข้อมูล
        with open('plateSave', 'r') as file:
            data = file.read()
    except FileNotFoundError:
        data = "ไม่พบไฟล์ plateSave.txt"

    return f"""
    <h1>Video Stream</h1>
    <img src="/video_feed" width="1000">
    <h1>เนื้อหาใน plateSave.txt</h1><pre>{data}</pre>
    """

def run_flask():
    app.run(host='0.0.0.0', port=6000, debug=False, use_reloader=False)

def main():
    # Start the Flask server in a new thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    thread_plate = threading.Thread(target=multi_plate.plateProgram)
    thread_top = threading.Thread(target=multi_top_centroid.topProgram)

    thread_plate.start()
    print('1')
    time.sleep(1)
    print('2')
    thread_top.start()

    thread_plate.join()
    thread_top.join()
    flask_thread.join()

    print("ทั้งสองโปรแกรมรันเสร็จแล้ว")

if __name__ == "__main__":
    main()
