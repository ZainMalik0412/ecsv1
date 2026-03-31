# Face recognition service.
#
# This module implements face detection and recognition using Pillow for image processing
# and a simplified embedding approach. For production, this can be extended with
# more sophisticated ML models.
#
# Key concepts:
# 1. Face Detection: Simple image validation (production would use ML model)
# 2. Face Encoding: Generate embedding vector from image features
# 3. Face Matching: Compare embeddings using cosine similarity
# 4. Storage: Embeddings stored as binary blobs in PostgreSQL (via numpy tobytes/frombuffer)

import base64
import io
import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from scipy.spatial.distance import cosine

from app.config import settings

# Load fast Haar cascade for face detection
# Using alt2 which is optimized for speed while maintaining good accuracy
_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml')

logger = logging.getLogger(__name__)

EMBEDDING_SIZE = 128


def decode_base64_image(image_base64: str) -> Image.Image:
    # Decode a base64-encoded image string to a PIL Image.
    # Supports data URLs (data:image/...;base64,...) and raw base64.
    # Strip data URL prefix if present
    if "," in image_base64:
        image_base64 = image_base64.split(",", 1)[1]
    
    # Decode base64 to bytes
    image_bytes = base64.b64decode(image_base64)
    
    # Open as PIL Image
    image = Image.open(io.BytesIO(image_bytes))
    return image.convert("RGB")


def detect_faces(image: Image.Image) -> List[Tuple[int, int, int, int]]:
    # Detect faces in an image using fast LBP cascade classifier.
    #
    # OPTIMIZED FOR SPEED - processes frames in <50ms for real-time detection:
    # - Uses LBP cascade (3-5x faster than Haar)
    # - Downscales image for faster processing
    # - Aggressive scaleFactor for fewer passes
    # - Single cascade pass (no redundant checks)
    #
    # Returns list of face locations as (top, right, bottom, left) tuples.
    # Convert PIL Image to OpenCV format
    img_array = np.array(image)
    
    # Downscale for faster processing (max 480px width)
    height, width = img_array.shape[:2]
    scale = 1.0
    max_width = 480
    if width > max_width:
        scale = max_width / width
        new_width = max_width
        new_height = int(height * scale)
        img_array = cv2.resize(img_array, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    # Convert to grayscale
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array
    
    # Quick histogram equalization for lighting normalization
    gray = cv2.equalizeHist(gray)
    
    # FAST detection parameters:
    # - scaleFactor=1.15: larger steps = much faster (was 1.05)
    # - minNeighbors=2: lower = catches faces quickly
    # - minSize=(20, 20): lowered from 30 to catch smaller distant faces
    detection_params = {
        'scaleFactor': 1.15,
        'minNeighbors': 2,
        'minSize': (20, 20),
        'flags': cv2.CASCADE_SCALE_IMAGE
    }
    
    # Fast single-pass face detection
    faces = _face_cascade.detectMultiScale(gray, **detection_params)
    
    # Fallback: if no faces found, retry with finer scale (slower but catches
    # small/distant faces that the fast pass misses)
    if len(faces) == 0:
        fallback_params = {
            'scaleFactor': 1.05,
            'minNeighbors': 2,
            'minSize': (15, 15),
            'flags': cv2.CASCADE_SCALE_IMAGE
        }
        faces = _face_cascade.detectMultiScale(gray, **fallback_params)
    
    # Convert to (top, right, bottom, left) format and scale back to original size
    face_locations = []
    for (x, y, w, h) in faces:
        # Scale coordinates back to original image size
        if scale != 1.0:
            x = int(x / scale)
            y = int(y / scale)
            w = int(w / scale)
            h = int(h / scale)
        top = y
        right = x + w
        bottom = y + h
        left = x
        face_locations.append((top, right, bottom, left))
    
    return face_locations


def _non_max_suppression(boxes: List, overlap_thresh: float = 0.3) -> List[Tuple[int, int, int, int]]:
    # Apply non-maximum suppression to remove overlapping face detections.
    # This prevents the same face from being detected multiple times
    # by different cascades.
    if len(boxes) == 0:
        return []
    
    # Convert to numpy array
    boxes_array = np.array([[x, y, x + w, y + h] for (x, y, w, h) in boxes], dtype=np.float32)
    
    # Get coordinates
    x1 = boxes_array[:, 0]
    y1 = boxes_array[:, 1]
    x2 = boxes_array[:, 2]
    y2 = boxes_array[:, 3]
    
    # Calculate areas
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    
    # Sort by bottom-right y coordinate (larger faces tend to be closer)
    indices = np.argsort(y2)
    
    picked = []
    while len(indices) > 0:
        # Pick the last (largest y2) box
        last = len(indices) - 1
        i = indices[last]
        picked.append(i)
        
        # Find overlap with remaining boxes
        xx1 = np.maximum(x1[i], x1[indices[:last]])
        yy1 = np.maximum(y1[i], y1[indices[:last]])
        xx2 = np.minimum(x2[i], x2[indices[:last]])
        yy2 = np.minimum(y2[i], y2[indices[:last]])
        
        # Calculate overlap ratio
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / areas[indices[:last]]
        
        # Remove boxes with high overlap
        indices = np.delete(indices, np.concatenate(([last], np.where(overlap > overlap_thresh)[0])))
    
    # Convert back to (top, right, bottom, left) format
    result = []
    for i in picked:
        x, y, w, h = boxes[i]
        top = y
        right = x + w
        bottom = y + h
        left = x
        result.append((top, right, bottom, left))
    
    return result


def _image_to_embedding(image: Image.Image) -> np.ndarray:
    # Generate a pseudo-embedding from image features.
    # Uses robust image statistics and structural features for face comparison.
    # For production, use a proper face embedding model (e.g., FaceNet, ArcFace).
    # Resize to standard size
    img_resized = image.resize((64, 64))
    img_array = np.array(img_resized, dtype=np.float32) / 255.0
    
    h, w = img_array.shape[:2]
    grid_size = 4
    gh, gw = h // grid_size, w // grid_size
    gray = np.mean(img_array, axis=2)
    
    # Apply histogram equalization on grayscale for lighting robustness
    gray_uint8 = (gray * 255).astype(np.uint8)
    gray_eq = cv2.equalizeHist(gray_uint8).astype(np.float32) / 255.0
    
    features = []
    
    # 1. Mean and std per channel (6 features)
    for c in range(3):
        features.append(img_array[:, :, c].mean())
        features.append(img_array[:, :, c].std())
    
    # 2. Spatial grid means - equalised grayscale (16 features)
    for i in range(grid_size):
        for j in range(grid_size):
            cell = gray_eq[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            features.append(cell.mean())
    
    # 3. Histogram features per channel (24 features)
    for c in range(3):
        hist, _ = np.histogram(img_array[:, :, c].flatten(), bins=8, range=(0, 1))
        features.extend(hist / hist.sum())
    
    # 4. Spatial grid standard deviations - captures texture (16 features)
    for i in range(grid_size):
        for j in range(grid_size):
            cell = gray_eq[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            features.append(cell.std())
    
    # 5. Gradient magnitude in spatial grid - captures edges/structure (16 features)
    gy, gx = np.gradient(gray_eq)
    grad_mag = np.sqrt(gx**2 + gy**2)
    for i in range(grid_size):
        for j in range(grid_size):
            cell = grad_mag[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
            features.append(cell.mean())
    
    # 6. Per-channel spatial grid means - captures colour distribution (48 features)
    for c in range(3):
        ch = img_array[:, :, c]
        for i in range(grid_size):
            for j in range(grid_size):
                cell = ch[i*gh:(i+1)*gh, j*gw:(j+1)*gw]
                features.append(cell.mean())
    
    # 7. Horizontal symmetry + overall brightness (2 features)
    left_half = gray_eq[:, :w//2]
    right_half = np.fliplr(gray_eq[:, w//2:])
    min_w = min(left_half.shape[1], right_half.shape[1])
    features.append(np.mean(np.abs(left_half[:, :min_w] - right_half[:, :min_w])))
    features.append(gray_eq.mean())
    
    # Total: 6 + 16 + 24 + 16 + 16 + 48 + 2 = 128 = EMBEDDING_SIZE
    
    # Pad or truncate to EMBEDDING_SIZE
    embedding = np.array(features[:EMBEDDING_SIZE], dtype=np.float64)
    if len(embedding) < EMBEDDING_SIZE:
        embedding = np.pad(embedding, (0, EMBEDDING_SIZE - len(embedding)))
    
    # Normalize
    norm = np.linalg.norm(embedding)
    if norm > 0:
        embedding = embedding / norm
    
    return embedding


def encode_faces(image: Image.Image, face_locations: Optional[List] = None) -> List[np.ndarray]:
    # Generate face encodings for faces in an image.
    # Returns list of numpy arrays, one per detected face.
    if face_locations is None:
        face_locations = detect_faces(image)
    
    encodings = []
    for (top, right, bottom, left) in face_locations:
        # Crop face region
        face_img = image.crop((left, top, right, bottom))
        encoding = _image_to_embedding(face_img)
        encodings.append(encoding)
    
    return encodings


def encoding_to_bytes(encoding: np.ndarray) -> bytes:
    # Convert a face encoding numpy array to bytes for database storage.
    return encoding.astype(np.float64).tobytes()


def bytes_to_encoding(data: bytes) -> np.ndarray:
    # Convert stored bytes back to a face encoding numpy array.
    return np.frombuffer(data, dtype=np.float64)


def compare_faces(
    known_encodings: List[np.ndarray],
    face_to_check: np.ndarray,
    tolerance: Optional[float] = None,
) -> Tuple[bool, float]:
    # Compare a face encoding against a list of known encodings.
    # Uses cosine similarity for comparison.
    # Returns (matched: bool, confidence: float).
    if tolerance is None:
        tolerance = settings.FACE_RECOGNITION_TOLERANCE
    
    if not known_encodings:
        return False, 0.0
    
    # Calculate cosine similarities
    similarities = []
    for known in known_encodings:
        sim = 1 - cosine(known, face_to_check)
        similarities.append(sim)
    
    best_similarity = max(similarities)
    
    # Convert tolerance (distance-based) to similarity threshold
    # tolerance of 0.6 means distance <= 0.6, so similarity >= 0.4
    similarity_threshold = 1 - tolerance
    matched = best_similarity >= similarity_threshold
    
    # Confidence is the similarity score
    confidence = max(0.0, min(1.0, best_similarity))
    
    return matched, confidence


def extract_and_encode_face(image_base64: str) -> Tuple[Optional[np.ndarray], str]:
    # Extract and encode a face from a base64 image.
    # Returns (encoding, message).
    # If no face or multiple faces found, returns (None, error_message).
    try:
        image = decode_base64_image(image_base64)
    except Exception as e:
        return None, f"Failed to decode image: {str(e)}"
    
    face_locations = detect_faces(image)
    
    if len(face_locations) == 0:
        return None, "No face detected in image"
    
    if len(face_locations) > 1:
        return None, f"Multiple faces detected ({len(face_locations)}). Please provide an image with a single face."
    
    encodings = encode_faces(image, face_locations)
    if not encodings:
        return None, "Failed to generate face encoding"
    
    return encodings[0], "Success"


def extract_all_faces(image_base64: str) -> Tuple[List[Tuple[np.ndarray, Tuple[int, int, int, int]]], str]:
    # Extract and encode ALL faces from a base64 image (for live recognition).
    #
    # Returns (list of (encoding, face_location) tuples, message).
    # Each face_location is (top, right, bottom, left) for drawing bounding boxes.
    # Used by lecturers during live sessions to detect multiple students.
    # Uses OpenCV Haar cascade for accurate face-only detection.
    try:
        image = decode_base64_image(image_base64)
    except Exception as e:
        return [], f"Failed to decode image: {str(e)}"
    
    width, height = image.size
    
    if width < 50 or height < 50:
        return [], "Image too small"
    
    # Detect faces using OpenCV Haar cascade - only detects actual faces
    face_locations = detect_faces(image)
    
    if len(face_locations) == 0:
        return [], "No faces detected"
    
    logger.debug(f"Detected {len(face_locations)} face(s) in {width}x{height} image")
    
    # Return encodings paired with their face locations for bounding box display
    encodings = encode_faces(image, face_locations)
    results = list(zip(encodings, face_locations))
    return results, f"Detected {len(results)} face(s)"


def match_face_to_students(
    face_encoding: np.ndarray,
    student_encodings: List[Tuple[int, str, List[np.ndarray]]],
    tolerance: Optional[float] = None,
) -> Optional[Tuple[int, str, float]]:
    # Match a single face encoding against a list of students' encodings.
    #
    # Args:
    #     face_encoding: The encoding to match
    #     student_encodings: List of (student_id, student_name, [encodings])
    #
    # Returns:
    #     (student_id, student_name, confidence) if matched, None otherwise
    if tolerance is None:
        tolerance = settings.FACE_RECOGNITION_TOLERANCE
    
    ABSOLUTE_MIN_CONFIDENCE = 0.55
    MIN_CONFIDENCE_GAP = 0.08

    best_match = None
    best_confidence = 0.0
    second_best_confidence = 0.0
    
    for student_id, student_name, encodings in student_encodings:
        if not encodings:
            continue
        
        matched, confidence = compare_faces(encodings, face_encoding, tolerance)
        if matched and confidence > best_confidence:
            second_best_confidence = best_confidence
            best_match = (student_id, student_name, confidence)
            best_confidence = confidence
        elif matched and confidence > second_best_confidence:
            second_best_confidence = confidence
    
    if best_match is None:
        return None

    # Hard floor: reject matches below absolute minimum confidence
    if best_confidence < ABSOLUTE_MIN_CONFIDENCE:
        return None

    # Ambiguity check: reject if gap between best and second-best is too small
    if second_best_confidence > 0 and (best_confidence - second_best_confidence) < MIN_CONFIDENCE_GAP:
        return None

    return best_match
