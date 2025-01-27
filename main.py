from flask import Flask, render_template, Response, send_from_directory
import json
import threading
import queue
import os
import io
from auth import requires_auth
from config import Config
from logger import setup_logger
from werkzeug.security import generate_password_hash
from security_monitor import SecurityMonitor

app = Flask(__name__)
status_queue = queue.Queue()
logger = setup_logger()
monitor = None

@app.route('/')
@requires_auth
def index():
    return render_template('index.html')

@app.route('/events')
@requires_auth
def events():
    def generate():
        while True:
            try:
                status_data = status_queue.get()
                logger.info(f"Sending status data: {status_data}")  
                yield f"data: {json.dumps(status_data)}\n\n"
            except Exception as e:
                logger.error(f"Stream error: {str(e)}")
                continue
    return Response(generate(), mimetype='text/event-stream')

@app.route('/static/captures/<path:filename>')
@requires_auth
def serve_image(filename):
    return send_from_directory(Config.IMAGE_DIR, filename)

@app.route('/video_feed')
@requires_auth
def video_feed():
    return Response(generate_frames(monitor),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


def generate_frames(monitor):
    try:
        while True:
            with monitor.output.condition:
                monitor.output.condition.wait()
                frame = monitor.output.frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    except Exception as e:
        logger.error(f"Streaming Error: {str(e)}")

# HTML template content
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Security Monitor</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f0f0;
        }
        .status-panel {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .status-item {
            margin: 10px 0;
            padding: 15px;
            border-radius: 4px;
        }
        .door-status, .motion-status {
            font-size: 18px;
            font-weight: bold;
        }
        .timestamp {
            color: #666;
            font-size: 14px;
        }
        .open { background-color: #ffebee; }
        .closed { background-color: #e8f5e9; }
        .motion { background-color: #fff3e0; }
        .no-motion { background-color: #f5f5f5; }
        .camera-feed {
            margin-top: 20px;
            text-align: center;
        }
        .camera-feed img {
            max-width: 100%;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .video-container {
            display: flex;
            justify-content: space-between;
            margin-top: 20px;
        }
        .video-feed, .captured-image {
            flex: 1;
            margin: 10px;
            background-color: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h2 {
            color: #333;
            margin-bottom: 15px;
        }
        img {
            max-width: 100%;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="status-panel">
        <h1>Security Monitor Status</h1>
        <div class="status-item" id="doorStatus">
            <div class="door-status">Door: --</div>
        </div>
        <div class="status-item" id="motionStatus">
            <div class="motion-status">Motion: --</div>
        </div>
        <div class="timestamp" id="timestamp">Last update: --</div>
        
        <div class="video-container">
            <div class="video-feed">
                <h2>Live View</h2>
                <img src="{{ url_for('video_feed') }}" alt="Live Camera Feed">
            </div>
            <div class="captured-image">
                <h2>Latest Capture</h2>
                <img id="latestImage" src="" alt="No image available" style="display: none;">
            </div>
        </div>
    </div>

    <script>
        const eventSource = new EventSource('/events');
        
        eventSource.onmessage = function(event) {
            console.log('Received event:', event.data);  // Debug logging
            const data = JSON.parse(event.data);
            
            // Update door status
            const doorStatus = document.querySelector('#doorStatus');
            doorStatus.className = 'status-item ' + (data.door === 'OPEN' ? 'open' : 'closed');
            doorStatus.querySelector('.door-status').textContent = `Door: ${data.door}`;
            
            // Update motion status
            const motionStatus = document.querySelector('#motionStatus');
            motionStatus.className = 'status-item ' + (data.motion === 'DETECTED' ? 'motion' : 'no-motion');
            motionStatus.querySelector('.motion-status').textContent = `Motion: ${data.motion}`;
            
            // Update timestamp
            document.querySelector('#timestamp').textContent = `Last update: ${data.timestamp}`;
            
            // Update captured image
            const imageElement = document.querySelector('#latestImage');
            if (data.image) {
                console.log('Loading image:', data.image);  // Debug logging
                imageElement.onerror = () => console.error('Image load failed:', data.image);
                imageElement.src = `/static/captures/${data.image}`;
                imageElement.style.display = 'block';
            }
        };
        
        eventSource.onerror = function(error) {
            console.error('EventSource failed:', error);
        };
    </script>
</body>
</html>
"""

def create_template_directory():
    if not os.path.exists('templates'):
        os.makedirs('templates')
    with open('templates/index.html', 'w') as f:
        f.write(HTML_TEMPLATE)

def run_flask():
    app.run(host='0.0.0.0', port=5000, threaded=True)

def init_monitor():
    global monitor
    monitor = SecurityMonitor(status_queue)

if __name__ == '__main__':
    create_template_directory()
    
    if 'SECURITY_PASSWORD' in os.environ:
        password = generate_password_hash(os.environ['SECURITY_PASSWORD'])
        Config.USERS = {'admin': password}
    
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    
    init_monitor()
    monitor.run()