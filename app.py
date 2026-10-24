import os
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from services.agents import IssueIntakeAgent, KnowledgeRetrievalAgent, TicketRoutingAgent
from services.audit_logger import log_audit_event, get_recent_audit_logs

load_dotenv()

app = Flask(__name__)

# In-memory session store
sessions = {}

intake_agent = IssueIntakeAgent()
knowledge_agent = KnowledgeRetrievalAgent()
routing_agent = TicketRoutingAgent()

def get_or_create_session(session_id: str) -> dict:
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "conversation_history": [],
            "extracted_data": {
                "user": None,
                "device": None,
                "application": None,
                "location": None,
                "impact": None,
                "urgency": None,
                "attempted_fixes": [],
                "description": ""
            },
            "current_guidance": None,
            "generated_ticket": None,
            "stage": "intake" # intake -> guidance_pending -> ticket_ready -> submitted / self_resolved
        }
    return sessions[session_id]

@app.route("/api/intake", methods=["POST"])
def handle_intake():
    data = request.json or {}
    session_id = data.get("session_id", "default_session")
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    session = get_or_create_session(session_id)
    session["conversation_history"].append({"role": "user", "content": user_message})

    # Step 1: Conversational Information Extraction via Issue Intake Agent
    intake_result = intake_agent.process_turn(session, user_message)

    response_payload = {
        "status": intake_result["status"],
        "reply": intake_result["reply"],
        "extracted_data": intake_result["extracted_data"],
        "missing_fields": intake_result["missing_fields"],
        "is_complete": intake_result["is_complete"],
        "guidance": None,
        "stage": session["stage"]
    }

    # Step 2: If intake is complete, invoke Knowledge Retrieval Agent
    if intake_result["is_complete"]:
        session["stage"] = "guidance_pending"
        guidance = knowledge_agent.retrieve_guidance(session)
        session["current_guidance"] = guidance
        response_payload["guidance"] = guidance
        response_payload["stage"] = "guidance_pending"

    session["conversation_history"].append({"role": "assistant", "content": intake_result["reply"]})
    return jsonify(response_payload)

@app.route("/api/feedback", methods=["POST"])
def handle_feedback():
    data = request.json or {}
    session_id = data.get("session_id", "default_session")
    resolved = bool(data.get("resolved", False))
    notes = data.get("notes", "")

    session = get_or_create_session(session_id)
    feedback_result = knowledge_agent.handle_resolution_feedback(session, resolved, notes)

    if resolved:
        session["stage"] = "self_resolved"
        return jsonify({
            "status": "self_resolved",
            "message": feedback_result["message"],
            "stage": "self_resolved"
        })
    else:
        # Self service did not resolve, proceed to Ticket Routing Agent
        session["stage"] = "ticket_ready"
        ticket = routing_agent.prepare_and_route_ticket(session)
        session["generated_ticket"] = ticket

        return jsonify({
            "status": "ticket_ready",
            "message": feedback_result["message"],
            "ticket": ticket,
            "stage": "ticket_ready"
        })

@app.route("/api/route_ticket", methods=["POST"])
def route_ticket_direct():
    data = request.json or {}
    session_id = data.get("session_id", "default_session")
    session = get_or_create_session(session_id)

    ticket = routing_agent.prepare_and_route_ticket(session)
    session["generated_ticket"] = ticket
    session["stage"] = "ticket_ready"

    return jsonify({
        "status": "ticket_ready",
        "ticket": ticket
    })

@app.route("/api/upload_doc", methods=["POST"])
def upload_document():
    """Upload support articles, service categories, priority rules, or resolver mappings."""
    if 'file' not in request.files:
        return jsonify({"error": "No file part in request"}), 400
    
    file = request.files['file']
    doc_type = request.form.get("doc_type", "support_article")

    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400

    filename = file.filename
    base_dir = os.path.dirname(__file__)

    if doc_type == "support_article":
        target_dir = os.path.join(base_dir, "data", "knowledge_base")
    elif doc_type == "priority_rules":
        target_dir = base_dir
        filename = "priority_rules.csv"
    elif doc_type == "assets":
        target_dir = base_dir
        filename = "assets.csv"
    elif doc_type == "resolver_groups":
        target_dir = os.path.join(base_dir, "data")
        filename = "resolver_groups.json"
    elif doc_type == "known_outages":
        target_dir = os.path.join(base_dir, "data")
        filename = "known_outages.json"
    else:
        target_dir = os.path.join(base_dir, "data")

    os.makedirs(target_dir, exist_ok=True)
    save_path = os.path.join(target_dir, filename)
    file.save(save_path)

    log_audit_event("system", "Document Management", "upload_file", {
        "filename": filename,
        "doc_type": doc_type,
        "save_path": save_path
    })

    return jsonify({
        "status": "success",
        "message": f"Successfully uploaded and indexed {filename} under {doc_type}.",
        "path": save_path
    })

@app.route("/api/audit_logs", methods=["GET"])
def get_audit_trail():
    limit = int(request.args.get("limit", 50))
    logs = get_recent_audit_logs(limit)
    return jsonify({"logs": logs})

@app.route("/api/session/<session_id>", methods=["GET"])
def get_session_info(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(sessions[session_id])

@app.route("/api/reset", methods=["POST"])
def reset_session():
    data = request.json or {}
    session_id = data.get("session_id", "default_session")
    if session_id in sessions:
        del sessions[session_id]
    return jsonify({"status": "reset", "session_id": session_id})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)