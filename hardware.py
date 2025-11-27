import time
import logging
try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("gpiozero not found. Running in hardware mock mode.")

from config import DOOR_SENSOR_PIN

class HardwareManager:
    def __init__(self):
        self.door_sensor = None
        if GPIO_AVAILABLE:
            # pull_up=True is standard for reed switches connecting to ground
            self.door_sensor = Button(DOOR_SENSOR_PIN, pull_up=True) 

    def is_door_open(self):
        if GPIO_AVAILABLE and self.door_sensor:
            return not self.door_sensor.is_pressed # Assuming switch closes (pressed) when door is closed
        else:
            # Mock behavior: Always return False (closed) unless manually triggered in test
            return False

    def wait_for_door_open(self):
        logging.info("Waiting for door to open...")
        if GPIO_AVAILABLE and self.door_sensor:
            self.door_sensor.wait_for_release() # wait for switch to open
        else:
            time.sleep(2) # Mock wait
            logging.info("Mock door opened!")
