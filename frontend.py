import streamlit as st
import os
import io
import platform
import pandas as pd
import time

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
    page_title="DocuVerify Pro — AI Document Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Premium CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg-primary: #0a0e1a;
        --bg-secondary: #111827;
        --bg-card: rgba(17, 24, 39, 0.7);
        --bg-glass: rgba(255, 255, 255, 0.03);
        --border-subtle: rgba(99, 102, 241, 0.15);
        --border-glow: rgba(99, 102, 241, 0.4);
        --accent-indigo: #6366f1;
        --accent-violet: #8b5cf6;
        --accent-purple: #a855f7;
        --accent-cyan: #06b6d4;
        --accent-emerald: #10b981;
        --accent-amber: #f59e0b;
        --accent-rose: #f43f5e;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
        --gradient-primary: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
        --gradient-dark: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
        --shadow-glow: 0 0 30px rgba(99, 102, 241, 0.15);
        --shadow-card: 0 4px 24px rgba(0, 0, 0, 0.3);
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
    }

    .main { background: var(--bg-primary) !important; }

    /* ── Scrollbar ─────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-primary); }
    ::-webkit-scrollbar-thumb { background: var(--accent-indigo); border-radius: 3px; }

    /* ── Hero Banner ───────────────────────────── */
    .hero-banner {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1145 30%, #302b63 60%, #24243e 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 2.5rem 2rem;
        margin-bottom: 1.5rem;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 40%, rgba(99, 102, 241, 0.08) 0%, transparent 50%),
                    radial-gradient(circle at 70% 60%, rgba(168, 85, 247, 0.06) 0%, transparent 50%);
        animation: heroShimmer 8s ease-in-out infinite alternate;
    }
    @keyframes heroShimmer {
        0% { transform: translate(0, 0) rotate(0deg); }
        100% { transform: translate(-5%, 3%) rotate(2deg); }
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 40%, #a5b4fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.6rem;
        position: relative;
        letter-spacing: -0.02em;
    }
    .hero-subtitle {
        color: var(--text-secondary);
        font-size: 1rem;
        font-weight: 400;
        line-height: 1.6;
        position: relative;
        max-width: 700px;
    }
    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(99, 102, 241, 0.12);
        border: 1px solid rgba(99, 102, 241, 0.25);
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.75rem;
        font-weight: 600;
        color: #a5b4fc;
        margin-right: 8px;
        margin-bottom: 12px;
        position: relative;
    }

    /* ── Buttons ───────────────────────────────── */
    .stButton > button {
        width: 100%;
        background: var(--gradient-primary) !important;
        color: white !important;
        border: none !important;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        border-radius: 12px;
        font-size: 1rem;
        letter-spacing: -0.01em;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 2px 12px rgba(99, 102, 241, 0.25);
        position: relative;
        overflow: hidden;
    }
    .stButton > button::before {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 200%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
        transition: left 0.5s ease;
    }
    .stButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4) !important;
    }
    .stButton > button:hover::before { left: 100%; }
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* ── Glass Card ────────────────────────────── */
    .glass-card {
        background: var(--bg-glass);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        box-shadow: var(--shadow-card);
    }
    .glass-card:hover {
        border-color: var(--border-glow);
        box-shadow: var(--shadow-glow);
        transform: translateY(-2px);
    }

    /* ── Metric Cards ─────────────────────────── */
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.8) 0%, rgba(49, 46, 129, 0.6) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 1.25rem 1rem;
        text-align: center;
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .metric-card::after {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%;
        height: 3px;
        background: var(--gradient-primary);
        border-radius: 16px 16px 0 0;
    }
    .metric-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-3px);
        box-shadow: 0 8px 30px rgba(99, 102, 241, 0.2);
    }
    .metric-icon { font-size: 1.6rem; margin-bottom: 0.4rem; }
    .metric-label {
        color: var(--text-secondary);
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.3rem;
    }
    .metric-value {
        color: var(--text-primary);
        font-size: 1.5rem;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
    }

    /* ── Verdict Cards ────────────────────────── */
    .verdict-card {
        border-radius: 16px;
        padding: 1.5rem 2rem;
        text-align: center;
        margin: 1rem 0;
        position: relative;
        overflow: hidden;
    }
    .verdict-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 100%;
        height: 100%;
        opacity: 0.05;
    }
    .verdict-authentic {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.15) 100%);
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .verdict-suspicious {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(217, 119, 6, 0.15) 100%);
        border: 1px solid rgba(245, 158, 11, 0.3);
    }
    .verdict-tampered {
        background: linear-gradient(135deg, rgba(244, 63, 94, 0.1) 0%, rgba(225, 29, 72, 0.15) 100%);
        border: 1px solid rgba(244, 63, 94, 0.3);
    }
    .verdict-icon { font-size: 2.5rem; margin-bottom: 0.5rem; }
    .verdict-text {
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .verdict-sub {
        font-size: 0.85rem;
        color: var(--text-secondary);
        margin-top: 0.3rem;
    }
    .verdict-authentic .verdict-text { color: #34d399; }
    .verdict-suspicious .verdict-text { color: #fbbf24; }
    .verdict-tampered .verdict-text { color: #fb7185; }

    /* ── Field Cards ──────────────────────────── */
    .field-card {
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.6) 100%);
        border: 1px solid rgba(99, 102, 241, 0.12);
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin: 0.35rem 0;
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .field-card::before {
        content: '';
        position: absolute;
        left: 0; top: 0;
        width: 3px; height: 100%;
        background: var(--gradient-primary);
        border-radius: 3px 0 0 3px;
    }
    .field-card:hover {
        border-color: rgba(99, 102, 241, 0.3);
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.8) 100%);
        transform: translateX(4px);
    }
    .field-label {
        color: var(--text-muted);
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 0.15rem;
    }
    .field-value {
        color: var(--text-primary);
        font-size: 1rem;
        font-weight: 500;
        font-family: 'JetBrains Mono', monospace;
    }
    .field-value.not-found {
        color: var(--text-muted);
        font-style: italic;
        font-family: 'Inter', sans-serif;
    }

    /* ── Pipeline Steps ───────────────────────── */
    .pipeline-step {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 0.7rem 1rem;
        background: rgba(17, 24, 39, 0.5);
        border: 1px solid var(--border-subtle);
        border-radius: 10px;
        margin-bottom: 0.5rem;
        transition: all 0.3s ease;
    }
    .pipeline-step.active {
        background: rgba(99, 102, 241, 0.08);
        border-color: rgba(99, 102, 241, 0.3);
    }
    .pipeline-step.done {
        background: rgba(16, 185, 129, 0.06);
        border-color: rgba(16, 185, 129, 0.2);
    }
    .step-num {
        width: 28px; height: 28px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        flex-shrink: 0;
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    .step-num.done {
        background: rgba(16, 185, 129, 0.2);
        color: #34d399;
        border-color: rgba(16, 185, 129, 0.4);
    }
    .step-text {
        font-size: 0.85rem;
        color: var(--text-secondary);
        font-weight: 500;
    }
    .step-text.done { color: #34d399; }

    /* ── Section Headers ──────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.5rem 0 1rem 0;
    }
    .section-icon {
        width: 36px; height: 36px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        background: rgba(99, 102, 241, 0.1);
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    .section-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--text-primary);
        letter-spacing: -0.01em;
    }

    /* ── Sidebar Styles ───────────────────────── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f0c29 0%, #111827 100%) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    .sidebar-logo {
        font-size: 1.6rem;
        font-weight: 800;
        background: var(--gradient-primary);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.03em;
        margin-bottom: 0.3rem;
    }
    .sidebar-tagline {
        color: var(--text-muted);
        font-size: 0.78rem;
        font-weight: 400;
        margin-bottom: 1.2rem;
    }
    .status-row {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.55rem 0;
        font-size: 0.82rem;
        color: var(--text-secondary);
    }
    .status-dot {
        width: 8px; height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
    }
    .status-dot.green {
        background: #10b981;
        box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
        animation: pulse-dot 2s ease-in-out infinite;
    }
    .status-dot.blue { background: #6366f1; box-shadow: 0 0 8px rgba(99, 102, 241, 0.4); }
    .status-dot.amber { background: #f59e0b; box-shadow: 0 0 8px rgba(245, 158, 11, 0.4); }
    .status-dot.gray { background: #64748b; }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .sidebar-section-title {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.12em;
        color: var(--text-muted);
        margin: 1.2rem 0 0.6rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 1px solid rgba(99, 102, 241, 0.1);
    }
    .workflow-step {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        padding: 0.5rem 0;
        font-size: 0.82rem;
        color: var(--text-secondary);
        line-height: 1.5;
    }
    .workflow-num {
        width: 22px; height: 22px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.68rem;
        font-weight: 700;
        background: rgba(99, 102, 241, 0.12);
        color: #818cf8;
        flex-shrink: 0;
        margin-top: 1px;
    }
    .config-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0.45rem 0.7rem;
        background: rgba(17, 24, 39, 0.5);
        border: 1px solid rgba(99, 102, 241, 0.08);
        border-radius: 8px;
        margin-bottom: 0.35rem;
        font-size: 0.78rem;
    }
    .config-label { color: var(--text-secondary); }
    .config-status { font-weight: 600; }
    .config-status.ok { color: #10b981; }
    .config-status.warn { color: #f59e0b; }

    /* ── Upload Area ──────────────────────────── */
    section[data-testid="stFileUploader"] {
        background: rgba(17, 24, 39, 0.4);
        border: 2px dashed rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 1rem;
        transition: all 0.3s ease;
    }
    section[data-testid="stFileUploader"]:hover {
        border-color: rgba(99, 102, 241, 0.4);
        background: rgba(99, 102, 241, 0.04);
    }

    /* ── Tab Styles ───────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: rgba(17, 24, 39, 0.4);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid var(--border-subtle);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        font-weight: 600;
        font-size: 0.9rem;
        padding: 0.6rem 1.5rem;
        color: var(--text-secondary);
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(99, 102, 241, 0.15) !important;
        color: #a5b4fc !important;
    }
    .stTabs [data-baseweb="tab-highlight"] {
        background-color: var(--accent-indigo) !important;
    }

    /* ── Divider ──────────────────────────────── */
    .custom-divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent);
        margin: 1.5rem 0;
        border: none;
    }

    /* ── Stats Bar ────────────────────────────── */
    .stats-bar {
        display: flex;
        gap: 12px;
        margin-bottom: 1rem;
        flex-wrap: wrap;
    }
    .stat-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: rgba(17, 24, 39, 0.6);
        border: 1px solid var(--border-subtle);
        border-radius: 20px;
        padding: 6px 14px;
        font-size: 0.8rem;
        font-weight: 500;
        color: var(--text-secondary);
    }
    .stat-chip .num {
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        color: var(--text-primary);
    }

    /* ── Progress Bar ─────────────────────────── */
    .prog-bar-wrap {
        background: rgba(255,255,255,0.06);
        border-radius: 999px;
        height: 5px;
        margin-top: 8px;
        overflow: hidden;
    }
    .prog-bar-fill {
        height: 100%;
        border-radius: 999px;
        transition: width 1s cubic-bezier(0.4,0,0.2,1);
    }

    /* ── Trust Score Badge ────────────────────── */
    .trust-score-wrap {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 1.5rem;
        background: linear-gradient(135deg, rgba(17,24,39,0.8) 0%, rgba(30,41,59,0.6) 100%);
        border: 1px solid var(--border-subtle);
        border-radius: 16px;
        padding: 1.2rem 2rem;
        margin: 1rem 0;
    }
    .trust-score-num {
        font-size: 3rem;
        font-weight: 800;
        font-family: 'JetBrains Mono', monospace;
        line-height: 1;
    }
    .trust-score-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        color: var(--text-muted);
        margin-top: 4px;
    }
    .trust-score-desc {
        font-size: 0.88rem;
        color: var(--text-secondary);
        max-width: 280px;
    }

    /* ── Upload Prompt ────────────────────────── */
    .upload-prompt {
        text-align: center;
        padding: 3rem 1rem;
        color: var(--text-muted);
    }
    .upload-prompt-icon { font-size: 3.5rem; margin-bottom: 1rem; }
    .upload-prompt-title {
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--text-secondary);
        margin-bottom: 0.4rem;
    }
    .upload-prompt-sub { font-size: 0.85rem; }

    /* ── Expander ─────────────────────────────── */
    .streamlit-expanderHeader {
        background: rgba(17, 24, 39, 0.5) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 12px !important;
        font-weight: 600;
    }

    /* ── Image container ──────────────────────── */
    .img-container {
        background: rgba(17, 24, 39, 0.5);
        border: 1px solid var(--border-subtle);
        border-radius: 12px;
        padding: 0.8rem;
        text-align: center;
    }
    .img-label {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--text-muted);
        margin-bottom: 0.5rem;
    }

    /* ── Spinner animation override ───────────── */
    .stSpinner > div {
        border-color: var(--accent-indigo) transparent transparent transparent !important;
    }

    /* ── Hide default decorations ─────────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Smooth entry animation ───────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .animate-in {
        animation: fadeInUp 0.5s ease-out forwards;
    }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
        <div class="sidebar-logo">🛡️ DocuVerify</div>
        <div class="sidebar-tagline">AI-Powered Document Intelligence Platform</div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── System Status ──
    st.markdown('<div class="sidebar-section-title">System Status</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="status-row">
            <span class="status-dot green"></span>
            <span>Platform Online</span>
        </div>
        <div class="status-row">
            <span class="status-dot blue"></span>
            <span>Tesseract-OCR Engine</span>
        </div>
        <div class="status-row">
            <span class="status-dot blue"></span>
            <span>OpenCV Preprocessing</span>
        </div>
        <div class="status-row">
            <span class="status-dot amber"></span>
            <span>ELA Tamper Detection</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Workflow ──
    st.markdown('<div class="sidebar-section-title">Workflow</div>', unsafe_allow_html=True)
    workflow_steps = [
        ("1", "Upload document (JPG, PNG, PDF)"),
        ("2", "Click <b>Run Verification</b>"),
        ("3", "Review extracted fields & verdict"),
        ("4", "Check audit logs for history"),
    ]
    for num, text in workflow_steps:
        st.markdown(f"""
            <div class="workflow-step">
                <span class="workflow-num">{num}</span>
                <span>{text}</span>
            </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

    # ── Configuration ──
    st.markdown('<div class="sidebar-section-title">Configuration</div>', unsafe_allow_html=True)
    s3_configured = bool(os.getenv("AWS_S3_BUCKET", "").strip())
    db_configured = bool(os.getenv("DB_HOST", "").strip())

    st.markdown(f"""
        <div class="config-item">
            <span class="config-label">☁️ S3 Upload</span>
            <span class="config-status {'ok' if s3_configured else 'warn'}">
                {'Enabled' if s3_configured else 'Not Set'}
            </span>
        </div>
        <div class="config-item">
            <span class="config-label">🗄️ PostgreSQL</span>
            <span class="config-status {'ok' if db_configured else 'warn'}">
                {'Connected' if db_configured else 'Default'}
            </span>
        </div>
    """, unsafe_allow_html=True)

# ─── Hero Banner ─────────────────────────────────────────────────────────────
st.markdown("""
    <div class="hero-banner animate-in">
        <div>
            <span class="hero-badge">🤖 AI-Powered</span>
            <span class="hero-badge">🔒 Tamper Detection</span>
            <span class="hero-badge">📊 Audit Logging</span>
        </div>
        <div class="hero-title">DocuVerify Pro</div>
        <div class="hero-subtitle">
            Enterprise-grade document intelligence — upload any document and get instant
            AI-powered verification, OCR extraction, tamper analysis & secure audit logging.
        </div>
    </div>
""", unsafe_allow_html=True)

# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["🔍  Verification Pipeline", "📋  Audit History"])


# ═══════════════════════════════════════════════════════════
# TAB 1 — Live Verification Pipeline
# ═══════════════════════════════════════════════════════════
with tab1:
    uploaded_file = st.file_uploader(
        "Drop your document here or browse",
        type=["jpg", "jpeg", "png", "pdf"],
        help="Supports JPG, PNG, and PDF formats. Max first page for PDFs."
    )

    if uploaded_file is None:
        st.markdown("""
            <div class="upload-prompt animate-in">
                <div class="upload-prompt-icon">🛡️</div>
                <div class="upload-prompt-title">Upload a document to begin verification</div>
                <div class="upload-prompt-sub">Supports JPG, PNG, PDF &mdash; certificates, IDs, marksheets, letters</div>
            </div>
        """, unsafe_allow_html=True)

    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        filename = uploaded_file.name

        # ── PDF → Image Conversion ──────────────────────
        if filename.lower().endswith(".pdf"):
            st.info("📄 PDF detected — converting first page to high-res image...")
            converted = False

            try:
                import fitz
                pdf_doc = fitz.open(stream=file_bytes, filetype="pdf")
                page = pdf_doc[0]
                mat = fitz.Matrix(4.0, 4.0)
                pix = page.get_pixmap(matrix=mat)
                image_bytes = pix.tobytes("png")
                display_bytes = image_bytes
                converted = True
                pdf_doc.close()
            except ImportError:
                pass
            except Exception as e:
                st.warning(f"PyMuPDF failed ({e}), trying fallback...")

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

        # ── Show original document in styled container ──
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div class="section-header">
                    <div class="section-icon">📄</div>
                    <span class="section-title">Original Document</span>
                </div>
            """, unsafe_allow_html=True)
            st.markdown('<div class="img-container">', unsafe_allow_html=True)
            st.image(display_bytes, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Run Pipeline ────────────────────────────────
        if st.button("🚀 Run AI Verification Pipeline", type="primary"):

            # Show pipeline steps
            progress_placeholder = st.empty()

            def show_pipeline_step(steps_done):
                all_steps = [
                    "Cloud Upload (S3)",
                    "OpenCV Preprocessing",
                    "OCR & Field Extraction",
                    "Tamper Analysis (ELA)",
                    "Database Logging",
                ]
                html = ""
                for i, step_name in enumerate(all_steps):
                    if i < steps_done:
                        html += f'''<div class="pipeline-step done">
                            <span class="step-num done">✓</span>
                            <span class="step-text done">{step_name}</span>
                        </div>'''
                    elif i == steps_done:
                        html += f'''<div class="pipeline-step active">
                            <span class="step-num">{i+1}</span>
                            <span class="step-text">⏳ {step_name}...</span>
                        </div>'''
                    else:
                        html += f'''<div class="pipeline-step">
                            <span class="step-num">{i+1}</span>
                            <span class="step-text">{step_name}</span>
                        </div>'''
                progress_placeholder.markdown(html, unsafe_allow_html=True)

            try:
                # ── Step 1: S3 Upload ────────────────────
                show_pipeline_step(0)
                s3_url = upload_to_s3(file_bytes, filename)
                if s3_url:
                    st.success(f"☁️ Uploaded to S3: [View]({s3_url})")
                show_pipeline_step(1)

                # ── Step 2: OpenCV Preprocessing ─────────
                processed_img = preprocess_image(image_bytes)

                with col2:
                    st.markdown("""
                        <div class="section-header">
                            <div class="section-icon">🔧</div>
                            <span class="section-title">Preprocessed (OpenCV)</span>
                        </div>
                    """, unsafe_allow_html=True)
                    st.markdown('<div class="img-container">', unsafe_allow_html=True)
                    st.image(processed_img, use_container_width=True, clamp=True)
                    st.markdown('</div>', unsafe_allow_html=True)

                show_pipeline_step(2)

                # ── Step 3: AI Extraction ────────────────
                extractor = get_extractor()
                result = extractor.extract_fields(image_bytes)
                show_pipeline_step(3)

                # ── Step 4: Results Display ──────────────
                tamper_data = result["tamper_analysis"]
                show_pipeline_step(4)

                # ── Step 5: DB Logging ───────────────────
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
                show_pipeline_step(5)

                st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)

                # ═══════════ RESULTS SECTION ═══════════
                st.markdown("""
                    <div class="section-header">
                        <div class="section-icon">📊</div>
                        <span class="section-title">Verification Results</span>
                    </div>
                """, unsafe_allow_html=True)

                # ── Metric Cards (color-coded) ────────────
                conf = result.get('ocr_confidence', 0)
                tscore = tamper_data['ela_score']
                engine = result.get('engine', 'Tesseract')

                # Dynamic colors
                conf_color  = '#34d399' if conf >= 70 else '#fbbf24' if conf >= 40 else '#fb7185'
                tamp_color  = '#34d399' if tscore < 20 else '#fbbf24' if tscore < 50 else '#fb7185'
                conf_pct    = min(conf, 100)
                tamp_pct    = min(tscore, 100)

                # Trust Score = weighted combo
                trust = max(0, min(100, round((conf * 0.5) + ((100 - tscore) * 0.5), 1)))
                trust_color = '#34d399' if trust >= 70 else '#fbbf24' if trust >= 40 else '#fb7185'
                trust_label = 'High Trust' if trust >= 70 else 'Moderate Trust' if trust >= 40 else 'Low Trust'

                m1, m2, m3, m4 = st.columns(4)
                with m1:
                    st.markdown(f"""
                        <div class="metric-card" style="border-color:rgba({','.join(['52,211,153' if conf>=70 else '251,191,36' if conf>=40 else '251,113,133'])},0.3)">
                            <div class="metric-icon">🎯</div>
                            <div class="metric-label">OCR Confidence</div>
                            <div class="metric-value" style="color:{conf_color}">{conf:.1f}%</div>
                            <div class="prog-bar-wrap"><div class="prog-bar-fill" style="width:{conf_pct}%;background:{conf_color}"></div></div>
                        </div>
                    """, unsafe_allow_html=True)
                with m2:
                    st.markdown(f"""
                        <div class="metric-card" style="border-color:rgba({','.join(['52,211,153' if tscore<20 else '251,191,36' if tscore<50 else '251,113,133'])},0.3)">
                            <div class="metric-icon">🔍</div>
                            <div class="metric-label">Tamper Score</div>
                            <div class="metric-value" style="color:{tamp_color}">{tscore:.1f}<span style="font-size:0.8rem;color:var(--text-muted)">/100</span></div>
                            <div class="prog-bar-wrap"><div class="prog-bar-fill" style="width:{tamp_pct}%;background:{tamp_color}"></div></div>
                        </div>
                    """, unsafe_allow_html=True)
                with m3:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-icon">🤖</div>
                            <div class="metric-label">AI Engine</div>
                            <div class="metric-value" style="font-size:0.85rem;font-family:'Inter',sans-serif;color:#a5b4fc">{engine}</div>
                        </div>
                    """, unsafe_allow_html=True)
                with m4:
                    st.markdown(f"""
                        <div class="metric-card" style="border-color:rgba(52,211,153,0.3)">
                            <div class="metric-icon">📦</div>
                            <div class="metric-label">Audit Status</div>
                            <div class="metric-value" style="color:#34d399;font-size:1.1rem">✓ Logged</div>
                        </div>
                    """, unsafe_allow_html=True)

                # ── Trust Score ───────────────────────────
                st.markdown(f"""
                    <div class="trust-score-wrap animate-in">
                        <div style="text-align:center">
                            <div class="trust-score-num" style="color:{trust_color}">{trust:.0f}</div>
                            <div class="trust-score-label">Trust Score</div>
                        </div>
                        <div>
                            <div style="font-size:1rem;font-weight:700;color:{trust_color};margin-bottom:4px">{trust_label}</div>
                            <div class="trust-score-desc">Composite score combining OCR readability ({conf:.1f}%) and tamper integrity ({100-tscore:.1f}%)</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                # ── Verdict Card ─────────────────────────
                verdict = tamper_data["verdict"]
                risk = tamper_data["risk_level"]
                verdict_class = {
                    "Low": "verdict-authentic",
                    "Medium": "verdict-suspicious",
                    "High": "verdict-tampered",
                }.get(risk, "verdict-suspicious")
                verdict_icon = {
                    "Low": "✅",
                    "Medium": "⚠️",
                    "High": "🚨",
                }.get(risk, "⚠️")
                verdict_detail = {
                    "Low": "No signs of digital manipulation detected",
                    "Medium": "Some anomalies found — manual review recommended",
                    "High": "Significant manipulation indicators — flagged for review",
                }.get(risk, "Analysis inconclusive")

                st.markdown(f"""
                    <div class="verdict-card {verdict_class} animate-in">
                        <div class="verdict-icon">{verdict_icon}</div>
                        <div class="verdict-text">{verdict}</div>
                        <div class="verdict-sub">{verdict_detail}</div>
                    </div>
                """, unsafe_allow_html=True)

                # ── Extracted Fields ─────────────────────
                st.markdown("""
                    <div class="section-header">
                        <div class="section-icon">🗂️</div>
                        <span class="section-title">Extracted Fields</span>
                    </div>
                """, unsafe_allow_html=True)

                fields = result.get("extracted_fields", {})
                cols = st.columns(2)
                field_icons = {
                    "name": "👤",
                    "dob": "📅",
                    "id_number": "🔢",
                    "department": "🏢",
                    "phone": "📱",
                    "email": "📧",
                }
                for i, (key, value) in enumerate(fields.items()):
                    with cols[i % 2]:
                        icon = field_icons.get(key, "📄")
                        not_found_class = ' not-found' if value == "Not Found" else ''
                        display_val = value if value != "Not Found" else "— Not detected —"
                        st.markdown(f"""
                            <div class="field-card">
                                <div class="field-label">{icon} {key.replace("_", " ").title()}</div>
                                <div class="field-value{not_found_class}">{display_val}</div>
                            </div>
                        """, unsafe_allow_html=True)

                # ── Raw OCR Text ─────────────────────────
                with st.expander("📝 Raw OCR Text Output"):
                    st.code(result.get("raw_text", ""), language=None)

                st.success("✅ Verification complete — results logged to audit database!")

            except Exception as e:
                st.error(f"❌ Processing failed: {e}")
                st.exception(e)


# ═══════════════════════════════════════════════════════════
# TAB 2 — Audit Logs from PostgreSQL
# ═══════════════════════════════════════════════════════════
with tab2:
    st.markdown("""
        <div class="section-header">
            <div class="section-icon">📋</div>
            <span class="section-title">Audit History — Verification Records</span>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("""
        <div style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 1rem;">
            Real-time records from the <code style="background: rgba(99,102,241,0.1); padding: 2px 6px; border-radius: 4px; color: #a5b4fc;">verification_logs</code> table in PostgreSQL.
        </div>
    """, unsafe_allow_html=True)

    col_refresh, _ = st.columns([1, 4])
    with col_refresh:
        refresh = st.button("🔄 Refresh Logs")

    df = fetch_all_logs()

    if df.empty:
        st.markdown("""
            <div class="glass-card" style="text-align: center; padding: 3rem;">
                <div style="font-size: 3rem; margin-bottom: 1rem;">📭</div>
                <div style="font-size: 1.1rem; font-weight: 600; color: var(--text-primary); margin-bottom: 0.5rem;">
                    No Verification Records Found
                </div>
                <div style="color: var(--text-secondary); font-size: 0.9rem; max-width: 400px; margin: 0 auto;">
                    Either the database is not connected, or no documents have been verified yet.
                    Check your <code>.env</code> file for DB credentials.
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Fallback: show dummy CSV if available
        if os.path.exists("dummy_applicants.csv"):
            st.markdown('<div class="custom-divider"></div>', unsafe_allow_html=True)
            st.markdown("""
                <div class="section-header">
                    <div class="section-icon">📂</div>
                    <span class="section-title">Demo Data — Sample Records</span>
                </div>
            """, unsafe_allow_html=True)
            dummy_df = pd.read_csv("dummy_applicants.csv")
            st.dataframe(dummy_df, use_container_width=True)
    else:
        # Summary stats bar
        total = len(df)
        authentic_count = len(df[df.get("status", pd.Series()).str.contains("Authentic", na=False)]) if "status" in df.columns else 0
        flagged_count = len(df[df.get("status", pd.Series()).str.contains("Flagged", na=False)]) if "status" in df.columns else 0
        suspicious_count = total - authentic_count - flagged_count

        st.markdown(f"""
            <div class="stats-bar animate-in">
                <div class="stat-chip">
                    📊 Total: <span class="num">{total}</span>
                </div>
                <div class="stat-chip">
                    🟢 Authentic: <span class="num" style="color:#10b981">{authentic_count}</span>
                </div>
                <div class="stat-chip">
                    🟡 Suspicious: <span class="num" style="color:#f59e0b">{suspicious_count}</span>
                </div>
                <div class="stat-chip">
                    🔴 Flagged: <span class="num" style="color:#f43f5e">{flagged_count}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Format columns
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

        # Download button
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Download Audit Logs as CSV",
            data=csv_data,
            file_name="verification_logs.csv",
            mime="text/csv",
        )
