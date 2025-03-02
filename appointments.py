

import os
from dotenv import load_dotenv

import mysql.connector
import spacy
from openai_utils import get_completion_from_messages
import re
from datetime import datetime, timedelta
import dateparser

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

nlp = spacy.load("en_core_web_sm")

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


def extract_provider_name(user_input, providers):
    """Extracts doctor name from user input."""
    for provider in providers:
        if provider.lower() in user_input.lower():
            return provider
    return None

def extract_date(user_input):
    """Extracts date (e.g., 'tomorrow', '2025-03-03') from user input."""
    today = datetime.today().date()
    
    if "tomorrow" in user_input.lower():
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')

    match = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', user_input)
    if match:
        return match.group(1)

    return None

def extract_time(user_input):
    """Extracts time (e.g., '10 AM', '15:30') from user input."""
    match = re.search(r'\b(\d{1,2}:\d{2}\s?(AM|PM)?)\b', user_input, re.IGNORECASE)
    if match:
        return match.group(1)

    return None

def extract_entities(user_input):
    """Extracts doctor names, dates, and times using NLP (spaCy)."""
    doc = nlp(user_input)
    extracted_data = {"provider_name": None, "date": None, "time": None}

    for ent in doc.ents:
        if ent.label_ == "PERSON":  # Doctor name
            extracted_data["provider_name"] = ent.text
        elif ent.label_ in ["DATE"]:
            extracted_data["date"] = dateparser.parse(ent.text)
        elif ent.label_ in ["TIME"]:
            extracted_data["time"] = ent.text    

    return extracted_data


def detect_appointment_intent(text):
    doc = nlp(text.lower()) 
    appointment_keywords = {"appointment", "meet", "schedule", "book", "consult"}
    return any(token.text in appointment_keywords for token in doc)
      
def format_timedelta_12h(td):
    # Convert timedelta to total seconds, then extract hours and minutes
    total_seconds = int(td.total_seconds())
    hours = (total_seconds // 3600) % 24  # Ensure it's within 24-hour range
    minutes = (total_seconds // 60) % 60
    
    # Determine AM/PM and adjust hour
    am_pm = "AM" if hours < 12 else "PM"
    hours = hours if 1 <= hours <= 12 else (12 if hours == 0 or hours == 12 else hours % 12)

    return f"{hours}:{minutes:02} {am_pm}"

def handle_user_input(user_input):
    """Processes user input and fetches doctor availability dynamically."""
    
    # Fetch list of providers from database
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT name FROM service_providers")
    providers = [row["name"] for row in cursor.fetchall()]
    cursor.close()

    # Extract doctor name, date, and time using NLP
    extracted_data = extract_entities(user_input)

    provider_name = extract_provider_name(user_input, providers) or extracted_data["provider_name"]
    date = extract_date(user_input) or extracted_data["date"]
    time = extract_time(user_input) or extracted_data["time"]


    if detect_appointment_intent(user_input):
        if not provider_name or not date or not time:
            return "Please specify a doctor, date, and time."
        available = check_availability(provider_name, date, time)
        if available:
         return f"Yes, {provider_name} is available at {time}."
        else:
         slots = get_available_slots(provider_name, date)

         available_times = [slot["available_time"] for slot in slots if "available_time" in slot]

         if available_times:
             formatted_times = [format_timedelta_12h(td) for td in available_times]
             return f"No,  {provider_name} is not available at {time}, but at {', '.join(formatted_times)}"
         else:
             return f"Sorry, {provider_name} has no available slots on {date}."

    else:
        new_message =  messages.copy()
        new_message.append({'role':'user', 'content':user_input})
        return get_completion_from_messages(new_message)
