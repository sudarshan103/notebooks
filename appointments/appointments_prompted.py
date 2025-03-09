

import json
from openai_utils import get_completion_from_messages
import re
from datetime import datetime, timedelta
from appointment_utils import db, trim_messages



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


def handle_user_input(user_input):
    global conversation
    conversation.append({'role':'user', 'content':user_input})
    conversation = trim_messages(conversation)
    bot_response = get_completion_from_messages(conversation)
    conversation.append({'role':'assistant', 'content':bot_response})
    conversation = trim_messages(conversation)
    return bot_response