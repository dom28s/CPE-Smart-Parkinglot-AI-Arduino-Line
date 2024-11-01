from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, TemplateSendMessage,
    ButtonsTemplate, MessageAction, ConfirmTemplate, CarouselTemplate,
    CarouselColumn, FlexSendMessage
)
import requests
import mysql.connector
import bcrypt
from linebot.exceptions import LineBotApiError




app = Flask(__name__)

 

line_bot_user = LineBotApi('LrNhBjORvm+h1SsEOcwznThZrIpm0y6ZRe/bogFD+ay2c+EbeVf0qLr1P53sCs+APukq/bdIH04ay/QQTSoO23IS4NM0ubq65sFozCePKGhGiawW9cQ0EoULNXvpflgh0hJphhE1+QK3KowHBONOEgdB04t89/1O/w1cDnyilFU=')
handler_user = WebhookHandler('3e756664e46445ccd4dc313e2b37237f')  

line_bot_admin = LineBotApi('SLvwb+XGCcn+taCfbetjjukblmgBGA6vDQUK264pbJGVxj2YWlXzM1eGfVmWf6UslAVoXUuzqspOuvNBx2AVYV1eGcVQmIbq4365SVhK+H4b2s6xwUK7rUiOuaiVBqo+LXBT2YZDwzCT1ftEOwl6FgdB04t89/1O/w1cDnyilFU=')
handler_admin = WebhookHandler('897342c07862a2e8d13715d06b29d47c')  

# เชื่อมต่อ MySQL Database


@app.route("/callback_user_acc", methods=['POST'])
def callback_user():
    # รับข้อมูลจาก Webhook
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler_user.handle(body, signature)
    except Exception as e:
        print(f"Error: {e}")
        abort(400)
    return 'OK'


@app.route("/callback_admin_acc", methods=['POST'])
def callback_admin():
    # รับข้อมูลจาก Webhook
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    
    try:
        handler_admin.handle(body, signature)
    except Exception as e:
        print(f"Error: {e}")
        abort(400)
    return 'OK'

def fetch_parking_lot_data():
    """Fetch real-time parking lot data from the database."""
    conn = mysql.connector.connect(
    host="100.124.147.43",
    user="admin",
    password="admin",
    database="projects"
    )
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM `parkinglot`")
    data = cursor.fetchall()
    cursor.close()
    return data

def all_empty():
    """Create a Flex Message showing all parking lots' free slots."""
    all_status = fetch_parking_lot_data()
    contents = []
    for status in all_status:
        park_name = status[7]
        park_free = status[2]
        park_image_url = "https://your-image-url.com"
        contents.append({
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "image",
                    "url": park_image_url,
                    "size": "sm",
                    "aspect_ratio": "1:1",
                    "flex": 1
                },
                {
                    "type": "text",
                    "text": park_name,
                    "size": "md",
                    "weight": "bold",
                    "flex": 3
                },
                {
                    "type": "text",
                    "text": f"ว่าง {park_free}",
                    "size": "md",
                    "align": "end",
                    "weight": "bold",
                    "color": "#32CD32" if park_free > 0 else "#FF0000",
                    "flex": 2
                }
            ]
        })
    
    flex_message = FlexSendMessage(
        alt_text="สถานะลานจอดรถ",
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": contents
            }
        }
    )
    return flex_message


def parkinglot(user_message):
    """Return Flex Message for a specific parking lot."""
    # Extract the parking lot name from the user message
    save = user_message.replace("ลานจอดรถ ", "")
    
    # Fetch the current status of parking lots
    park_status = fetch_parking_lot_data()
    print(user_message)
    print(park_status)

    # Find the specific parking lot status based on user input
    specific_lot_status = None
    for lot in park_status:
        if lot[-1].lower() == save.lower():  # Assuming the last element contains the lot name
            specific_lot_status = lot[2]  # Assuming the 3rd element contains the available spots
            break
    
    # If the specific parking lot is not found, return a message indicating this
    if specific_lot_status is None:
        return FlexSendMessage(
            alt_text=f'🚫 ลานจอดรถ: {save} ไม่พบ',
            contents={
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"🚫 ไม่พบข้อมูลสำหรับลานจอดรถ: {save}",
                            "weight": "bold",
                            "size": "xxl",
                            "align": "center",
                            "color": "#FF0000",
                            "margin": "md"
                        }
                    ]
                }
            }
        )

    # Construct the Flex Message for the found parking lot
    flex_message = FlexSendMessage(
        alt_text=f'🚗 ลานจอดรถ: {save}\n📊 ว่าง: {specific_lot_status} ช่องจอด',
        contents={
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"🚗 ลานจอดรถ: {save}",
                        "weight": "bold",
                        "size": "xxl",
                        "align": "center",
                        "color": "#FF69B4",
                        "margin": "md"
                    },
                    {
                        "type": "separator",
                        "margin": "lg",
                        "color": "#CCCCCC"
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "🔓 ว่าง: ",
                                "size": "lg",
                                "align": "center",
                                "flex": 1
                            },
                            {
                                "type": "text",
                                "text": f"{specific_lot_status} ช่องจอด",
                                "size": "lg",
                                "align": "center",
                                "weight": "bold",
                                "color": "#32CD32",
                                "flex": 1
                            }
                        ],
                        "margin": "lg"
                    }
                ]
            },
        }
    )
    
    return flex_message


def all_parkinglot():
    """Return a carousel template showing all parking lots."""
    park_data = fetch_parking_lot_data()
    carousel_columns = []
    
    for space in park_data:
        if len(space) > 7:
            action = MessageAction(label='ดูข้อมูล', text=f'ลานจอดรถ {space[7]}')
            carousel_columns.append(
                CarouselColumn(
                    thumbnail_image_url='https://sv1.img.in.th/iw67lb.jpeg',
                    title=f'ลานจอดรถ: {space[7]}',
                    text='📍 คลิกปุ่มด้านล่างเพื่อดูข้อมูลช่องว่างลานจอดรถ',
                    actions=[action]
                )
            )
    
    carousel_template = CarouselTemplate(columns=carousel_columns)
    return TemplateSendMessage(
        alt_text='ลานจอดรถทั้งหมด',
        template=carousel_template
    )



save = None

# ฟังก์ชันสำหรับจัดการข้อความที่ได้รับ
@handler_user.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global save  # ประกาศตัวแปร save ให้เป็น global
    user_message = event.message.text.strip()

    if user_message == "ลานจอดรถทั้งหมด":
        template_message = all_parkinglot()

        line_bot_user.reply_message(
            event.reply_token,
            template_message
        )

        

    else:
        if "ลานจอดรถ" in user_message:
            flex_message = parkinglot(user_message)
            line_bot_user.reply_message(
                event.reply_token,
                flex_message
            )

        if user_message == 'ว่าง':
            flex_message = all_empty()
            line_bot_user.reply_message(
                event.reply_token,
                flex_message
            )

            

logged_in_users = {}  # Store logged-in users
save = None

@handler_admin.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    global save

    # Check if the user is logged in
    if user_id in logged_in_users:
        # Handle parking inquiries
        if user_message.startswith("ประกาศ"):
            url = "https://api.line.me/v2/bot/message/broadcast"
            headers = {
                "Content-Type": "application/json",
                "Authorization": "Bearer LrNhBjORvm+h1SsEOcwznThZrIpm0y6ZRe/bogFD+ay2c+EbeVf0qLr1P53sCs+APukq/bdIH04ay/QQTSoO23IS4NM0ubq65sFozCePKGhGiawW9cQ0EoULNXvpflgh0hJphhE1+QK3KowHBONOEgdB04t89/1O/w1cDnyilFU="  # Replace with your actual token
            }
            
            # Extract the part of the message after "ประกาศ"
            announcement_message = user_message[6:].strip()  # Get the text after "ประกาศ"
            
            # Create the Flex Message
            flex_message = {
                "type": "bubble",
                "size": "mega",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "text": "ประกาศ",
                        "margin": "none",
                        "size": "xxl",
                        "color": "#8c59fe",
                        "weight": "bold",
                        "style": "normal",
                        "align": "center"
                    }
                    ],
                    "spacing": "none",
                    "margin": "none",
                    "backgroundColor": "#ffffff",
                    "cornerRadius": "none",
                    "borderWidth": "none"
                },
                "hero": {
                    "type": "image",
                    "url": "https://sv1.img.in.th/iw67lb.jpeg",
                    "size": "full",
                    "aspectRatio": "20:13",
                    "aspectMode": "cover",
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                    {
                        "type": "text",
                        "weight": "bold",
                        "size": "xl",
                        "text": "เนื้อหา",
                        "color": "#61d8ea"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                        {
                            "type": "box",
                            "layout": "baseline",
                            "spacing": "sm",
                            "contents": [
                            {
                                "type": "text",
                                "text": f"{announcement_message}",
                                "color": "#666666",
                                "size": "lg",
                                "flex": 5
                            }
                            ]
                        }
                        ]
                    }
                    ]
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [],
                    "backgroundColor": "#5ee0e8"
                }
                }

            payload = {
                "messages": [
                    {
                        "type": "flex",
                        "altText": "ประกาศ",
                        "contents": flex_message
                    }
                ]
            }
            
            response = requests.post(url, headers=headers, json=payload)

        line_bot_admin.reply_message(
            event.reply_token,
            TextSendMessage(text="ถ้าต้องการประกาศให้พิมพ์ว่า ประกาศ ตามด้วยข้อความที่ต้องการประกาศ")
        )

        cursor.close()  # ปิด cursor เก่า

    else:
        # Handle login process
        if len(user_message.split()) == 2:
            input_username, input_password = user_message.split()
            conn = mysql.connector.connect(
            host="100.124.147.43",
            user="admin",
            password="admin",
            database="projects"
        )
            # Fetch username and hashed password from the database
            cursor = conn.cursor()
            cursor.execute("SELECT username, password FROM admin WHERE username = %s", (input_username,))
            admin_data = cursor.fetchone()
            cursor.close()

            # Validate the credentials
            if admin_data:
                db_username, db_hashed_password = admin_data

                if bcrypt.checkpw(input_password.encode('utf-8'), db_hashed_password.encode('utf-8')):
                    reply_message = "เข้าสู่ระบบสำเร็จ!"  # Login successful
                    logged_in_users[user_id] = True  # Mark user as logged in
                else:
                    reply_message = "รหัสผ่านไม่ถูกต้อง!"  # Incorrect password
            else:
                reply_message = "ชื่อผู้ใช้ไม่ถูกต้อง!"  # Invalid username
        else:
            reply_message = "กรุณาใส่ชื่อผู้ใช้และรหัสผ่านในรูปแบบ 'username password'"  # Prompt for correct format

        # Reply to the user
        line_bot_admin.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
 

# สำหรับการรัน Flask
if __name__ == "__main__":
    app.run(port=5001)
