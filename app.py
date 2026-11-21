import html
import hashlib
import json
import mimetypes
import re
from pathlib import Path
import streamlit as st
import uuid
from database import (
 add_message,
 create_chat,
 delete_chat,
 get_all_chats,
 get_messages,
 init_database,
 rename_chat,
 create_user, authenticate_user,
)
from services.file_service import (
 read_document_bytes,
 save_image_bytes,
 save_uploaded_file,
)
from services.gemini_service import generate_text, safe_generate_text, safe_analyze_audio
from services.image_service import analyze_image, edit_image, generate_image

# ==================================================
# CONFIGURATION + AUTHENTICATION

# ==================================================
st.set_page_config(page_title="Multimind AI", page_icon="✨", layout="wide")
PROJECT_DIR = Path(__file__).resolve().parent
STORAGE_ROOT = PROJECT_DIR / "user_data"
init_database()
if "auth_user" not in st.session_state:
 st.session_state.auth_user = None
if "guest_mode" not in st.session_state:
 st.session_state.guest_mode = False
if not st.session_state.auth_user and not st.session_state.guest_mode:
 st.markdown("<h1 style='text-align:center;'>✨ Multimind AI</h1>", unsafe_allow_html=True)
 st.markdown("<h3 style='text-align:center;'>Hoş geldin! Devam etmek için giriş yap.</h3>", unsafe_allow_html=True)
 login_tab, signup_tab = st.tabs(["Giriş Yap", "Kayıt Ol"])
 with login_tab:
     with st.form("login_form"):
         login_username = st.text_input("Kullanıcı adı")
         login_password = st.text_input("Şifre", type="password")
         login_submit = st.form_submit_button("Giriş Yap", use_container_width=True)
     if login_submit:
         account = authenticate_user(login_username, login_password)
         if account:
             st.session_state.auth_user = account
             st.session_state.guest_mode = False
             st.rerun()
         else:
             st.error("Kullanıcı adı veya şifre hatalı.")
 with signup_tab:
     with st.form("signup_form"):
         signup_username = st.text_input("Kullanıcı adı (en az 3 karakter)")
         signup_password = st.text_input("Şifre (en az 8 karakter)", type="password")
         signup_password_confirm = st.text_input("Şifre tekrar", type="password")
         signup_submit = st.form_submit_button("Hesap Oluştur", use_container_width=True)
     if signup_submit:
         if len(signup_username.strip()) < 3:
             st.error("Kullanıcı adı en az 3 karakter olmalı.")
         elif len(signup_password) < 8:
             st.error("Şifre en az 8 karakter olmalı.")
         elif signup_password != signup_password_confirm:
             st.error("Şifreler eşleşmiyor.")
         elif create_user(signup_username, signup_password):
             st.success("Hesabın oluşturuldu. Giriş sekmesinden giriş yapabilirsin.")
         else:
             st.error("Bu kullanıcı adı zaten alınmış.")
 st.divider()
 if st.button("Hesap olmadan devam et", use_container_width=True):
     st.session_state.guest_mode = True
     st.rerun()
 st.stop()
IS_GUEST = bool(st.session_state.guest_mode)
OWNER_ID = st.session_state.auth_user["id"] if st.session_state.auth_user else None
STORAGE_KEY = f"user_{OWNER_ID}" if OWNER_ID is not None else f"guest_{st.session_state.get('guest_storage_key', '')}"
if IS_GUEST and not st.session_state.get("guest_storage_key"):
 st.session_state.guest_storage_key = uuid.uuid4().hex
 STORAGE_KEY = f"guest_{st.session_state.guest_storage_key}"
USER_DIR = STORAGE_ROOT / STORAGE_KEY
UPLOAD_DIR = USER_DIR / "uploads"
GENERATED_DIR = USER_DIR / "generated_images"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
SUPPORTED_TYPES = ["pdf", "txt", "docx", "png", "jpg", "jpeg", "webp", "mp3", "wav", "m4a", "aac", "ogg", "flac"]
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
DOCUMENT_EXTENSIONS = {".txt", ".pdf", ".docx"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

# ==================================================
# SESSION STATE

# ==================================================
for key, default in {
 "messages": [], "chats": {}, "chat_ids": {}, "current_chat": None,
 "session_initialized": False, "voice_processing_error": None,}.items():
 if key not in st.session_state:
     st.session_state[key] = default

def refresh_chat_index():
 st.session_state.chats = {}
 st.session_state.chat_ids = {}
 if IS_GUEST:
     for name in st.session_state.get("guest_chats", {}):
         st.session_state.chats[name] = []
         st.session_state.chat_ids[name] = name
 else:
     for chat in get_all_chats(OWNER_ID):
         st.session_state.chats[chat["name"]] = []
         st.session_state.chat_ids[chat["name"]] = chat["id"]

def load_chat_into_session(chat_name: str):
 chat_id = st.session_state.chat_ids[chat_name]
 if IS_GUEST:
     st.session_state.current_chat = chat_name
     st.session_state.messages = st.session_state.guest_chats.get(chat_name, [])
     return
 rows = get_messages(chat_id, OWNER_ID)
 messages = []
 for row in rows:
     item = {"role": row["role"], "content": row["content"], "attachments": []}
     if row["attachment_json"]:
         try: item["attachments"] = json.loads(row["attachment_json"])
         except (TypeError, json.JSONDecodeError): item["attachments"] = []
     elif row["attachment_path"]:
         item["attachments"] = [{"path": row["attachment_path"], "name": row["attachment_name"] or Path(row["attachment_path"]).name, "type": row["attachment_type"] or "file"}]
     messages.append(item)
 st.session_state.current_chat = chat_name
 st.session_state.messages = messages
if not st.session_state.chats:
 refresh_chat_index()

def start_new_chat():
 number = 1
 name = f"Yeni Sohbet {number}"
 while name in st.session_state.chats:
     number += 1
     name = f"Yeni Sohbet {number}"
 if IS_GUEST:
     chat_id = name
     st.session_state.setdefault("guest_chats", {})[name] = []
 else:
     chat_id = create_chat(name, OWNER_ID)
 st.session_state.chats[name] = []
 st.session_state.chat_ids[name] = chat_id
 st.session_state.current_chat = name
 st.session_state.messages = []
if not st.session_state.session_initialized:
 start_new_chat()
 st.session_state.session_initialized = True

def save_message(role, content, attachments=None):
 chat_name = st.session_state.current_chat
 chat_id = st.session_state.chat_ids[chat_name]
 attachments = attachments or []
 message = {"role": role, "content": content, "attachments": attachments}
 st.session_state.messages.append(message)
 if IS_GUEST:
     st.session_state.setdefault("guest_chats", {})[chat_name] = st.session_state.messages
 else:
     first_attachment = attachments[0] if attachments else {}
     add_message(chat_id, OWNER_ID, role, content,
                attachment_path=first_attachment.get("path"), attachment_name=first_attachment.get("name"),
                attachment_type=first_attachment.get("type"),
                attachment_json=json.dumps(attachments, ensure_ascii=False) if attachments else None)
 if role == "user":
     user_message_count = sum(1 for item in st.session_state.messages if item["role"] == "user")
     if user_message_count == 1:
         old_name = chat_name
         content_lines = content.strip().splitlines()
         base_name = (content_lines[0][:40] if content_lines else "Sesli Mesaj") or "Yeni Sohbet"
         new_name = base_name
         suffix = 2
         while new_name in st.session_state.chats and new_name != old_name:
             new_name = f"{base_name} ({suffix})"; suffix += 1
         if IS_GUEST:
             st.session_state.guest_chats[new_name] = st.session_state.guest_chats.pop(old_name)
         else:
             rename_chat(chat_id, OWNER_ID, new_name)
         st.session_state.chats[new_name] = st.session_state.chats.pop(old_name)
         st.session_state.chat_ids[new_name] = st.session_state.chat_ids.pop(old_name)
         st.session_state.current_chat = new_name

def get_chat_file_context():
 """Collect user uploads and assistant-generated images from this chat."""
 documents = []
 images = []
 audios = []
 seen_paths = set()
 for message in st.session_state.messages:
     role = message.get("role")
     for attachment in message.get("attachments", []):
         path_value = attachment.get("path")
         if not path_value:
             continue
         attachment_type = attachment.get("type", "")
         is_generated_image = attachment_type == "generated_image"
         if role != "user" and not (role == "assistant" and is_generated_image):
             continue
         path = Path(path_value)
         path_key = str(path.resolve())
         if path_key in seen_paths or not path.is_file():
             continue
         seen_paths.add(path_key)
         suffix = path.suffix.lower()
         name = attachment.get("name", path.name)
         if role == "user" and suffix in DOCUMENT_EXTENSIONS:
             extracted_text = attachment.get("extracted_text")
             if extracted_text is None:
                 extracted_text = read_document_bytes(name, path.read_bytes())
             if extracted_text.strip():
                 documents.append((name, extracted_text))
         elif suffix in IMAGE_EXTENSIONS or is_generated_image:
             mime_type = attachment.get("type") if attachment.get("type", "").startswith("image/") else None
             mime_type = mime_type or mimetypes.guess_type(name)[0] or "image/png"
             images.append((path.read_bytes(), mime_type, name))
         elif role == "user" and suffix in AUDIO_EXTENSIONS:
             mime_type = attachment.get("type") or mimetypes.guess_type(name)[0] or "audio/mpeg"
             audios.append((path.read_bytes(), mime_type, name))
 return documents, images, audios

def detect_image_generation_request(user_text: str) -> bool:
    """Detect image-generation intent from flexible natural-language requests."""
    text = user_text.lower().strip()
    if not text:
        return False


    # Keep this subject-agnostic: the user can request any scene or object.
    # Match Turkish suffixes (e.g. "görseli", "resim oluşturur musun") by
    # checking stems rather than requiring exact whole-word matches.
    image_terms = (
        "görsel", "res", "fotoğraf", "fotograf", "illustrasyon",
        "illüstrasyon", "image", "picture", "photo", "illustration",
        "artwork", "art", "poster", "wallpaper",
    )
    creation_terms = (
        "oluştur", "olustur", "üret", "uret", "yarat", "create", "generate",
        "make", "render",
    )
    drawing_terms = ("çiz", "ciz", "draw", "sketch", "paint", "resmet", "illustrate")

    has_image_term = any(term in text for term in image_terms)
    has_creation_term = any(term in text for term in creation_terms)
    has_drawing_term = any(term in text for term in drawing_terms)


    # Image noun + creation verb in any order, including Turkish suffixes.
    if has_image_term and (has_creation_term or has_drawing_term):
        return True


    # Natural requests such as "bana bir kedi çiz" / "draw a cat" need not
    # contain the word image or picture.
    if has_drawing_term:
        return True


    # Explicit prompt labels and common English image-generation phrasing.
    if re.search(r"(?:^|\n)\s*(?:\*\*)?\s*(?:image\s+)?prompt\s*:", text):
        return True
    prompt_phrases = (
        "prompt ile oluştur", "promptla oluştur", "prompt ile üret", "promptla üret",
        "bunu görsele dönüştür", "görsele dönüştür", "resme dönüştür",
        "generate from this prompt", "turn this into an image", "visual version of this",
        "create a visual", "make it visual", "as an image", "in image form",
    )
    return any(phrase in text for phrase in prompt_phrases)

def detect_image_edit_request(user_text: str) -> bool:
 """Detect general follow-up instructions that ask to change an existing image."""
 text = user_text.lower().strip()
 direct_edit_phrases = [
     "rengini", "renklerini", "yap", "olsun", "olsunlar", "görünsün",
     "görmek istiyorum", "yer alsın", "bulunsun", "dahil et", "ekle",
     "kaldır", "sil", "değiştir", "düzenle", "arka planı değiştir",
     "arka planını değiştir", "arka planı sil", "arka planını sil",
     "fotoğrafı düzenle", "görseli düzenle", "resmi düzenle",
     "haline getir", "dönüştür", "make it", "change the", "remove the",
     "add a", "edit this", "edit the image", "change its",
 ]
 return any(phrase in text for phrase in direct_edit_phrases)

def render_message(message, index):
 role = message["role"]
 content = message["content"]
 attachments = message.get("attachments", [])
 if role == "user":
     if content.strip():
         safe = html.escape(content).replace("\n", "<br>")
         st.markdown(
             f"""<div style="display:flex;justify-content:flex-end;width:100%;margin:18px 0;">
             <div style="background:#713D61;color:white;padding:12px 20px;border-radius:22px;
             max-width:78%;overflow-wrap:anywhere;font-size:16px;">{safe}</div></div>""",
             unsafe_allow_html=True,
         )
 else:
     st.markdown(content)
 for attachment_index, attachment in enumerate(attachments):
     path = Path(attachment.get("path", ""))
     if not path.is_file():
         continue
     file_type = attachment.get("type", "")
     if file_type.startswith("image/") or file_type == "generated_image":
         st.image(str(path), caption=attachment.get("name", "Görsel"), use_container_width=True)
         st.download_button(
             "⬇️ Görseli indir",
             data=path.read_bytes(),
             file_name=attachment.get("name", path.name),
             mime=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
             key=f"download_{st.session_state.current_chat}_{index}_{attachment_index}",
         )
     else:
         st.caption(f"📎 {attachment.get('name', path.name)}")

# ==================================================
# SIDEBAR

# ==================================================
with st.sidebar:
 st.title("✨ Multimind AI")
 st.caption("Yapay zekâ destekli kişisel asistanın")
 st.caption("Misafir modu — sohbetler bu oturumda tutulur" if IS_GUEST else "Kullanıcı: " + st.session_state.auth_user["username"])
 if st.button("🚪 Çıkış / Oturumu kapat", use_container_width=True):
     if IS_GUEST:
         import shutil
         shutil.rmtree(USER_DIR, ignore_errors=True)
     for key in list(st.session_state.keys()):
         del st.session_state[key]
     st.rerun()
 st.divider()
 if st.button("➕ Yeni Sohbet", use_container_width=True):
     start_new_chat()
     st.rerun()
 st.divider()
 st.subheader("🚀 Neler yapabilirim?")
 for feature in [
     "📝 Metin oluşturma ve düzenleme",
     "📌 Metin özetleme ve çeviri",
     "💡 İçerik fikri üretme",
     "🎨 Cloudflare ile görsel üretme",
     "🖼️ Cloudflare ile görsel analizi",
     "📂 TXT, PDF ve DOCX analizi",
     "📎 Birden fazla dosya yükleme",
     "🎧 Ses dosyası yükleme ve Gemini ile analiz",
 ]:
     st.caption(feature)
 st.divider()
 st.subheader("💬 Chat History")
 for chat_index, chat_name in enumerate(list(st.session_state.chats.keys())):
     chat_id = st.session_state.chat_ids[chat_name]
     col_open, col_delete = st.columns([5, 1])
     with col_open:
         if st.button(f"💬 {chat_name}", key=f"open_{chat_index}_{chat_id}", use_container_width=True):
             load_chat_into_session(chat_name)
             st.rerun()
     with col_delete:
         if st.button("🗑️", key=f"delete_{chat_index}_{chat_id}"):
             if IS_GUEST:
                 st.session_state.guest_chats.pop(chat_name, None)
             else:
                 delete_chat(chat_id, OWNER_ID)
             st.session_state.chats.pop(chat_name, None)
             st.session_state.chat_ids.pop(chat_name, None)
             if st.session_state.current_chat == chat_name:
                 if st.session_state.chats:
                     load_chat_into_session(next(iter(st.session_state.chats)))
                 else:
                     start_new_chat()
             st.rerun()
 st.divider()

# ==================================================
# MAIN CHAT

# ==================================================
st.markdown(
 "<h1 style='text-align:center;margin-bottom:36px;'>✨ Multimind AI</h1>",
 unsafe_allow_html=True,
)
if not st.session_state.messages:
 st.markdown(
     "<h3 style='text-align:center;'>Bugün sana nasıl yardımcı olabilirim?</h3>",
     unsafe_allow_html=True,
 )
 st.markdown(
     "<p style='text-align:center;color:#999;'>Metin, belge, görsel ve ses dosyalarıyla çalışabilirsin.</p>",
     unsafe_allow_html=True,
 )
for message_index, message in enumerate(st.session_state.messages):
 render_message(message, message_index)
if st.session_state.get("voice_processing_error"):
 st.error(st.session_state.voice_processing_error)

# ==================================================
# CHAT INPUT AND MULTIMODAL ROUTING

# ==================================================
st.markdown(
 """

 <style>

 /* Sidebar genişliğine müdahale ETME: Streamlit doğal resize/collapse davranışı */

 /* Streamlit'in doğal alt composer'ı main alanına göre konumlanır.

    Mikrofon yalnızca sağ kenara sabitlenir; sidebar genişliğini etkilemez. */

 .st-key-mic_toggle_button {

     position: fixed !important;

     right: 5rem !important;

     bottom: 3.5rem !important;

     width: 3.25rem !important;

     z-index: 1001 !important;

     margin: 0 !important;

 }

 .st-key-mic_toggle_button button {

     width: 3.25rem !important;

     height: 3.25rem !important;

     min-height: 3.25rem !important;

     border-radius: 0.9rem !important;

 }

 /* Input, Streamlit'in main alanına göre alt konumlandırmasını korur.

    Sağda mikrofon için küçük yer bırakılır. */

 div[data-testid="stChatInput"] {

     width: calc(100% - 5rem) !important;

     max-width: calc(100% - 5rem) !important;

 }

 /* Alt giriş arkasında sohbet mesajları kalmasın */

 section[data-testid="stMain"] .block-container {

     padding-bottom: 7rem !important;

 }

 @media (max-width: 700px) {
     .st-key-mic_toggle_button {
         right: 0.75rem !important;
         bottom: 1rem !important;
     }
     div[data-testid="stChatInput"] {
         width: calc(100% - 5.25rem) !important;
         max-width: calc(100% - 5.25rem) !important;
         margin-right: 5.25rem !important;
     }
 }

 </style>

 """,
 unsafe_allow_html=True,
)
user_prompt = None
voice_recording = None
mic_clicked = False
# Ses paneli normal akışta chat input'un hemen üstünde gösterilir.
if st.session_state.get("show_mic_recording", False):
 voice_recording = st.audio_input(
     "Ses kaydet",
     key="voice_message_input",
     label_visibility="collapsed"
 )
# st.chat_input: Streamlit'in native fixed-bottom yerleşimi ve main alanı
# sidebar açık/kapalı durumuna göre otomatik genişlik değişimini korur.
user_prompt = st.chat_input(
 "Bana bir şey sor...",
 accept_file="multiple",
 file_type=SUPPORTED_TYPES,
 key="main_chat_input",
)
# Buton CSS ile sağ alt köşeye sabitlenir.
mic_clicked = st.button(
 "🎙️",
 help="Sesli mesaj kaydet",
 key="mic_toggle_button",
)
if mic_clicked:
 st.session_state.show_mic_recording = not st.session_state.get("show_mic_recording", False)
 if st.session_state.show_mic_recording:
     st.session_state.voice_processing_error = None
 st.rerun()
if voice_recording is not None:
 voice_bytes = voice_recording.getvalue()
 voice_hash = hashlib.sha256(voice_bytes).hexdigest()
 if st.session_state.get("last_processed_voice_hash") != voice_hash:
     st.session_state.last_processed_voice_hash = voice_hash
     chat_id = st.session_state.chat_ids[st.session_state.current_chat]
     voice_name = voice_recording.name or "voice_message.wav"
     voice_path = UPLOAD_DIR / f"chat_{hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]}" / f"voice_{voice_hash[:12]}_{Path(voice_name).name}"
     voice_path.parent.mkdir(parents=True, exist_ok=True)
     voice_path.write_bytes(voice_bytes)
     voice_mime = voice_recording.type or mimetypes.guess_type(voice_name)[0] or "audio/wav"
     voice_attachment = {"path": str(voice_path), "name": voice_name, "type": voice_mime}
     transcription_prompt = (
         "Bu ses kaydındaki konuşmayı eksiksiz ve doğru şekilde yazıya dök. "
         "Yalnızca konuşulan metni döndür; başlık, 'transkripsiyon' etiketi, "
         "açıklama veya yorum ekleme."
     )
     with st.spinner("Konuşman yazıya dönüştürülüyor..."):
         transcript = safe_analyze_audio(
             transcription_prompt, voice_bytes, voice_mime, max_output_tokens=1200
         )
     if transcript and transcript.strip():
         transcript = transcript.strip()
         save_message("user", transcript, [voice_attachment])
         with st.spinner("Yanıt hazırlanıyor..."):
             try:
                     document_files, image_files, audio_files = get_chat_file_context()
                     if detect_image_generation_request(transcript):
                         with st.spinner("🎨 Sesli prompttan görsel oluşturuluyor..."):
                             generated_bytes = generate_image(transcript)
                         generated_name = f"generated_{chat_id}_{len(st.session_state.messages)}.png"
                         generated_path = GENERATED_DIR / generated_name
                         path_string = save_image_bytes(generated_bytes, generated_path)
                         save_message(
                             "assistant",
                             "🎨 Görselin başarıyla oluşturuldu!",
                             [{"path": path_string, "name": generated_name, "type": "generated_image"}],
                         )
                         voice_answer = None
                     elif image_files and detect_image_edit_request(transcript):
                         source_bytes, source_mime, source_name = image_files[-1]
                         with st.spinner("🪄 Sesli talimatla görsel düzenleniyor..."):
                             edited_bytes = edit_image(source_bytes, source_mime, transcript)
                         edited_name = f"edited_{chat_id}_{len(st.session_state.messages)}.png"
                         edited_path = GENERATED_DIR / edited_name
                         path_string = save_image_bytes(edited_bytes, edited_path)
                         save_message(
                             "assistant",
                             f"🪄 **{source_name}** görseli sesli talimatına göre düzenlendi.",
                             [{"path": path_string, "name": edited_name, "type": "generated_image"}],
                         )
                         voice_answer = None
                     else:
                         voice_answer = generate_text(transcript, temperature=0.7, max_output_tokens=1800)
             except Exception as voice_error:
                 voice_answer = None
                 st.session_state.voice_processing_error = f"Sesli mesajın yanıtı oluşturulamadı: {voice_error}"
         if voice_answer and voice_answer.strip():
             save_message("assistant", voice_answer.strip())
         elif voice_answer == "":
             st.session_state.voice_processing_error = "Gemini boş yanıt döndürdü. API/model ayarlarını kontrol et."
     else:
         st.session_state.voice_processing_error = "Konuşma yazıya dönüştürülemedi. Tekrar deneyebilir misin?"
     st.session_state.show_mic_recording = False
     st.rerun()
if user_prompt is not None:
 user_text = (user_prompt.text or "").strip()
 uploaded_files = user_prompt.files or []
 if not user_text and uploaded_files:
     user_text = "Yüklediğim dosyaları incele ve açıkla."
 if user_text or uploaded_files:
     chat_id = st.session_state.chat_ids[st.session_state.current_chat]
     saved_attachments = []
     upload_errors = []
     # Save current uploads. Extract document text and persist it in attachment metadata.
     for file_number, uploaded_file in enumerate(uploaded_files, start=1):
         safe_name = Path(uploaded_file.name).name
         suffix = Path(safe_name).suffix.lower()
         stored_path = UPLOAD_DIR / f"chat_{hashlib.sha256(str(chat_id).encode()).hexdigest()[:12]}" / f"{file_number}_{safe_name}"
         try:
             path_string = save_uploaded_file(uploaded_file, stored_path)
             mime_type = uploaded_file.type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
             attachment = {
                 "path": path_string,
                 "name": safe_name,
                 "type": mime_type,
             }
             if suffix in DOCUMENT_EXTENSIONS:
                 extracted_text = read_document_bytes(safe_name, uploaded_file.getvalue())
                 attachment["extracted_text"] = extracted_text
             elif suffix not in IMAGE_EXTENSIONS and suffix not in AUDIO_EXTENSIONS:
                 upload_errors.append(f"{safe_name}: Desteklenmeyen dosya türü.")
                 continue
             saved_attachments.append(attachment)
         except Exception as error:
             upload_errors.append(f"{safe_name}: {error}")
     display_text = user_text
     if saved_attachments:
         display_text += "\n\n📎 Eklenen dosyalar: " + ", ".join(item["name"] for item in saved_attachments)
     save_message("user", display_text, saved_attachments)
     for error in upload_errors:
         st.warning(error)
     # IMPORTANT: Build context from all user attachments in this chat, not only this turn.
     # This makes follow-up questions work without uploading the same file again.
     try:
         document_files, image_files, audio_files = get_chat_file_context()
     except Exception as error:
         st.error(f"Sohbetteki dosyalar okunamadı: {error}")
         st.stop()
     try:
         # Route image edits before ordinary image analysis. Use the latest image in this chat.
         is_generation_request = detect_image_generation_request(user_text)
         is_edit_request = bool(image_files) and detect_image_edit_request(user_text) and not is_generation_request
         current_audio_attachments = [
             attachment for attachment in saved_attachments
             if Path(attachment["name"]).suffix.lower() in AUDIO_EXTENSIONS
         ]
         if current_audio_attachments:
             attachment = current_audio_attachments[-1]
             audio_path = Path(attachment["path"])
             audio_bytes = audio_path.read_bytes()
             audio_mime = attachment.get("type") or mimetypes.guess_type(attachment["name"])[0] or "audio/mpeg"
             audio_name = attachment["name"]
             audio_prompt = user_text or "Bu ses kaydını yazıya dök, içeriğini analiz et ve önemli noktaları açıkla."
             with st.spinner(f"🎧 {audio_name} Gemini ile analiz ediliyor..."):
                 audio_answer = safe_analyze_audio(audio_prompt, audio_bytes, audio_mime, max_output_tokens=1800)
             if audio_answer:
                 save_message("assistant", audio_answer)
             else:
                 st.error("Ses analiz edilemedi. Gemini API anahtarını ve ses dosyasının formatını kontrol et.")
         elif is_edit_request:
             source_bytes, source_mime, source_name = image_files[-1]
             with st.spinner("🪄 Görselin Cloudflare ile düzenleniyor..."):
                 edited_bytes = edit_image(source_bytes, source_mime, user_text)
             edited_name = f"edited_{chat_id}_{len(st.session_state.messages)}.png"
             edited_path = GENERATED_DIR / edited_name
             path_string = save_image_bytes(edited_bytes, edited_path)
             save_message(
                 "assistant",
                 f"🪄 **{source_name}** görseli isteğine göre düzenlendi.",
                 [{"path": path_string, "name": edited_name, "type": "generated_image"}],
             )
         elif is_generation_request:
             with st.spinner("🎨 Görselin Cloudflare ile oluşturuluyor..."):
                 generated_bytes = generate_image(user_text)
             generated_name = f"generated_{chat_id}_{len(st.session_state.messages)}.png"
             generated_path = GENERATED_DIR / generated_name
             path_string = save_image_bytes(generated_bytes, generated_path)
             save_message(
                 "assistant",
                 "🎨 Görselin başarıyla oluşturuldu!",
                 [{"path": path_string, "name": generated_name, "type": "generated_image"}],
             )
         else:
             assistant_parts = []
             for image_bytes, mime_type, image_name in image_files:
                 with st.spinner(f"🖼️ {image_name} Cloudflare ile analiz ediliyor..."):
                     image_answer = analyze_image(
                         image_bytes,
                         mime_type,
                         user_text or "Bu görseli ayrıntılı şekilde açıkla.",
                     )
                 assistant_parts.append(f"### Görsel analizi: {image_name}\n{image_answer}")
             if document_files:
                 document_context = "\n\n".join(
                     f"--- {name} ---\n{text}" for name, text in document_files
                 )
                 document_prompt = f"""Kullanıcının son isteği:
{user_text or 'Yüklenen belgeleri açıkla ve özetle.'}
Bu sohbet içinde yüklenmiş belgelerin içerikleri:
{document_context}
Yanıtını belgelerin içeriğine dayandır. Belgede bulunmayan bilgileri açıkça belirt. Kullanıcı takip sorusu soruyorsa önceki belge bağlamını kullan."""
                 with st.spinner("📄 Belgeler Gemini ile analiz ediliyor..."):
                     document_answer = safe_generate_text(
                         document_prompt,
                         temperature=0.7,
                         max_output_tokens=1800,
                     )
                 if document_answer:
                     assistant_parts.append(f"### Belge yanıtı\n{document_answer}")
                 else:
                     assistant_parts.append("Belge yanıtı oluşturulamadı. Gemini bağlantını kontrol et.")
             if not image_files and not document_files:
                 with st.spinner("Yanıt hazırlanıyor..."):
                     text_answer = safe_generate_text(
                         user_text,
                         temperature=0.7,
                         max_output_tokens=1500,
                     )
                 if text_answer:
                     assistant_parts.append(text_answer)
                 else:
                     st.error("Yanıt oluşturulamadı. Gemini bağlantını ve API anahtarını kontrol et.")
             if assistant_parts:
                 save_message("assistant", "\n\n".join(assistant_parts))
     except Exception as error:
         st.session_state.voice_processing_error = f"İşlem sırasında hata oluştu: {error}"
     st.rerun()
