import ctypes
import os
from flask import Flask, render_template, Response, request, redirect
import face_recognition
import numpy as np
import cv2
import base64
import io
import PIL.Image
import json
import signal
import threading
from datetime import datetime

app = Flask(__name__)


with open("data.json", "r") as file:
    data_dict = json.load(file)

known_face_encodings = []
known_face_names = []



# Convert the values back to NumPy arrays in the dictionary
for key, value in data_dict.items():
    data_dict[key] = np.array(value)
    known_face_encodings.append(value)
    known_face_names.append(key)
    
#recording settings

print(os.path.dirname(__file__))
fps = 30.0

camera = cv2.VideoCapture(0)

def cctv_capture_frame():
    date_time  = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
    filename = os.path.join(os.path.dirname(__file__), 'static/captures/capture_' + date_time + '.png')
    status, frame = camera.read()
    frame = cv2.flip(frame, 1)
    
    cv2.imwrite(filename, frame)
   
def cctv_feed():
    
    while True:
        # get camera frames
        status, frame = camera.read()
        frame = cv2.flip(frame, 1)
        if not status:
            break

        ret, buff = cv2.imencode('.jpg', frame)
        frame = buff.tobytes()
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def cctv_record():
    date_time  = datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")
    filename = os.path.join(os.path.dirname(__file__), 'static/video/video_' + date_time + '.avi')
    
    print(os.path.dirname(__file__))

   
    frame_width = int(camera.get(3))
    frame_height = int(camera.get(4))
    
    size = (frame_width, frame_height)
    result = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), fps, size)

    while True:
        # get camera frames
        global frame
        status, frame = camera.read()
        frame = cv2.flip(frame, 1)
        if not status:
            break
       
        result.write(frame)
       
       

        #result.release()
     
# Create a thread for the infinite_loop function

            
            




def video_feed():
    camera = cv2.VideoCapture(0)

    process_this_frame = 0

    while True:
        # get camera frames
        status, frame = camera.read()
        frame = cv2.flip(frame, 1)
        global name 
        name= "-"

        if not status:
            break
        else:

            if process_this_frame == 0:
                # Resize frame of video to 1/4 size for faster face recognition processing
                small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
                # Convert the image from BGR color (which OpenCV uses) to RGB color (which face_recognition uses)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                # Only process every other frame of video to save time

                # Find all the faces and face encodings in the current frame of video
                face_locations = face_recognition.face_locations(rgb_small_frame, model="hog")
                face_encodings = face_recognition.face_encodings(rgb_small_frame, known_face_locations=face_locations, model="small")
                face_names = []
                for face_encoding in face_encodings:
                    # See if the face is a match for the known face(s)
                    matches = face_recognition.compare_faces(
                        known_face_encodings, face_encoding)
                    
                    # Or instead, use the known face with the smallest distance to the new face
                    face_distances = face_recognition.face_distance(
                        known_face_encodings, face_encoding)
                    best_match_index = np.argmin(face_distances)
                    # Threshold for similar looking people
                    if face_distances[best_match_index] >= 0.55 :
                        name="Unknown"
                    elif matches[best_match_index]:
                        name = known_face_names[best_match_index]
                        #print(name, " " , np.min(face_distances))

                    face_names.append(name)
                    
                    write_name()
                    
                    
            process_this_frame = (process_this_frame + 1) % 10

            # Display the results
            for (top, right, bottom, left), name in zip(face_locations, face_names):
                # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4

                # Draw a box around the face
                cv2.rectangle(frame, (left, top),
                              (right, bottom), (0, 0, 255), 2)

                # Draw a label with a name below the face
                cv2.rectangle(frame, (left, bottom - 35),
                              (right, bottom), (0, 0, 255), cv2.FILLED)
                font = cv2.FONT_HERSHEY_DUPLEX
                cv2.putText(frame, name, (left + 6, bottom - 6),
                            font, 1.0, (255, 255, 255), 1)

        ret, buff = cv2.imencode('.jpg', frame)
        frame = buff.tobytes()
        yield(b'--frame\r\n'
              b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


# For template
@app.route('/')
def welcome():
    return render_template('index.html')

# For video feed
@app.route('/video')
def video():
    return Response(video_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')

# For cctv view
@app.route('/cctv', methods=['GET', 'POST'])
def cctv():
    global thread
    record_status = ' '
    record_status= request.form.get('status')
    print(record_status)

     
    if(record_status == 'true'):
        thread.start()
    else:
        print('sdfgsdfsdf sdf sf sf')
        try:
            thread_id = thread.ident
            if thread_id is not None:
                thread_id = ctypes.c_long(thread_id)
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(KeyboardInterrupt))
        except:
            print("Exception")
        finally:
            thread = threading.Thread(target=cctv_record)         
        
    return render_template('cctv.html')


@app.route('/cctv_capture', methods=['GET', 'POST'])
def cctv_capture():
    print("Capture")
    cctv_capture_frame()
    return Response("yo")

@app.route('/cctv_view', methods=['GET', 'POST'])
def cctv_view():
    
    cc = cctv_feed()
    return Response(cc, mimetype='multipart/x-mixed-replace; boundary=frame')

# For passing name
@app.route('/write_name', methods=['POST'])
def write_name():
    print(name)

    return Response(name)


@app.route('/store_face_encoding', methods=['POST'])
def store_face_encoding():
    name = request.form.get('name')
    image_data = request.form.get('image_data')

    try:
        # Remove the "data:image/jpeg;base64," prefix
        image_data = image_data.split(",")[1]
        image = PIL.Image.open(io.BytesIO(base64.b64decode(image_data)))
    except Exception as e:
        print("Error decoding image data:", e)
        return "Error decoding image data"

    # Convert PIL Image to numpy array
    np_image = np.array(image)

    # Convert color format from RGB to BGR
    frame = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)

    # Detect face and get face encoding
    face_locations = face_recognition.face_locations(frame)
    face_encodings = face_recognition.face_encodings(frame, face_locations)

    if len(face_encodings) > 0 and name is not None:
        # Assuming only one face is detected
        face_encoding = face_encodings[0]
        data_dict[name] = face_encoding
        known_face_encodings.append(face_encoding)
        known_face_names.append(name)
        for key, value in data_dict.items():
            data_dict[key] = value.tolist()
        with open("data.json", "w") as file:
            json.dump(data_dict, file)
        return "Face encoding stored successfully"
    else:
        return "No face detected"


@app.route('/header')
def header():
    return render_template('header.html')

@app.route('/about')
def about():
    return render_template('aboutus.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port='5050', debug=True)
