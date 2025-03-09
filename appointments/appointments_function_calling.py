from appointment_utils import db, trim_messages
from openai_utils import get_completion_with_function_calling
import json

prompt = f"""
You are an assistant at AI clinic, helping a user to book an appointment with a doctor at date and time as per the doctor's availability
Follow these rules:
- Make sure user provides date and doctor name both.
- If a user provides a doctor, date but no time, list all available time slots for the date using get_available_slots function.
- If a user provides a doctor, date, time check the doctor availability using check_availability function.
- if availability is true, confirm appointments before finalizing.
- if availability is false, list all available time slots regardless of date using get_available_slots function.
- Show the time in 12 hour format, skip seconds part.
"""

conversation_base =  [  
{'role':'system', 'content':f'{prompt}'}    
]


conversation = conversation_base.copy()

def get_available_slots(provider_name, date=None):
    cursor = db.cursor(dictionary=True)
    
    query = """
        SELECT ss.available_date, ss.available_time 
        FROM service_slots ss
        JOIN service_providers sp ON ss.provider_id = sp.id
        WHERE sp.name LIKE %s
    """
    
    params = [f"%{provider_name}%"]
    
    if date:
        query += " AND ss.available_date = %s"
        params.append(date)
    
    cursor.execute(query, tuple(params))
    slots = cursor.fetchall()
    cursor.close()
    
    return slots if slots else []


def check_availability(provider_name, date, time):
    
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

functions=[
            {
                "name": "get_available_slots",
                "description": "Fetch available time slots for a doctor",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider_name": {"type": "string", "description": "Doctor's name"},
                        "date": {"type": "string", "format": "date", "description": "Appointment date (YYYY-MM-DD) optional"}
                    },
                    "required": ["provider_name"] 
                },
                "response": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "description": "Available time slot in HH:MM:SS format (24-hour format)."
                    },
                    "description": "A list of available time slots for the provider. Returns an empty list if no slots are available."
                }
            },
            {
                "name": "check_availability",
                "description": "Check if a service provider (doctor) is available at a specific date and time.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "provider_name": {
                            "type": "string",
                            "description": "The name of the doctor or service provider."
                        },
                        "date": {
                            "type": "string",
                            "format": "date",
                            "description": "The appointment date in YYYY-MM-DD format."
                        },
                        "time": {
                            "type": "string",
                            "description": "The appointment time in HH:MM:SS format (24-hour format)."
                        }
                    },
                    "required": ["provider_name", "date", "time"]
                },
                "response": {
                    "type": "boolean",
                    "description": "Returns true if the provider is available, otherwise false."
                }
            }

        ]


def handle_user_input(user_input):
    global conversation
    conversation.append({'role':'user', 'content':user_input})

    while True:
        conversation = trim_messages(conversation)
        bot_response = get_completion_with_function_calling(conversation, functions)

        if "function_call" in bot_response:
            function_name = bot_response["function_call"]["name"]
            function_args = json.loads(bot_response["function_call"]["arguments"])

            if function_name == "get_available_slots":
                function_response = get_available_slots(**function_args)
                conversation.append({'role': 'function', 'name': function_name, "content": json.dumps(function_response, default=str)})
            elif function_name == "check_availability":
                function_response = check_availability(**function_args)
                conversation.append({'role': 'function', 'name': function_name, "content": function_response})
        else:
            conversation.append({'role':'assistant', 'content':bot_response.content})
            break
    
    return bot_response.content


   
