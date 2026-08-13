import logging
import os

import cv2
import rawpy

logger = logging.getLogger(__name__)


def convert_raw_to_jpeg(raw_path):
    try:
        with rawpy.imread(raw_path) as raw:
            rgb = raw.postprocess()
        jpeg_path = raw_path.rsplit('.', 1)[0] + '.jpg'
        cv2.imwrite(jpeg_path, cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        return jpeg_path
    except Exception as e:
        logger.error("RAW conversion error for %s: %s", raw_path, e)
        return None


def detect_faces(image_path):
    """Detect faces in the image and return (count, [(x, y, w, h), ...]).

    The original image is never modified. Two extra artefacts are written
    next to it:
      - processed_<name>: a copy with green boxes drawn around faces
      - faces/<base>_face_<i>.jpg: a crop of each face, used by the
        tag-faces page as thumbnails
    """
    img = cv2.imread(image_path)
    if img is None:
        logger.warning("Could not read image for face detection: %s",
                       image_path)
        return 0, []

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

    folder = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    base = filename.rsplit('.', 1)[0]

    # Save a crop of each face for the tagging page
    faces_dir = os.path.join(folder, 'faces')
    os.makedirs(faces_dir, exist_ok=True)
    for i, (x, y, w, h) in enumerate(faces):
        crop = img[y:y + h, x:x + w]
        cv2.imwrite(os.path.join(faces_dir, f'{base}_face_{i}.jpg'), crop)

    # Save an annotated copy with green boxes; the original stays untouched
    annotated = img.copy()
    for (x, y, w, h) in faces:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    cv2.imwrite(os.path.join(folder, 'processed_' + filename), annotated)

    face_list = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]
    return len(faces), face_list
