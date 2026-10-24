import streamlit as st
import requests
import uuid
import json
import glob
import os

st.set_page_config(
    page_title="AI IT Helpdesk Ticket Assistant",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded"
)

BACKEND_URL = "http://localhost:5001"

# Initialize session state
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "👋 **Hello! I am your AI IT Helpdesk Assistant.**\nPlease describe the issue or problem you are experiencing, and I'll help diagnose it or route a ticket."
        }
    ]
if "extracted_data" not in st.session_state:
    st.session_state.extracted_data = {}
if "missing_fields" not in st.session_state:
    st.session_state.missing_fields = ["application", "device", "location", "impact", "urgency"]
if "current_guidance" not in st.session_state:
    st.session_state.current_guidance = None
if "generated_ticket" not in st.session_state:
    st.session_state.generated_ticket = None
if "stage" not in st.session_state:
    st.session_state.stage = "intake"
if "ticket_submitted" not in st.session_state:
    st.session_state.ticket_submitted = False

# Sidebar Controls
with st.sidebar:
    st.title("⚙️ Control & Diagnostics")
    st.caption(f"Session ID: `{st.session_state.session_id[:8]}...`")

    if st.button("🔄 Start New Conversation", use_container_width=True):
        try:
            requests.post(f"{BACKEND_URL}/api/reset", json={"session_id": st.session_state.session_id}, timeout=3)
        except Exception:
            pass
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 **Hello! I am your AI IT Helpdesk Assistant.**\nPlease describe the issue or problem you are experiencing, and I'll help diagnose it or route a ticket."
            }
        ]
        st.session_state.extracted_data = {}
        st.session_state.missing_fields = ["application", "device", "location", "impact", "urgency"]
        st.session_state.current_guidance = None
        st.session_state.generated_ticket = None
        st.session_state.stage = "intake"
        st.session_state.ticket_submitted = False
        st.rerun()

    st.markdown("---")
    st.subheader("📋 Memory & Extracted Slots")
    extracted = st.session_state.extracted_data

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"**User**: `{extracted.get('user') or '—'}`")
        st.markdown(f"**Device**: `{extracted.get('device') or '—'}`")
        st.markdown(f"**App**: `{extracted.get('application') or '—'}`")
    with col_b:
        st.markdown(f"**Location**: `{extracted.get('location') or '—'}`")
        st.markdown(f"**Impact**: `{extracted.get('impact') or '—'}`")
        st.markdown(f"**Urgency**: `{extracted.get('urgency') or '—'}`")

    if extracted.get("attempted_fixes"):
        st.markdown("**Attempted Fixes:**")
        for fix in extracted["attempted_fixes"]:
            st.markdown(f"- 🔧 *{fix}*")

    if st.session_state.missing_fields:
        st.info(f"⏳ **Pending Details:** {', '.join(st.session_state.missing_fields)}")
    else:
        st.success("✅ All required intake parameters collected!")

    st.markdown("---")
    st.subheader("📤 Document & Rule Uploader")
    doc_type = st.selectbox(
        "Select Document Type",
        ["support_article", "priority_rules", "assets", "resolver_groups", "known_outages"],
        format_func=lambda x: {
            "support_article": "Support Knowledge Article (.md)",
            "priority_rules": "Priority Rules (priority_rules.csv)",
            "assets": "Asset Catalog (assets.csv)",
            "resolver_groups": "Resolver Groups (resolver_groups.json)",
            "known_outages": "Known Outages (known_outages.json)"
        }.get(x, x)
    )
    uploaded_file = st.file_uploader("Upload File", key="doc_uploader")
    if uploaded_file is not None:
        if st.button("Submit & Index Document", use_container_width=True):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
                data = {"doc_type": doc_type}
                res = requests.post(f"{BACKEND_URL}/api/upload_doc", files=files, data=data, timeout=10)
                if res.status_code == 200:
                    st.success(res.json().get("message", "Uploaded successfully!"))
                else:
                    st.error(f"Upload failed: {res.text}")
            except Exception as e:
                st.error(f"Error connecting to backend: {e}")

# Main Tabs
tab_chat, tab_kb, tab_audit = st.tabs(["💬 Helpdesk Ticket Assistant", "📚 Knowledge Articles", "🛡️ Audit & Governance Logs"])

with tab_chat:
    st.header("🎧 AI IT Helpdesk Assistant")
    st.caption("Intelligent Intake • Duplicate & Outage Detection • RAG Guidance • Smart Triage • Routing Explanation")

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Outage and Duplicate Notifications
    if st.session_state.current_guidance:
        guidance = st.session_state.current_guidance

        # Check for Outage
        if guidance.get("has_outage"):
            for out in guidance["outages"]:
                st.warning(
                    f"⚠️ **ACTIVE OUTAGE DETECTED:** **[{out.get('outage_id')}] {out.get('title')}**\n\n"
                    f"- **Service:** {out.get('service')}\n"
                    f"- **Affected Locations:** {', '.join(out.get('affected_locations', []))}\n"
                    f"- **Status:** `{out.get('status')}` | **Estimated Resolution:** `{out.get('eta')}`\n\n"
                    f"_{out.get('description')}_"
                )

        # Check for Duplicate Ticket
        if guidance.get("has_duplicate"):
            for dup in guidance["duplicates"]:
                st.info(
                    f"ℹ️ **POTENTIAL DUPLICATE TICKET DETECTED:** **[{dup.get('ticket_id')}]**\n\n"
                    f"- **Summary:** {dup.get('summary')}\n"
                    f"- **Status:** `{dup.get('status')}`\n"
                    f"- **Past Resolution:** {dup.get('resolution')}"
                )

        # Recommended Self-Service Steps Card (Innovative Workflow 4)
        if guidance.get("recommended_step") and st.session_state.stage == "guidance_pending":
            with st.container(border=True):
                st.markdown("### 🛠️ Recommended Approved Self-Service Guidance")
                st.caption(f"📌 {guidance.get('source_citation')}")
                st.markdown(guidance.get("recommended_step"))

                st.markdown("---")
                st.markdown("##### ❓ Did these self-service steps resolve your issue?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("✅ Yes, My Issue is Resolved!", use_container_width=True, type="primary"):
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/api/feedback",
                                json={"session_id": st.session_state.session_id, "resolved": True},
                                timeout=10
                            ).json()
                            st.session_state.stage = "self_resolved"
                            st.session_state.messages.append({"role": "assistant", "content": resp.get("message")})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with c2:
                    if st.button("❌ No, I Need IT Ticket Routing", use_container_width=True):
                        try:
                            resp = requests.post(
                                f"{BACKEND_URL}/api/feedback",
                                json={"session_id": st.session_state.session_id, "resolved": False},
                                timeout=10
                            ).json()
                            st.session_state.stage = "ticket_ready"
                            st.session_state.generated_ticket = resp.get("ticket")
                            st.session_state.messages.append({"role": "assistant", "content": resp.get("message")})
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

    # Ticket Routing and Review Card (Innovative Workflow 3 & 5)
    if st.session_state.generated_ticket and st.session_state.stage == "ticket_ready":
        ticket = st.session_state.generated_ticket
        with st.container(border=True):
            st.markdown(f"### 🎫 Prepared Incident Ticket: `{ticket.get('ticket_id')}`")
            
            p_col1, p_col2, p_col3 = st.columns([1, 1, 1])
            with p_col1:
                p_val = ticket.get("priority", "P3 - Moderate")
                if "P1" in p_val:
                    st.error(f"**Priority:** {p_val}")
                elif "P2" in p_val:
                    st.warning(f"**Priority:** {p_val}")
                else:
                    st.success(f"**Priority:** {p_val}")
            with p_col2:
                st.info(f"**Resolver Group:** `{ticket.get('suggested_resolver_group')}`")
            with p_col3:
                conf = ticket.get('confidence', 0.9)
                st.metric("Triage Confidence", f"{int(conf * 100)}%", delta="Uncertain" if ticket.get("flagged_for_review") else "High")

            st.markdown(f"**Routing Rationale:** {ticket.get('routing_explanation')}")
            st.markdown(f"**Priority Factors:** {ticket.get('priority_factors')}")

            if ticket.get("flagged_for_review"):
                st.warning("⚠️ **Flagged for Human Review:** Low routing confidence score. Human-in-the-loop review recommended before queue dispatch.")

            st.markdown("#### Complete Structured JSON Ticket")
            st.json(ticket)

            st.markdown("---")
            if not st.session_state.ticket_submitted:
                if st.button("🚀 Confirm & Submit Ticket to Resolver Queue", type="primary", use_container_width=True):
                    st.session_state.ticket_submitted = True
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"🎉 **Ticket Successfully Dispatched!**\n\nYour incident **`{ticket.get('ticket_id')}`** has been routed to **{ticket.get('suggested_resolver_group')}** with priority **{ticket.get('priority')}**."
                    })
                    st.rerun()
            else:
                st.success(f"✅ Ticket `{ticket.get('ticket_id')}` has been officially submitted and dispatched.")

    # User Input Field
    if user_input := st.chat_input("Type your response or issue description here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})

        try:
            with st.spinner("Analyzing request with AI Helpdesk Agents..."):
                response = requests.post(
                    f"{BACKEND_URL}/api/intake",
                    json={"session_id": st.session_state.session_id, "message": user_input},
                    timeout=20
                )
                if response.status_code == 200:
                    res_data = response.json()
                    st.session_state.extracted_data = res_data.get("extracted_data", {})
                    st.session_state.missing_fields = res_data.get("missing_fields", [])
                    st.session_state.stage = res_data.get("stage", "intake")

                    if res_data.get("guidance"):
                        st.session_state.current_guidance = res_data.get("guidance")

                    bot_reply = res_data.get("reply", "Processing complete.")
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    st.rerun()
                else:
                    st.error(f"Backend error: {response.status_code} - {response.text}")
        except requests.exceptions.ConnectionError:
            err = "⚠️ Error: Flask backend is not reachable. Ensure `python app.py` is running on port 5001."
            st.session_state.messages.append({"role": "assistant", "content": err})
            st.rerun()

# Knowledge Base Viewer Tab
with tab_kb:
    st.header("📚 Local Support Knowledge Base")
    st.caption("Active support articles indexed for RAG self-service guidance.")

    kb_dir = os.path.join(os.path.dirname(__file__), "data", "knowledge_base")
    articles = glob.glob(os.path.join(kb_dir, "*.md"))
    if not articles:
        st.info("No knowledge articles found. Upload one via the sidebar!")
    else:
        for art_path in sorted(articles):
            filename = os.path.basename(art_path)
            with open(art_path, "r", encoding="utf-8") as f:
                content = f.read()
            with st.expander(f"📄 {filename}", expanded=False):
                st.markdown(content)

# Audit Log Viewer Tab
with tab_audit:
    st.header("🛡️ System Audit Trail & Evaluation")
    st.caption("Human-in-the-loop tracking, agent decisions, tool invocations, and confidence logs.")

    if st.button("🔄 Refresh Audit Log"):
        st.rerun()

    try:
        log_res = requests.get(f"{BACKEND_URL}/api/audit_logs?limit=40", timeout=5)
        if log_res.status_code == 200:
            logs = log_res.json().get("logs", [])
            if not logs:
                st.info("No audit logs recorded yet in this session.")
            else:
                for entry in logs:
                    with st.expander(f"⏱️ {entry.get('timestamp')} | [{entry.get('agent_role')}] - {entry.get('action')}"):
                        st.json(entry.get("details", {}))
        else:
            st.error("Failed to load audit logs.")
    except Exception as e:
        st.info(f"Unable to fetch logs: {e}")