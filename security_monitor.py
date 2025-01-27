from PCF8574 import PCF8574_GPIO
from Adafruit_LCD1602 import Adafruit_CharLCD
import RPi.GPIO as GPIO
from time import sleep, time
from datetime import datetime
import sys
import os
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import controls
from config import Config
from logger import setup_logger
import io
import threading

class SecurityMonitor:
    def __init__(self, status_queue):
        self.status_queue = status_queue
        self.logger = setup_logger()
        if not self.logger:
            print("Logger setup failed. Exiting...")
            sys.exit(1)

        try:
            self.logger.info("Starting SecurityMonitor initialization")
            self.DOOR_SENSOR_PIN = Config.DOOR_SENSOR_PIN
            self.DOOR_LED_PIN = Config.DOOR_LED_PIN
            self.BUZZER_PIN = Config.BUZZER_PIN
            self.MOTION_SENSOR_PIN = Config.MOTION_SENSOR_PIN
            self.MOTION_LED_PIN = Config.MOTION_LED_PIN
            self.BUZZER_INTERVAL = Config.BUZZER_INTERVAL
            self.CAPTURE_INTERVAL = Config.CAPTURE_INTERVAL
            self.DISPLAY_UPDATE_INTERVAL = Config.DISPLAY_UPDATE_INTERVAL
            self.last_door_state = None
            self.last_motion_state = None
            self.last_buzzer_time = 0
            self.last_capture_time = 0
            self.last_display_update = 0
            
            os.makedirs(Config.IMAGE_DIR, exist_ok=True)
            
            self.setup_camera()
            self.setup_gpio()
            self.setup_lcd()
        except Exception as e:
            if self.logger:
                self.logger.error(f"Initialization error: {str(e)}")
            else:
                print(f"Initialization error: {str(e)}")
            sys.exit(1)

    def setup_gpio(self):
        try:
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.DOOR_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(self.MOTION_SENSOR_PIN, GPIO.IN)
            GPIO.setup(self.DOOR_LED_PIN, GPIO.OUT)
            GPIO.setup(self.MOTION_LED_PIN, GPIO.OUT)
            GPIO.setup(self.BUZZER_PIN, GPIO.OUT)
            GPIO.output(self.DOOR_LED_PIN, GPIO.LOW)
            GPIO.output(self.MOTION_LED_PIN, GPIO.LOW)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            self.logger.info("GPIO setup completed successfully")
        except Exception as e:
            self.logger.error(f"GPIO Setup Error: {str(e)}")
            sys.exit(1)

    def setup_lcd(self):
        try:
            PCF8574_address = 0x27
            PCF8574A_address = 0x3F
            
            try:
                self.mcp = PCF8574_GPIO(PCF8574_address)
            except:
                try:
                    self.mcp = PCF8574_GPIO(PCF8574A_address)
                except:
                    self.logger.error('I2C Address Error!')
                    sys.exit(1)
            
            self.lcd = Adafruit_CharLCD(pin_rs=0, pin_e=2, pins_db=[4,5,6,7], GPIO=self.mcp)
            self.mcp.output(3, 1)
            self.lcd.begin(16, 2)
            self.logger.info("LCD setup completed successfully")
            
        except Exception as e:
            self.logger.error(f"LCD Setup Error: {str(e)}")
            sys.exit(1)

    def setup_camera(self):
        try:
            self.camera = Picamera2()
            video_config = self.camera.create_video_configuration(main={"size": (640, 480)})
            self.camera.configure(video_config)
            self.output = StreamingOutput()
            self.encoder = JpegEncoder()
            self.camera.start_recording(self.encoder, FileOutput(self.output))
            self.logger.info("Camera initialized successfully with streaming")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Camera Setup Error: {str(e)}")
            else:
                print(f"Camera Setup Error: {str(e)}")
            sys.exit(1)

    def update_display(self, force_update=False):
        current_time = time()
        if not force_update and (current_time - self.last_display_update) < self.DISPLAY_UPDATE_INTERVAL:
            return

        try:
            door_state, motion_state, _ = self.get_sensor_states()
            
            self.lcd.setCursor(0, 0)
            door_status = "Door: OPEN   " if door_state else "Door: CLOSED "
            self.lcd.message(door_status)
            
            self.lcd.setCursor(0, 1)
            motion_status = "Motion: YES  " if motion_state else "Motion: NO   "
            self.lcd.message(motion_status)
            
            self.last_display_update = current_time
            
        except Exception as e:
            self.logger.error(f"Display Update Error: {str(e)}")

    def capture_image(self, trigger_type):
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'{trigger_type}_{timestamp}.jpg'
            filepath = os.path.join(Config.IMAGE_DIR, filename)

            self.camera.capture_file(filepath)
            self.logger.info(f"Image captured: {filepath}")  # Add this line

            # Verify file exists
            if not os.path.exists(filepath):
                self.logger.error(f"Capture failed - file not created: {filepath}")
                return None

            return filename
        except Exception as e:
            self.logger.error(f"Image Capture Error: {str(e)}")
            return None
        
    def check_buzzer(self, is_door_open):
        current_time = time()
        if is_door_open and (current_time - self.last_buzzer_time) >= self.BUZZER_INTERVAL:
            GPIO.output(self.BUZZER_PIN, GPIO.HIGH)
            sleep(0.1)
            GPIO.output(self.BUZZER_PIN, GPIO.LOW)
            self.last_buzzer_time = current_time

    def update_door_led(self, is_door_open):
        GPIO.output(self.DOOR_LED_PIN, GPIO.HIGH if is_door_open else GPIO.LOW)

    def update_motion_led(self, motion_detected):
        GPIO.output(self.MOTION_LED_PIN, GPIO.HIGH if motion_detected else GPIO.LOW)

    def get_sensor_states(self):
        try:
            is_door_open = GPIO.input(self.DOOR_SENSOR_PIN) == GPIO.HIGH
            motion_detected = GPIO.input(self.MOTION_SENSOR_PIN) == GPIO.HIGH
            
            state_changed = (is_door_open != self.last_door_state or 
                           motion_detected != self.last_motion_state)
                    
            if state_changed:
                image_filename = None
                if is_door_open and is_door_open != self.last_door_state:
                    image_filename = self.capture_image('door')
                elif motion_detected and motion_detected != self.last_motion_state:
                    image_filename = self.capture_image('motion')

                status_data = {
                    'door': 'OPEN' if is_door_open else 'CLOSED',
                    'motion': 'DETECTED' if motion_detected else 'NONE',
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'image': image_filename
                }

                self.status_queue.put(status_data)
            
            self.last_door_state = is_door_open
            self.last_motion_state = motion_detected
            
            return is_door_open, motion_detected, state_changed
        except Exception as e:
            self.logger.error(f"Error reading sensors: {str(e)}")
            return False, False, False

    def cleanup(self):
        try:
            self.lcd.clear()
            self.camera.stop_recording()
            self.camera.close()
            GPIO.cleanup()
            self.logger.info("Cleaning up resources...")
        except Exception as e:
            self.logger.error(f"Cleanup Error: {str(e)}")

    def run(self):
        self.logger.info('Security monitoring system starting...')
        try:
            self.update_display(force_update=True)
            while True:
                self.update_display()
                sleep(0.1)
        except KeyboardInterrupt:
            self.cleanup()
        except Exception as e:
            self.logger.error(f"Runtime error: {str(e)}")
            self.cleanup()

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = threading.Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)