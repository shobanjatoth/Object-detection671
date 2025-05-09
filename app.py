import os
import streamlit as st
from paddleocr import PaddleOCR
from ultralytics import YOLO
import cv2
import numpy as np
import pandas as pd
from difflib import SequenceMatcher
import base64

# --- Set PaddleOCR Model Cache Directory ---
custom_model_dir = os.path.join(os.getcwd(), 'models')
os.environ['PADDLEOCR_HOME'] = custom_model_dir
os.makedirs(custom_model_dir, exist_ok=True)

# --- PAGE CONFIG ---
st.set_page_config(page_title="Car License Plate Detection", layout="centered")

# --- BASE64 BACKGROUND IMAGE ---
def get_base64_image(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

img_base64 = get_base64_image("assets/car3.jpg")

# --- CUSTOM CSS STYLING ---
st.markdown(f"""
    <style>
    .stApp {{
        background-image: url("data:image/jpg;base64,{img_base64}");
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        color: white;
        font-family: 'Segoe UI', sans-serif;
    }}
    .main-container {{
        background-color: rgba(0, 0, 0, 0.5);
        padding: 50px 40px;
        text-align: center;
        max-width: 600px;
        margin: 100px auto 30px auto;
        border-radius: 12px;
    }}
    .main-title {{
        font-size: 32px;
        font-weight: bold;
        color: #87CEEB;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8);
    }}
    .upload-btn {{
        display: inline-block;
        background-color: #008CFF;
        color: white;
        padding: 10px 30px;
        font-size: 16px;
        border-radius: 6px;
        margin-top: 15px;
        text-decoration: none;
        cursor: pointer;
    }}
    .contact {{
        text-align: center;
        font-size: 16px;
        margin-top: 60px;
        font-weight: bold;
    }}
    .contact a {{
        color: #42A5F5;
        text-decoration: none;
    }}
    div.stButton > button:first-child {{
        background-color: #1E88E5;
        color: white;
        border-radius: 6px;
        padding: 8px 20px;
    }}
    .stFileUploader {{
        background-color: rgba(255, 255, 255, 0.1);
        border: 2px solid #64B5F6;
        border-radius: 10px;
        padding: 10px;
    }}
    .stDataFrame tbody td {{
        background-color: rgba(255, 255, 255, 0.05);
        color: white;
    }}
    </style>
""", unsafe_allow_html=True)

# --- MAIN INTERFACE CONTAINER ---
st.markdown('<div class="main-container">', unsafe_allow_html=True)
st.markdown('<div class="main-title">Car License Plate Detection</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader("", type=["jpg", "jpeg", "png", "bmp", "mp4", "avi", "mov", "mkv"])

if uploaded_file is not None:
    st.markdown('<div class="upload-btn">Uploading...</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# --- Load Models ---
model = YOLO('best.pt')

@st.cache_resource
def load_ocr():
    return PaddleOCR(use_angle_cls=True, lang='en')

ocr = load_ocr()

# Create temp directory if it doesn't exist
os.makedirs("temp", exist_ok=True)

# --- Helper Functions ---
def is_similar(text, seen_texts, threshold=0.85):
    for seen in seen_texts:
        if SequenceMatcher(None, text, seen).ratio() >= threshold:
            return True
    return False

def extract_text_from_region(region, ocr_engine, seen_texts):
    result = ocr_engine.ocr(region, cls=True)
    extracted = []
    if result:
        for line in result:
            if not line:
                continue
            for item in line:
                if item and len(item) == 2:
                    (bbox, (text, conf)) = item
                    if not is_similar(text, seen_texts) and text.strip():
                        seen_texts.add(text)
                        extracted.append({
                            'Detected Text': text,
                            'Confidence': f"{conf * 100:.2f}%"
                        })
    return extracted

def process_image(image_path, output_path):
    image = cv2.imread(image_path)
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = model.predict(image_rgb, device='cpu')

    ocr_data = []
    seen_texts = set()

    for result in results:
        for box in result.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(image_rgb, (x1, y1), (x2, y2), (0, 255, 0), 2)
            roi = image_rgb[y1:y2, x1:x2]
            roi_bgr = cv2.cvtColor(roi, cv2.COLOR_RGB2BGR)
            ocr_data.extend(extract_text_from_region(roi_bgr, ocr, seen_texts))

    cv2.imwrite(output_path, cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR))
    return output_path, ocr_data

def process_media(input_path, output_path):
    ext = os.path.splitext(input_path)[1].lower()
    if ext in ['.jpg', '.jpeg', '.png', '.bmp']:
        return process_image(input_path, output_path)
    elif ext in ['.mp4', '.avi', '.mov', '.mkv']:
        st.warning("⚠️ Video processing is currently not supported.")
        return None, []
    else:
        st.error("❌ Unsupported file type.")
        return None, []

# --- Main Logic ---
if uploaded_file is not None:
    input_path = os.path.join("temp", uploaded_file.name)
    output_path = os.path.join("temp", f"output_{uploaded_file.name}")

    with open(input_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    st.success(f"✅ File saved: {input_path}")
    st.write("🚀 Processing...")

    with st.spinner("Running object detection and OCR..."):
        result_path, ocr_results = process_media(input_path, output_path)

    if result_path and os.path.exists(result_path):
        st.image(result_path, use_container_width=True)

        if ocr_results:
            st.subheader("🔍 Unique OCR Detected Texts")
            df = pd.DataFrame(ocr_results)
            st.dataframe(df)
        else:
            st.info("No text detected.")
    else:
        st.info("📹 Please upload an image file for processing.")

# --- CONTACT INFO ---
st.markdown('<div class="contact">Contact: <a href="mailto:shobanbabujatoth@gmail.com">shobanbabujatoth@gmail.com</a></div>', unsafe_allow_html=True)


