import logging

class MessagingService:
    def send_welcome_message(self, phone_number):
        logging.info(f"Sending welcome message to {phone_number}...")
        # Placeholder for SMS/WhatsApp API
        print(f"MESSAGE SENT TO {phone_number}: '¡Hola! Aquí tienes tu video del Árbol Encantado. ¡Feliz Navidad!'")
        return True
