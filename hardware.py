import time
import logging

# Try to import gpiozero, but handle all possible failures gracefully
GPIO_AVAILABLE = False
try:
    from gpiozero import Button
    GPIO_AVAILABLE = True
except ImportError:
    logging.warning("gpiozero not found. Running in hardware mock mode.")
except Exception as e:
    logging.warning(f"GPIO initialization failed: {e}. Running in hardware mock mode.")

from config import DOOR_SENSOR_PIN

class HardwareManager:
    def __init__(self, mock_mode=False):
        """
        Initialize hardware manager.
        Args:
            mock_mode: Force mock mode even if GPIO is available (useful for testing)
        """
        self.door_sensor = None
        self.mock_mode = mock_mode
        
        if GPIO_AVAILABLE and not mock_mode:
            try:
                # pull_up=True is standard for reed switches connecting to ground
                self.door_sensor = Button(DOOR_SENSOR_PIN, pull_up=True)
                logging.info("GPIO initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize GPIO: {e}. Falling back to mock mode.")
                self.mock_mode = True
        else:
            self.mock_mode = True
            logging.info("Running in MOCK MODE - GPIO disabled")

    def is_door_open(self):
        if self.door_sensor and not self.mock_mode:
            return not self.door_sensor.is_pressed # Assuming switch closes (pressed) when door is closed
        else:
            # Mock behavior: Always return False (closed) unless manually triggered in test
            return False

    def wait_for_door_open(self):
        if self.door_sensor and not self.mock_mode:
            logging.info("Waiting for door to open...")
            self.door_sensor.wait_for_release() # wait for switch to open
            logging.info("Door opened!")
        else:
            logging.info("MOCK MODE: Press Enter to simulate door opening...")
            input()  # Wait for user to press Enter
            logging.info("Mock door opened!")
