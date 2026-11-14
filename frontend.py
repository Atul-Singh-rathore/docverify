import streamlit as st
import os
import io
import platform
import pandas as pd

from src.preprocessing import preprocess_image
from src.extractor import DocumentExtractor
from src.database import init_db, log_verification, fetch_all_logs
from src.s3_upload import upload_to_s3

@st.cache_resource
def get_extractor():
    """Cache the extractor so it's only initialized once per session."""
    return DocumentExtractor()

# ─── Tesseract Path (Windows) ────────────────────────────────────────────────
if platform.system() == "Windows":
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─── DB Init ─────────────────────────────────────────────────────────────────
try:
    init_db()
except Exception as e:
    st.warning(f"⚠️ DB Init skipped: {e}")

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DocuVerify Pro",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .main { background: #0f1117; }

    .stButton > button {
        width: 100%;
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 100%);
        color: white;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: 600;
        border-radius: 8px;
        font-size: 1rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #4f46e5 0%, #9333ea 100%);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(99,102,241,0.4);
    }

    .metric-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
        border: 1px solid #4338ca;
        border-radius: 12px;
        padding: 1rem;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .metric-label { color: #a5b4fc; font-size: 0.8rem; font-weight: 500; }
    .metric-value { color: #e0e7ff; font-size: 1.5rem; font-weight: 700; }

    .verdict-authentic { color: #4ade80; font-size: 1.3rem; font-weight: 700; }
    .verdict-suspicious { color: #fbbf24; font-size: 1.3rem; font-weight: 700; }
    .verdict-tampered   { color: #f87171; font-size: 1.3rem; font-weight: 700; }

    .field-box {
        background: #1e293b;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        margin: 0.3rem 0;
        font-size: 0.95rem;
        border-left: 3px solid #6366f1;
    }
    .field-label { color: #94a3b8; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
    .field-value { color: #e2e8f0; font-size: 1rem; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛡️ DocuVerify Hub")
    st.markdown("---")
    st.info(
        "**System Status:** 🟢 Online\n\n"
        "**AI Engine:** Tesseract-OCR + LayoutLMv3\n\n"
        "**Preprocessing:** OpenCV (Deskew + Denoise)\n\n"
        "**Tamper Detection:** ELA (Error Level Analysis)\n\n"
        "**Database:** PostgreSQL\n\n"
        "**Cloud Storage:** AWS S3 (optional)"
    )
    st.markdown("---")
    st.markdown("### 📋 Workflow Guide")
    st.markdown(
        "1. Upload a document (JPG, PNG, or PDF)\n"
        "2. Click **Run AI Verification Pipeline**\n"
        "3. View extracted fields & tamper verdict\n"
        "4. Check audit logs in **Tab 2**"
    )
    st.markdown("---")
    st.markdown("### ⚙️ Config")
    s3_configured = bool(os.getenv("AWS_S3_BUCKET", "").strip())
    db_configured = bool(os.getenv("DB_HOST", "").strip())
    st.markdown(f"- S3 Upload: {'✅ Enabled' if s3_configured else '⚠️ Not configured'}")
    st.markdown(f"- PostgreSQL: {'✅ Env vars set' if db_configured else '⚠️ Using defaults'}")

# ─── Main Header ─────────────────────────────────────────────────────────────
st.title("🛡️ DocuVerify Pro")
st.markdown(
    "**Enterprise-grade document intelligence** — AI-powered verification, "
    "OCR extraction, tamper detection & secure audit logging."
)
st.markdown("---")

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📄  Live Verification Pipeline", "📋  Audit Logs (PostgreSQL)"])


# ═══════════════════════════════════════════════════════════
# TAB 1 — Live Verification Pipeline
# ═══════════════════════════════════════════════════════════
with tab1:
    uploaded_file = st.file_uploader(
        "Upload a document image or PDF",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Supports JPG, PNG, and PDF formats."
    )

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name

        # ── PDF → Image Conversion ──────────────────────
        if filename.lower().endswith(".pdf"):
            st.info("📄 PDF detected — converting first page to image for processing...")
            converted = False

            # Method 1: PyMuPDF (fitz) — no Poppler needed ✅
            try:
                import fitz  # pymupdf
                pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                page = pdf_doc[0]
                mat = fitz.Matrix(4.0, 4.0)  # 4x zoom = ~288 DPI — better for OCR
                pix = page.get_pixmap(matrix=mat)
                image_bytes = pix.tobytes("png")
                display_bytes = image_bytes
                converted = True
                pdf_doc.close()
            except ImportError:
                pass  # Try fallback
            except Exception as e:
                st.warning(f"PyMuPDF failed ({e}), trying fallback...")

            # Method 2: pdf2image + Poppler (fallback)
            if not converted:
                try:
                    from pdf2image import convert_from_bytes
                    pages = convert_from_bytes(file_bytes, dpi=200)
                    img_buf = io.BytesIO()
                    pages[0].save(img_buf, format="PNG")
                    image_bytes = img_buf.getvalue()
                    display_bytes = image_bytes
                    converted = True
                except Exception as e:
                    st.error(
                        f"❌ PDF conversion failed: {e}\n\n"
                        "**Fix:** Run `pip install pymupdf` in your terminal."
                    )
                    st.stop()

            if not converted:
                st.error("❌ Could not convert PDF. Run `pip install pymupdf`.")
                st.stop()
        else:
            image_bytes = file_bytes
            display_bytes = file_bytes

        # ── Show original document ──────────────────────
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📄 Original Document")
            st.image(display_bytes, use_container_width=True)

        # ── Run Pipeline ────────────────────────────────
        if st.button("🚀 Run AI Verification Pipeline"):
            with st.spinner("⚙️ Running OpenCV preprocessing & AI analysis..."):

                # ── Step 1: S3 Upload (optional) ────────
                s3_url = upload_to_s3(file_bytes, filename)
                if s3_url:
                    st.success(f"☁️ Document uploaded to S3: [View]({s3_url})")

                try:
                    # ── Step 2: OpenCV Preprocessing ────
                    processed_img = preprocess_image(image_bytes)

                    with col2:
                        st.subheader("🔧 Preprocessed (OpenCV)")
                        st.image(processed_img, use_container_width=True, clamp=True)

                    # ── Step 3: AI Extraction ────────────
                    extractor = get_extractor()
                    result = extractor.extract_fields(image_bytes)

                    st.markdown("---")
                    st.subheader("📊 Verification Results")

                    # ── Metrics Row ──────────────────────
                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("🎯 OCR Confidence",  f"{result.get('ocr_confidence', 0):.1f}%")
                    m2.metric("🔍 Tamper Score",    f"{result['tamper_analysis']['ela_score']:.1f}/100")
                    m3.metric("🤖 AI Engine",       result.get("engine", "Tesseract"))
                    m4.metric("📦 DB Log",          "✅ Saved")

                    # ── Tamper Verdict ───────────────────
                    verdict = result["tamper_analysis"]["verdict"]
                    risk = result["tamper_analysis"]["risk_level"]
                    css_class = {
                        "Low": "verdict-authentic",
                        "Medium": "verdict-suspicious",
                        "High": "verdict-tampered",
                    }.get(risk, "verdict-suspicious")

                    st.markdown(
                        f'<p class="{css_class}">Tamper Verdict: {verdict}</p>',
                        unsafe_allow_html=True
                    )

                    # ── Extracted Fields ─────────────────
                    st.subheader("🗂️ Extracted Fields")
                    fields = result.get("extracted_fields", {})
                    cols = st.columns(2)
                    for i, (key, value) in enumerate(fields.items()):
                        with cols[i % 2]:
                            st.markdown(
                                f'<div class="field-box">'
                                f'<div class="field-label">{key.replace("_", " ").title()}</div>'
                                f'<div class="field-value">{value}</div>'
                                f'</div>',
                                unsafe_allow_html=True
                            )

                    # ── Raw OCR Text ─────────────────────
                    with st.expander("📝 Raw OCR Text"):
                        st.text(result.get("raw_text", ""))

                    # ── Step 4: DB Logging ───────────────
                    tamper_data = result["tamper_analysis"]
                    final_status = (
                        "Authentic" if tamper_data["risk_level"] == "Low"
                        else "Flagged" if tamper_data["risk_level"] == "High"
                        else "Suspicious"
                    )
                    log_verification(
                        filename=filename,
                        status=final_status,
                        confidence_score=result.get("ocr_confidence", 0) / 100,
                        ocr_confidence=result.get("ocr_confidence", 0),
                        tamper_score=tamper_data["ela_score"],
                        tamper_verdict=tamper_data["verdict"],
                        s3_url=s3_url,
                    )
                    st.success("✅ Document verified and logged to PostgreSQL audit table!")

                except Exception as e:
                    st.error(f"❌ Processing failed: {e}")
                    st.exception(e)


# ═══════════════════════════════════════════════════════════
# TAB 2 — Audit Logs from PostgreSQL
# ═══════════════════════════════════════════════════════════
with tab2:
    st.subheader("📋 PostgreSQL Audit Logs — Verification History")
    st.markdown("Real-time records from the `verification_logs` table in PostgreSQL.")

    col_refresh, col_info = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("🔄 Refresh Logs")

    df = fetch_all_logs()

    if df.empty:
        st.warning(
            "⚠️ No records found in PostgreSQL. "
            "Either the database is not connected, or no documents have been verified yet.\n\n"
            "**Tip:** Check your `.env` file / environment variables for DB credentials."
        )

        # Fallback: show dummy CSV if available
        if os.path.exists("dummy_applicants.csv"):
            st.markdown("---")
            st.subheader("📂 Demo Data — Dummy Applicants (CSV Fallback)")
            dummy_df = pd.read_csv("dummy_applicants.csv")
            st.dataframe(dummy_df, use_container_width=True)
    else:
        # Format columns nicely
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")

        status_colors = {
            "Authentic": "🟢 Authentic",
            "Flagged": "🔴 Flagged",
            "Suspicious": "🟡 Suspicious",
        }
        if "status" in df.columns:
            df["status"] = df["status"].map(lambda x: status_colors.get(x, x))

        st.dataframe(df, use_container_width=True, height=500)
        st.markdown(f"**Total records:** {len(df)}")

        # Download button
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Logs as CSV",
            data=csv_data,
            file_name="verification_logs.csv",
            mime="text/csv",
        )
