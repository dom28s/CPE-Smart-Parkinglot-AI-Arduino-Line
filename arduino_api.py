from flask import Flask
import mysql.connector
import multi_variable

parkinglot_ID = multi_variable.parkinglot_ID
app = Flask(__name__)

# MySQL database connection settings
db_config = {
    'host': "100.124.147.43",
    'user': "admin",
    'password': "admin",
    'database': "projects"
}

def get_parking_data():
    try:
        # Open a new connection for each request
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()

        # Query to select FreeSpace where ParkingLot_ID = parkinglot_ID
        cursor.execute("SELECT FreeSpace FROM `parkinglot` WHERE ParkingLot_ID = %s;", (parkinglot_ID,))
        status = cursor.fetchall()

        cursor.execute("SELECT `Wifi` FROM `led` WHERE ParkingLot_ID = %s;", (parkinglot_ID,))
        led_user = cursor.fetchall()

        cursor.execute("SELECT `Wifi_Password` FROM `led` WHERE ParkingLot_ID = %s;", (parkinglot_ID,))
        led_pass = cursor.fetchall()

        # Close the cursor and connection
        cursor.close()
        conn.close()

        if status and led_user and led_pass:
            freespace_value = status[0][0]  # Assuming only one row returned for FreeSpace
            led_pass_value = led_pass[0][0]  # Assuming only one row for Wifi_Password
            led_user_value = led_user[0][0]  # Assuming only one row for Wifi
            return [int(freespace_value), str(led_user_value), str(led_pass_value)]
        
        return None
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return None

@app.route('/api/parking', methods=['GET'])
def api_parking():
    data = get_parking_data()
    if data is not None:
        return str(data)  
    else:
        return "Unable to retrieve parking data"

# Run the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5500, debug=True)
