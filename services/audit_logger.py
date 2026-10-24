import os
import json
from datetime import datetime

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audit_log.jsonl")

def log_audit_event(session_id: str, agent_role: str, action: str, details: dict):
    """Logs an agent interaction or tool invocation to audit_log.jsonl for governance and auditing."""
    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "agent_role": agent_role,
        "action": action,
        "details": details
    }
    os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)
    with open(AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")
    return event

def get_recent_audit_logs(limit: int = 50):
    """Retrieves recent audit log events."""
    if not os.path.exists(AUDIT_LOG_FILE):
        return []
    logs = []
    with open(AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    logs.append(json.loads(line.strip()))
                except Exception:
                    pass
    return logs[-limit:][::-1]