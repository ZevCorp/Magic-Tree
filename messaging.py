import logging
import requests
import json

class MessagingService:
    def send_welcome_message(self, phone_number, video_path=None):
        logging.info(f"Preparing to send welcome message to {phone_number} via Local Server...")
        
        # Clean number
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Mexico '01' prefix
        if phone_number.startswith("01") and len(phone_number) > 10:
            phone_number = phone_number[2:]
            
        # Ensure phone number has country code (Default Colombia 57 if length is 10)
        # Assuming usually 10 digits for local (3xx xxx xxxx)
        if len(phone_number) == 10:
            from config import PHONE_COUNTRY_CODE
            phone_number = PHONE_COUNTRY_CODE + phone_number
            
        logging.info(f"Target Phone Number: {phone_number}")
            
        try:
            # Send request to local Node.js server
            payload = {"phoneNumber": phone_number, "videoPath": video_path}
            headers = {'Content-type': 'application/json'}
            
            response = requests.post(
                "http://localhost:3000/send-welcome", 
                data=json.dumps(payload), 
                headers=headers,
                timeout=5 # Fast timeout, don't block UI
            )
            
            if response.status_code == 200:
                logging.info(f"Success! Server responded: {response.json()}")
                return True
            else:
                logging.error(f"Server Error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.ConnectionError:
            logging.error("Could not connect to Messaging Server at http://localhost:3000. Is 'node messaging/server.js' running?")
            return False
        except Exception as e:
            logging.error(f"Error sending message request: {e}")
            return False
