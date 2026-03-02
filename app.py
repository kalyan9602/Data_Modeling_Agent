"""
DataMind Agent — Streamlit UI
Run: streamlit run app.py
"""

import streamlit as st
import json
import pandas as pd
import io
import zipfile
from datetime import datetime

from utils.bedrock_client import call_bedrock, BedrockError
from utils.generators import generate_ddl, generate_etl, generate_lineage_csv
from utils.prompts import SYSTEM_PROMPT

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DataMind Agent",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Overall dark feel */
  [data-testid="stAppViewContainer"] { background: #0a0e1a; }
  [data-testid="stSidebar"] { background: #111827; border-right: 1px solid #1e2d45; }
  
  /* Chat messages */
  .user-msg {
    background: linear-gradient(135deg, #7c3aed, #5b21b6);
    color: white;
    padding: 10px 14px;
    border-radius: 8px 8px 2px 8px;
    margin: 4px 0 4px 40px;
    font-size: 13px;
    line-height: 1.6;
  }
  .agent-msg {
    background: #1a2236;
    border: 1px solid #1e2d45;
    color: #e2e8f0;
    padding: 10px 14px;
    border-radius: 8px 8px 8px 2px;
    margin: 4px 40px 4px 0;
    font-size: 13px;
    line-height: 1.6;
  }
  .system-msg {
    background: rgba(0,212,255,0.05);
    border: 1px dashed rgba(0,212,255,0.3);
    color: #00d4ff;
    padding: 10px 14px;
    border-radius: 8px;
    margin: 4px 0;
    font-size: 12px;
    line-height: 1.6;
  }
  .msg-label {
    font-size: 9px;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 2px;
  }
  
  /* Tag badges */
  .tag-fact    { background:#1a1000; color:#f59e0b; border:1px solid #f59e0b44; padding:1px 7px; border-radius:10px; font-size:10px; font-weight:600; }
  .tag-dim     { background:#001a0e; color:#10b981; border:1px solid #10b98144; padding:1px 7px; border-radius:10px; font-size:10px; font-weight:600; }
  .tag-bridge  { background:#0a001a; color:#7c3aed; border:1px solid #7c3aed44; padding:1px 7px; border-radius:10px; font-size:10px; font-weight:600; }

  /* Hide streamlit branding */
  #MainMenu, footer, header { visibility: hidden; }
  
  /* Code block */
  .stCodeBlock { border-radius: 6px; }
  
  /* Download buttons row */
  .dl-row { display:flex; gap:8px; flex-wrap:wrap; margin:8px 0; }
</style>
""", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []          # {role, content, parsed?}
if "current_model" not in st.session_state:
    st.session_state.current_model = None
if "history" not in st.session_state:
    st.session_state.history = []           # raw bedrock conversation history

# ── Sidebar — AWS Config ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🧠 DataMind Agent")
    st.caption("Powered by AWS Bedrock")
    st.divider()

    st.markdown("**AWS Configuration**")
    aws_region = st.selectbox("Region", ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"])
    aws_key    = st.text_input("Access Key ID",   type="password", placeholder="AKIA...")
    aws_secret = st.text_input("Secret Access Key", type="password", placeholder="Your secret key")
    model_id   = st.selectbox("Model", [
      "us.anthropic.claude-sonnet-4-20250514-v1:0",       # Claude Sonnet 4 ← recommended
    "us.anthropic.claude-haiku-4-5-20251001-v1:0",      # Claude Haiku 4.5 ← fastest/cheapest
    "us.anthropic.claude-opus-4-20250514-v1:0",         # Claude Opus 4 ← most powerful
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",      # Claude 3.5 Haiku ← fallback
    ])

    if not aws_key or not aws_secret:
        st.info("⚠️ No credentials — running in **demo mode**", icon="🎭")

    st.divider()
    st.markdown("**Upload Mapping Sheet**")
    uploaded = st.file_uploader("CSV / TXT", type=["csv", "txt"])
    if uploaded:
        content = uploaded.read().decode("utf-8", errors="ignore")
        st.success(f"Loaded: {uploaded.name} ({len(content)} chars)")
        if st.button("📤 Send to Agent"):
            msg = f"[Uploaded: {uploaded.name}]\n\n{content[:4000]}"
            st.session_state.messages.append({"role": "user", "content": f"📎 Uploaded: **{uploaded.name}**\n```\n{content[:600]}{'...' if len(content)>600 else ''}\n```"})
            st.session_state.history.append({"role": "user", "content": msg})
            st.session_state["trigger_call"] = True
            st.rerun()

    st.divider()
    if st.button("🗑️ Clear conversation"):
        st.session_state.messages = []
        st.session_state.history = []
        st.session_state.current_model = None
        st.rerun()

    st.caption("DataMind Agent POC · v1.0")

# ── Main layout ───────────────────────────────────────────────────────────────
col_chat, col_output = st.columns([1, 1], gap="medium")

# ── LEFT — Chat ───────────────────────────────────────────────────────────────
with col_chat:
    st.markdown("#### ⬡ Modeling Agent Chat")

    # Welcome message
    if not st.session_state.messages:
        st.markdown("""<div class='system-msg'>
👋 Welcome to <b>DataMind Agent</b>! I help you model data from source attributes into structured tables with lineage tracking and ER diagrams.<br><br>
You can:<br>
• Paste your mapping sheet (CSV rows in the chat)<br>
• Upload a file using the sidebar<br>
• Describe your source system<br><br>
Let's start — what is your source system or domain?
</div>""", unsafe_allow_html=True)

    # Message history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(f"<div class='msg-label'>You</div><div class='user-msg'>{msg['content']}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='msg-label'>DataMind Agent</div><div class='agent-msg'>{msg['content']}</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Input
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "Message",
            placeholder="Describe your source, paste field list, or answer a question...",
            height=80,
            label_visibility="collapsed",
        )
        submitted = st.form_submit_button("Send ↵", use_container_width=True)

    if submitted and user_input.strip():
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.history.append({"role": "user", "content": user_input})
        st.session_state["trigger_call"] = True
        st.rerun()

# ── Agent call ────────────────────────────────────────────────────────────────
if st.session_state.get("trigger_call"):
    st.session_state["trigger_call"] = False
    with col_chat:
        with st.spinner("DataMind is thinking..."):
            try:
                raw = call_bedrock(
                    history=st.session_state.history,
                    system_prompt=SYSTEM_PROMPT,
                    region=aws_region,
                    access_key=aws_key,
                    secret_key=aws_secret,
                    model_id=model_id,
                )
                # Parse JSON response
                clean = raw.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(clean)

                display_msg = parsed.get("message", "")
                questions = parsed.get("questions", [])
                if questions:
                    display_msg += "\n\n" + "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

                st.session_state.messages.append({"role": "assistant", "content": display_msg})
                st.session_state.history.append({"role": "assistant", "content": raw})

                if parsed.get("model"):
                    st.session_state.current_model = parsed["model"]

            except BedrockError as e:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": f"⚠️ AWS Error: {e}\n\nCheck your credentials and ensure Bedrock is enabled in your region."
                })
            except json.JSONDecodeError:
                st.session_state.messages.append({"role": "assistant", "content": raw})
            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": f"⚠️ Error: {e}"})

    st.rerun()

# ── RIGHT — Output Tabs ───────────────────────────────────────────────────────
with col_output:
    model = st.session_state.current_model

    # Download bar — only shown when model exists
    if model:
        st.markdown("#### ⬇ Downloads")
        dcol1, dcol2, dcol3, dcol4 = st.columns(4)

        ddl_sql  = generate_ddl(model)
        etl_py   = generate_etl(model)
        lin_csv  = generate_lineage_csv(model)

        # Build ZIP
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("datamind_ddl.sql",     ddl_sql)
            zf.writestr("datamind_etl.py",      etl_py)
            zf.writestr("datamind_lineage.csv", lin_csv)
            if model.get("mermaid_er"):
                zf.writestr("datamind_er.mmd", model["mermaid_er"])
            zf.writestr("README.md", f"""# DataMind Agent Output
Generated: {datetime.now().isoformat()}

## Files
- `datamind_ddl.sql`     — CREATE TABLE statements (Redshift / Snowflake / Postgres)
- `datamind_etl.py`      — Python ETL pipeline (pandas + boto3)
- `datamind_lineage.csv` — Field-level source → target lineage
- `datamind_er.mmd`      — Mermaid ER diagram source

## Run ETL
```bash
pip install pandas
python datamind_etl.py
```
""")
        zip_buf.seek(0)

        with dcol1:
            st.download_button("📄 DDL (SQL)",     data=ddl_sql,           file_name="datamind_ddl.sql",     mime="text/plain",  use_container_width=True)
        with dcol2:
            st.download_button("⚙️ ETL (Python)",  data=etl_py,            file_name="datamind_etl.py",      mime="text/plain",  use_container_width=True)
        with dcol3:
            st.download_button("🔗 Lineage (CSV)", data=lin_csv,           file_name="datamind_lineage.csv", mime="text/csv",    use_container_width=True)
        with dcol4:
            st.download_button("📦 All (ZIP)",     data=zip_buf.getvalue(), file_name="datamind_output.zip",  mime="application/zip", use_container_width=True)

        st.divider()

    # Tabs
    tab_er, tab_lineage, tab_tables = st.tabs(["🗂 ER Diagram", "🔗 Field Lineage", "📊 Table Definitions"])

    # ── ER Diagram ──
    with tab_er:
        if model and model.get("mermaid_er"):
            st.code(model["mermaid_er"], language="text")
            st.caption("💡 Copy the above and paste into [mermaid.live](https://mermaid.live) to render interactively")
        else:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.info("ER diagram will appear here once you share your mapping data.", icon="🗂")

    # ── Field Lineage ──
    with tab_lineage:
        if model and model.get("lineage"):
            rows = []
            for l in model["lineage"]:
                rows.append({
                    "Source Field":       l.get("source_field", ""),
                    "Description":        l.get("source_description", ""),
                    "Target Table":       l.get("target_table", ""),
                    "Target Column":      l.get("target_column", ""),
                    "Transformation":     l.get("transformation", ""),
                    "Logic":              l.get("logic", ""),
                })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True,
                column_config={
                    "Transformation": st.column_config.TextColumn(width="small"),
                    "Logic": st.column_config.TextColumn(width="large"),
                })
        else:
            st.info("Field lineage will appear here.", icon="🔗")

    # ── Table Definitions ──
    with tab_tables:
        if model and model.get("tables"):
            for t in model["tables"]:
                ttype = t.get("type", "table")
                tag_class = f"tag-{ttype}" if ttype in ["fact","dimension","bridge"] else "tag-bridge"
                st.markdown(f"""
                    <span class='{tag_class}'>{ttype.upper()}</span>
                    <b style='margin-left:8px;font-size:14px'>{t['name']}</b>
                    <span style='color:#64748b;font-size:11px;margin-left:8px'>{t.get('description','')}</span>
                """, unsafe_allow_html=True)
                cols_data = []
                for c in t.get("columns", []):
                    flags = []
                    if c.get("pk"): flags.append("🔑 PK")
                    if c.get("fk"): flags.append(f"🔗 FK → {c['fk']}")
                    cols_data.append({
                        "Column":      c["name"],
                        "Type":        c.get("type",""),
                        "Flags":       " ".join(flags),
                        "Description": c.get("description",""),
                    })
                st.dataframe(pd.DataFrame(cols_data), use_container_width=True, hide_index=True)
                st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.info("Table definitions will appear here.", icon="📊")



AWS_ACCESS_KEY_ID=AKIAQVJ6HWZ2OCJXW6FO
AWS_SECRET_ACCESS_KEY=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
AWS_DEFAULT_REGION=us-east-1
