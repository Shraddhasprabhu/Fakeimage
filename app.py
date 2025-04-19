import streamlit as st
from PIL import Image
from stegano import lsb
import os
import sqlite3
from datetime import datetime

# =======================
# DATABASE SETUP
# =======================
conn = sqlite3.connect("image_crypto.db", check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS embedded_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_name TEXT,
    secret_message TEXT,
    image_path TEXT,
    timestamp TEXT
)''')

c.execute('''CREATE TABLE IF NOT EXISTS detection_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image1_name TEXT,
    image2_name TEXT,
    result TEXT,
    timestamp TEXT
)''')

conn.commit()

# =======================
# STREAMLIT UI SETUP
# =======================
st.set_page_config(page_title="Crypto Image Checker", layout="centered")
st.title("🔐 Crypto Image Authenticity Tool")

st.sidebar.title("🔧 Options")
mode = st.sidebar.radio("Choose an action:", ["📝 Embed Secret in Image", "🔍 Detect Real vs Fake", "📜 View History"])

# =======================
# 1️⃣ EMBED SECRET
# =======================
if mode == "📝 Embed Secret in Image":
    st.header("📝 Embed a Secret Message")

    embed_image = st.file_uploader("Upload an image (PNG only)", type=["png"], key="embed_img")
    secret_text = st.text_input("Enter the secret message to embed")

    if embed_image and secret_text:
        if st.button("🧬 Embed Message"):
            original = Image.open(embed_image)
            original_path = "uploaded_to_embed.png"
            original.save(original_path)

            encoded_img = lsb.hide(original_path, secret_text)
            saved_path = f"real_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            encoded_img.save(saved_path)

            st.success("✅ Secret embedded successfully!")
            st.image(saved_path, caption="Real Image (with message)", use_column_width=True)

            with open(saved_path, "rb") as f:
                st.download_button("⬇️ Download Embedded Image", data=f, file_name=os.path.basename(saved_path), mime="image/png")

            # Save to database
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO embedded_images (image_name, secret_message, image_path, timestamp) VALUES (?, ?, ?, ?)",
                      (embed_image.name, secret_text, saved_path, timestamp))
            conn.commit()

# =======================
# 2️⃣ DETECT REAL VS FAKE
# =======================
elif mode == "🔍 Detect Real vs Fake":
    st.header("🔍 Detect Real vs Fake Image")

    col1, col2 = st.columns(2)

    with col1:
        img1 = st.file_uploader("Upload Image 1", type=["png", "jpg", "jpeg"], key="img1")
    with col2:
        img2 = st.file_uploader("Upload Image 2", type=["png", "jpg", "jpeg"], key="img2")

    def detect_hidden_message(uploaded_file):
        if uploaded_file:
            image = Image.open(uploaded_file)
            temp_path = "temp_" + uploaded_file.name
            image.save(temp_path)
            try:
                message = lsb.reveal(temp_path)
                os.remove(temp_path)
                return message
            except:
                os.remove(temp_path)
                return None
        return None

    if img1 and img2:
        if st.button("🔎 Check Which is Real"):
            msg1 = detect_hidden_message(img1)
            msg2 = detect_hidden_message(img2)

            col1, col2 = st.columns(2)
            with col1:
                st.image(img1, caption="Image 1", use_column_width=True)
                st.info("✅ Real (message found)" if msg1 else "❌ Fake (no message)")
            with col2:
                st.image(img2, caption="Image 2", use_column_width=True)
                st.info("✅ Real (message found)" if msg2 else "❌ Fake (no message)")

            st.markdown("---")
            st.subheader("🔐 Final Verdict:")

            if msg1 and not msg2:
                result = "Image 1 is Real. Image 2 is Fake."
                st.success(result)
            elif msg2 and not msg1:
                result = "Image 2 is Real. Image 1 is Fake."
                st.success(result)
            elif not msg1 and not msg2:
                result = "Neither image contains a hidden message."
                st.warning(result)
            else:
                result = "Both images may contain a message. Possibly both Real."
                st.info(result)

            # Save detection to DB
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO detection_logs (image1_name, image2_name, result, timestamp) VALUES (?, ?, ?, ?)",
                      (img1.name, img2.name, result, timestamp))
            conn.commit()

# =======================
# 3️⃣ VIEW HISTORY
# =======================
elif mode == "📜 View History":
    st.header("📜 Detection and Embedding History")

    st.subheader("🧬 Embedded Image Logs")
    c.execute("SELECT image_name, secret_message, image_path, timestamp FROM embedded_images ORDER BY timestamp DESC")
    embed_data = c.fetchall()
    for row in embed_data:
        st.markdown(f"- **Image**: {row[0]} | 🧾 **Message**: `{row[1]}` | 🕒 {row[3]}")

    st.markdown("---")

    st.subheader("🔍 Detection Logs")
    c.execute("SELECT image1_name, image2_name, result, timestamp FROM detection_logs ORDER BY timestamp DESC")
    detect_data = c.fetchall()
    for row in detect_data:
        st.markdown(f"- **Image 1**: {row[0]} | **Image 2**: {row[1]} | 🕒 {row[3]}<br>📌 **Result**: _{row[2]}_", unsafe_allow_html=True)
