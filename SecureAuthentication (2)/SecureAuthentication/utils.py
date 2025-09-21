import numpy as np
from PIL import Image
import io
from deepface import DeepFace

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


def allowed_file(filename):
    if not filename:
        return False
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def image_bytes_to_np(image_bytes):
    """
    Convert raw image bytes to numpy RGB array.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return np.array(img)
    except Exception:
        return None


def image_to_embedding(image_bytes, model_name="VGG-Face"):
    """
    Returns a face embedding (numpy array) or None if no face found.
    DeepFace supports models: VGG-Face, Facenet, OpenFace, DeepFace, ArcFace, Dlib, SFace
    """
    arr = image_bytes_to_np(image_bytes)
    if arr is None:
        return None
    try:
        embeddings = DeepFace.represent(img_path=arr, model_name=model_name, enforce_detection=True)
        if len(embeddings) == 0:
            return None
        return np.array(embeddings[0]["embedding"])
    except Exception:
        return None


def compare_embeddings(a, b):
    """
    Compute Euclidean distance between two embeddings.
    Lower distance = more similar faces.
    """
    a = np.asarray(a)
    b = np.asarray(b)
    return np.linalg.norm(a - b)
