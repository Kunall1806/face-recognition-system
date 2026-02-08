# Final Advanced Code V8 for Kunal (Fully Repaired)
import face_recognition
import cv2
import numpy as np
import os  # <-- YEH LINE THEEK KAR DI GAYI HAI
from datetime import datetime
import sqlite3
import platform
import subprocess
from deepface import DeepFace
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import time
import threading

# --- HINDI VOICE FEATURE LIBRARIES ---
from gtts import gTTS
from playsound import playsound
import speech_recognition as sr

# --- Settings and Configuration ---
KNOWN_FACES_DIR = 'known_faces'
DB_FILE = 'attendance.db'
RECOGNITION_TOLERANCE = 0.55
RESIZE_FACTOR = 0.5

# --- Aapke Naam ki Setting ---
AUTHORIZED_USER_FOR_UNLOCK = "kunal" 
PATH_TO_UNLOCK = "/Users/kunal/Desktop/MySecrets.txt"

# --- EMAIL ALERT KI SETTING ---
EMAIL_SENDER = "rana87891bth@gmail.com"
EMAIL_PASSWORD = "jqcx mcnf tnuq bjgq"
EMAIL_RECEIVER = "kunalrajput70047@gmail.com"

# --- HINDI VOICE FEATURE: TTS FUNCTION ---
def speak(text):
    print(f"System bol raha hai: {text}")
    try:
        tts = gTTS(text=text, lang='hi')
        speech_file = 'speech.mp3'
        tts.save(speech_file)
        playsound(speech_file)
        os.remove(speech_file)
    except Exception as e:
        print(f"Bolne mein error aaya: {e}")

def start_conversation(name):
    speak(f"Namaste {name}, kaise ho aap?")
    
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Suna jaa raha hai... (kuch boliye)")
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
        try:
            audio = r.listen(source, timeout=5, phrase_time_limit=5)
        except sr.WaitTimeoutError:
            print("Sunna band kar diya, koi aawaz nahi aayi.")
            return

    try:
        print("Samjha jaa raha hai...")
        user_text = r.recognize_google(audio, language='en-in')
        print(f"Aapne kaha: {user_text}")
        
        if 'fine' in user_text.lower() or 'good' in user_text.lower() or 'theek' in user_text.lower() or 'badhiya' in user_text.lower():
            speak("Yeh sunkar accha laga!")
        else:
            speak("Samajh gaya. Aapka din accha beete.")
            
    except Exception as e:
        print(f"Maaf kijiye, main samajh nahi paaya. Error: {e}")
        speak("Maaf kijiye, main samajh nahi paaya.")

def setup_database():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS attendance (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, date TEXT, time TEXT)''')
    conn.commit()
    conn.close()

def send_email_alert(image_path):
    # --- YEH FUNCTION AB POORA KAR DIYA GAYA HAI ---
    print("Stranger alert bhejne ki koshish...")
    try:
        msg = MIMEMultipart(); msg['From'] = EMAIL_SENDER; msg['To'] = EMAIL_RECEIVER
        msg['Subject'] = "Security Alert: Unknown Person Detected!"
        msg.attach(MIMEText("An unknown person was detected. Photo is attached.", 'plain'))
        with open(image_path, 'rb') as f: img = MIMEImage(f.read(), name=os.path.basename(image_path))
        msg.attach(img)
        server = smtplib.SMTP('smtp.gmail.com', 587); server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string()); server.quit()
        print("Alert email safalta se bhej diya gaya!")
        return True
    except Exception as e:
        print(f"Email nahi bhej paaye. Error: {e}"); return False

def mark_attendance_in_db(name):
    now = datetime.now()
    date_string = now.strftime('%Y-%m-%d')
    time_string = now.strftime('%I:%M:%S %p')
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE name=? AND date=?", (name, date_string))
    entry = cursor.fetchone()
    if entry:
        # Agar entry pehle se hai, toh time UPDATE karein
        cursor.execute("UPDATE attendance SET time = ? WHERE name = ? AND date = ?", (time_string, name, date_string))
    else:
        # Agar entry nahi hai, toh nayi entry INSERT karein
        cursor.execute("INSERT INTO attendance (name, date, time) VALUES (?, ?, ?)", (name, date_string, time_string))
        print(f"Attendance marked for {name} in Database")
    conn.commit()
    conn.close()

def get_last_seen(name):
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("SELECT date, time FROM attendance WHERE name = ? ORDER BY id DESC LIMIT 1", (name,))
        result = cursor.fetchone()
        conn.close()
        if result: return f"Last seen: {result[0]} at {result[1]}"
        else: return "First time seen!"
    except Exception as e:
        return ""

def get_gaze_direction(landmarks):
    try:
        left_eye_points = landmarks['left_eye']; right_eye_points = landmarks['right_eye']; nose_bridge = landmarks['nose_bridge']
        left_eye_center = np.mean(left_eye_points, axis=0); right_eye_center = np.mean(right_eye_points, axis=0)
        nose_tip = nose_bridge[0]
        if (right_eye_center[0] - left_eye_center[0]) == 0: return "Center"
        horizontal_ratio = (nose_tip[0] - left_eye_center[0]) / (right_eye_center[0] - left_eye_center[0])
        if horizontal_ratio < 0.4: return "Looking Left"
        elif horizontal_ratio > 0.6: return "Looking Right"
        else: return "Looking Center"
    except:
        return ""

def open_file(filepath):
    try: subprocess.run(["open", filepath], check=True); return True
    except: return False

print("Known faces ko load kiya ja raha hai...")
known_face_encodings = []
known_face_names = []
def load_known_faces():
    global known_face_encodings, known_face_names
    known_face_encodings = []
    known_face_names = []
    for filename in os.listdir(KNOWN_FACES_DIR):
        if filename.startswith('.'): continue
        image_path = os.path.join(KNOWN_FACES_DIR, filename)
        try:
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(os.path.splitext(filename)[0])
        except Exception as e:
            print(f"Warning: {filename} ko load nahi kar paaye. Error: {e}")
    print(f"{len(known_face_names)} known faces load ho gaye.")

load_known_faces()
setup_database()

video_capture = cv2.VideoCapture(0)
if not video_capture.isOpened():
    print("CRITICAL ERROR: Webcam nahi mila ya use nahi kar paa rahe. Program band ho raha hai.")
    exit()

results = []
process_this_frame = True
faces_welcomed_this_session = set()
unlock_action_done = False
stranger_detected_time = None
alert_sent = False

print("\nAdvanced System V8 (Repaired) shuru ho gaya hai!")
print("Naya chehra register karne ke liye 'r' dabayein.")
print("Band karne ke liye 'q' key dabayein.")

while True:
    ret, frame = video_capture.read()
    if not ret: break

    if process_this_frame:
        results_this_frame = []
        small_frame = cv2.resize(frame, (0, 0), fx=RESIZE_FACTOR, fy=RESIZE_FACTOR)
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])
        
        face_locations = face_recognition.face_locations(rgb_small_frame)
        face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
        face_landmarks_list = face_recognition.face_landmarks(rgb_small_frame, face_locations)

        for i, face_encoding in enumerate(face_encodings):
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=RECOGNITION_TOLERANCE)
            name, emotion, gaze, last_seen = "Unknown", "", "", ""
            
            if True in matches: name = known_face_names[matches.index(True)]
            
            face_roi = frame[int(face_locations[i][0]/RESIZE_FACTOR):int(face_locations[i][2]/RESIZE_FACTOR), int(face_locations[i][3]/RESIZE_FACTOR):int(face_locations[i][1]/RESIZE_FACTOR)]
            
            if face_roi.size > 0:
                try:
                    analysis = DeepFace.analyze(face_roi, actions=['emotion'], enforce_detection=False, detector_backend='mtcnn')
                    emotion = analysis[0]['dominant_emotion'] if isinstance(analysis, list) else analysis['dominant_emotion']
                except: pass

            gaze = get_gaze_direction(face_landmarks_list[i])
            if name != "Unknown": last_seen = get_last_seen(name)
            
            results_this_frame.append((face_locations[i], name, emotion, gaze, last_seen))
        results = results_this_frame

    process_this_frame = not process_this_frame

    for (top, right, bottom, left), name, emotion, gaze, last_seen in results:
        top, right, bottom, left = int(top/RESIZE_FACTOR), int(right/RESIZE_FACTOR), int(bottom/RESIZE_FACTOR), int(left/RESIZE_FACTOR)
        box_color = (0, 0, 255) # Default red

        if name != "Unknown":
            box_color = (0, 255, 0)
            mark_attendance_in_db(name)
            
            if name not in faces_welcomed_this_session:
                faces_welcomed_this_session.add(name)
                conversation_thread = threading.Thread(target=start_conversation, args=(name,))
                conversation_thread.daemon = True
                conversation_thread.start()

            if name == AUTHORIZED_USER_FOR_UNLOCK and not unlock_action_done:
                if open_file(PATH_TO_UNLOCK): unlock_action_done = True
            
            current_time = datetime.now().strftime('%I:%M:%S %p')
            display_text = f"{name} ({emotion.capitalize()}) {current_time}"
            gaze_text = f"Gaze: {gaze}"
            
            cv2.putText(frame, gaze_text, (left, bottom + 25), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 1)
            cv2.putText(frame, last_seen, (left, bottom + 50), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 255, 0), 1)
            stranger_detected_time = None; alert_sent = False
        else:
            display_text = "Unknown"
            # --- EMAIL ALERT LOGIC AB YAHAAN HAI ---
            if stranger_detected_time is None: stranger_detected_time = time.time()
            elif (time.time() - stranger_detected_time) > 2 and not alert_sent:
                stranger_photo_path = "stranger.jpg"
                cv2.imwrite(stranger_photo_path, frame)
                threading.Thread(target=send_email_alert, args=(stranger_photo_path,), daemon=True).start()
                alert_sent = True

        cv2.rectangle(frame, (left, top), (right, bottom), box_color, 2)
        cv2.rectangle(frame, (left, bottom - 35), (right, bottom), box_color, cv2.FILLED)
        cv2.putText(frame, display_text, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.7, (255, 255, 255), 1)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        # --- LIVE REGISTRATION FEATURE AB YAHAAN HAI ---
        new_name = input("\nTerminal mein naye insaan ka naam daalein aur Enter dabayein: ")
        if new_name:
            img_path = os.path.join(KNOWN_FACES_DIR, f"{new_name}.jpg")
            cv2.imwrite(img_path, frame)
            print(f"{new_name} ki photo save ho gayi! System ko update kiya ja raha hai...")
            load_known_faces() # Naye chehre ko live load karein

    cv2.imshow('Advanced System V8 (Repaired)', frame)

video_capture.release()
cv2.destroyAllWindows()
print("System band ho gaya.")