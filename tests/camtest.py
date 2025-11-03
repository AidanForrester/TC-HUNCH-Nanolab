from picamzero import Camera
from flask import Flask, Response
import cv2
import time

##Create flask and camera instances
app = Flask(__name__) 
cam = Camera()

##Create function to get the jpeg images to display
def generate_frames():
    while True:
        frame = cam.capture_array() 
        frame = cv2.resize(frame, (640, 480)) ##Resize the output image to save cpu power
        # Optional: simple color correction if still reddish
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
              time.sleep(0.05)

@app.route('/videofeed') ##Specify address for feed to refer back to
def videofeed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
