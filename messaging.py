import logging

class MessagingService:
    def send_welcome_message(self, phone_number):
        import subprocess
        import os
        
        logging.info(f"Sending welcome message to {phone_number}...")
        
        script_path = os.path.join(os.path.dirname(__file__), "messaging", "send_message.js")
        
        # Ensure phone number has country code (assuming Mexico +52 for now if missing)
        # This is a basic check, can be improved
        # Clean number
        phone_number = ''.join(filter(str.isdigit, phone_number))
        
        # Handle Mexico '01' prefix (obsolete but common in dictation)
        if phone_number.startswith("01") and len(phone_number) > 10:
            phone_number = phone_number[2:]
            
        # Ensure phone number has country code
        if len(phone_number) == 10:
            from config import PHONE_COUNTRY_CODE
            phone_number = PHONE_COUNTRY_CODE + phone_number
            
        logging.info(f"Formatted phone number for WhatsApp: {phone_number}")
            
        try:
            result = subprocess.run(
                ["node", script_path, phone_number],
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )
            logging.info(f"Node.js output: {result.stdout}")
            return True
        except subprocess.CalledProcessError as e:
            logging.error(f"Error sending message: {e.stderr}")
            return False
        except subprocess.TimeoutExpired:
            logging.error("Error: Messaging service timed out after 60 seconds.")
            return False
