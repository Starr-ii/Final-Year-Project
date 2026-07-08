import cv2
import os
import rawpy
import numpy as np

def convert_raw_to_jpeg(raw_path):
    try:
        with rawpy.imread(raw_path) as raw:
            rgb = raw.postprocess()
        jpeg_path = raw_path.rsplit('.', 1)[0] + '.jpg'
        cv2.imwrite(jpeg_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return jpeg_path
    except Exception as e:
        print(f"RAW conversion error: {e}")
        return None

def detect_faces(image_path):
    img = cv2.imread(image_path)
    print(f"Image loaded: {img is not None}") 
    if img is None:
        return 0, []
    
    print(f"Image shape: {img.shape}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    )

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=10,
        minSize=(80, 80)
    )

    print(f"Faces detected: {len(faces)}")

    # Draw green boxes around detected faces
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # Overwrite original with processed version
    cv2.imwrite(image_path, img)

    # Return face count AND coordinates
    face_list = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
    return len(faces), face_list


   # Save processed image
    # processed_filename = 'processed_' + os.path.basename(image_path)
    # processed_path = os.path.join(
    #     os.path.dirname(image_path), processed_filename)