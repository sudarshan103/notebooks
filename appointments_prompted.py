

import os
from dotenv import load_dotenv

import mysql.connector
from openai_utils import get_completion_from_messages
import re
from datetime import datetime, timedelta


load_dotenv('/home/sudarshan/notebooks/local.env' )



messages =  [  
{'role':'assistant', 'content':'Hello and welcome to the Super Clinic'},    
{'role':'user', 'content':'Hi can I have an appointment with Dr X'},   
{'role':'assistant', 'content':'Sure, what date and time would you like the appointment?'},
{'role':'user', 'content':'I would like to meet him tomorrow at 10 AM'},  
{'role':'assistant', 'content':'Sure, let me check with the slots'},  
{'role':'system', 'content':'no slots'},  
{'role':'assistant', 'content':'Sorry, he is not available at 10 AM, are you available at 11 AM'},  
{'role':'user', 'content':'ok'},  
{'role':'assistant', 'content':'Great, the appointment is booked'}  
]


db = mysql.connector.connect(
    host="localhost",
    user=os.getenv('MYSQL_USERNAME'),
    password=os.getenv('MYSQL_PASSWORD'),
    database="appointments"
)

from datetime import datetime

def get_available_slots(provider_name, date):
    if isinstance(date, datetime):
        date = date.strftime("%Y-%m-%d")

    cursor = db.cursor(dictionary=True)
    query = """
        SELECT ss.available_time 
        FROM service_slots ss
        JOIN service_providers sp ON ss.provider_id = sp.id
        WHERE sp.name LIKE %s AND ss.available_date = %s
    """
    
    provider_name_like = f"%{provider_name}%"

    cursor.execute(query, (provider_name_like, date))
    slots = cursor.fetchall()
    cursor.close()
    
    return slots if slots else [{"message": "No available slots"}]

def check_availability(provider_name, date, time):
    if isinstance(date, datetime):
        date = date.strftime("%Y-%m-%d")

    cursor = db.cursor(dictionary=True)
    query = """
        SELECT COUNT(*) as count 
        FROM service_slots ss
        JOIN service_providers sp ON ss.provider_id = sp.id
        WHERE sp.name LIKE %s AND ss.available_date = %s AND ss.available_time = %s
    """

    provider_name_like = f"%{provider_name}%"

    cursor.execute(query, (provider_name_like, date, time))
    result = cursor.fetchone()
    cursor.close()
    
    return result["count"] > 0


def handle_user_input(user_input):
    """Processes user input and fetches doctor availability dynamically."""
    
    # Fetch list of providers from database
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name FROM service_providers")
    providers = [row["name"] for row in cursor.fetchall()]
    cursor.close()

    new_message =  messages.copy()
    new_message.append({'role':'user', 'content':user_input})
    return get_completion_from_messages(new_message)