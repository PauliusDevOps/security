import os

class Config:
    # GPIO Pin Configuration
    DOOR_SENSOR_PIN = 16
    DOOR_LED_PIN = 17
    BUZZER_PIN = 12
    MOTION_SENSOR_PIN = 18
    MOTION_LED_PIN = 21
    
    # Timing Configuration
    BUZZER_INTERVAL = 3
    CAPTURE_INTERVAL = 5
    DISPLAY_UPDATE_INTERVAL = 0.5
    
    # Web Interface Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'change-this-in-production'
    USERS = {
        'admin': 'scrypt:32768:8:1$zlBphNHgonre4CaR$ed45c748c060576054decf09b9a35fc80587f3f3040243506e850ee0d8cb4d18a0ac002d10ce2f763782e25bd99fe7db3275d5601ed8decfef3f34af811b10a8'  # Use generate_password_hash()
    }
    
    # Paths Configuration
    IMAGE_DIR = 'static/captures'
    LOG_FILE = 'security_monitor.log'
    LOG_LEVEL = 'INFO'
