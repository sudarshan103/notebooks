

import json
import os
from dotenv import load_dotenv

import mysql.connector
from openai_utils import get_completion_from_messages
import re
from datetime import datetime, timedelta


load_dotenv('/home/sudarshan/notebooks/local.env' )



db = mysql.connector.connect(
    host="localhost",
    user=os.getenv('MYSQL_USERNAME'),
    password=os.getenv('MYSQL_PASSWORD'),
    database="appointments"
)

from datetime import datetime


def get_master_data():
    cursor = db.cursor(dictionary=True)
    query = """
        SELECT sp.name, sp.service, ss.available_date, ss.available_time 
        FROM service_slots ss
        JOIN service_providers sp ON ss.provider_id = sp.id
    """
    
    cursor.execute(query)
    slots = cursor.fetchall()
    cursor.close()
    
    return json.dumps(slots if slots else [{"message": "No available slots"}], default=str)




prompt = f"""
You are an assistant at AI clinic, helping a user to book an appointment with a doctor at date and time as per the doctor's availability
Doctors & the availability slots are as following: 
{get_master_data()},
"Follow these rules:
- Make sure user provides date and doctor name & always check doctor availability before confirming an appointment.
- If a user provides only a date, ask for doctor name or vice versa
- If a user provides a doctor and date but no time, list all available time slots for the date.
- If the requested slot is unavailable, suggest an alternative slot.
- Confirm appointments before finalizing.
- Show the time in 12 hour format, skip seconds part.
- If user provides a doctor, in case of suggesting alternative doctors, consider only the doctors providing same service as user suggested doctor.
"""

conversation_base =  [  
{'role':'system', 'content':f'{prompt}'}    
]


conversation = conversation_base.copy()


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
    global conversation
    conversation.append({'role':'user', 'content':user_input})
    conversation = trim_messages(conversation)
    bot_response = get_completion_from_messages(conversation)
    conversation.append({'role':'assistant', 'content':bot_response})
    conversation = trim_messages(conversation)
    return bot_response


def trim_messages(messages, max_length=15, preserve_count=1):
    if len(messages) <= max_length:
        return messages  # No trimming needed

    # Preserve the first 'preserve_count' messages
    preserved_messages = messages[:preserve_count]

    # Trim older messages from the remaining ones
    remaining_messages = messages[preserve_count:]
    trimmed_remaining = remaining_messages[-(max_length - preserve_count):]

    return preserved_messages + trimmed_remaining


def print_conversation():
    """
    Prints messages in a formatted conversation style.

    :param messages: List of message dictionaries
    """
    role_labels = {
        "system": "System:",
        "assistant": "Assistant:",
        "user": "User:"
    }

    for msg in conversation:
        role = role_labels.get(msg["role"], msg["role"].capitalize() + ":")
        print(f"{role} {msg['content']}")