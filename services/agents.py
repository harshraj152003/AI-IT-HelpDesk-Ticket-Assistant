import json
import uuid
from datetime import datetime
from services.tools import (
    client, CHAT_MODEL, lookup_asset, calculate_priority, 
    check_known_outages, check_duplicate_tickets, 
    retrieve_knowledge_articles, get_resolver_groups
)
from services.audit_logger import log_audit_event

CONFIDENCE_THRESHOLD = 0.80

class IssueIntakeAgent:
    """Agent 1: Conducts conversational information extraction, remembers context, and asks only for missing details."""
    
    def __init__(self):
        self.role_name = "Issue Intake Agent"

    def process_turn(self, session: dict, user_message: str) -> dict:
        extracted = session.get("extracted_data", {
            "user": None,
            "device": None,
            "application": None,
            "location": None,
            "impact": None,
            "urgency": None,
            "attempted_fixes": [],
            "description": ""
        })

        if not extracted.get("description"):
            extracted["description"] = user_message
            
        # Call LLM for slot extraction
        prompt = f"""You are the Issue Intake Agent for an enterprise IT Helpdesk.
Extract IT incident parameters from the user's latest message, while preserving and updating current known state.

Current Known State:
{json.dumps(extracted, indent=2)}

User's Latest Message: "{user_message}"

Instructions:
1. Extract or update any of the following fields if mentioned:
   - "user": employee username or name (e.g., alice, bob, charlie)
   - "device": hardware model, asset tag, or OS (e.g., MacBook Pro M2, Dell Latitude, ThinkPad, AST-101)
   - "application": software or system involved (e.g., Cisco AnyConnect VPN, Outlook, Badge Access, WiFi, M365). If the issue is purely physical workstation/hardware (e.g., battery, screen, keyboard, charger), set "application" to "Hardware & Peripherals".
   - "location": office location or city (e.g., New York, London, Tokyo, Remote)
   - "impact": High, Medium, or Low (High=blocks whole team/critical workflow, Medium=single user blocked with partial workaround, Low=minor convenience/cosmetic)
   - "urgency": High, Medium, or Low (High=immediate tight deadline/outage, Medium=business day response needed, Low=can wait several days)
   - "attempted_fixes": list of actions already taken by user (e.g., "restarted laptop", "cleared cache", "reinstalled app")
   - "summary": concise 1-sentence technical description of the problem.

2. If a field was already established and not contradicted, do NOT overwrite it with null.
3. Return valid JSON only with keys: "extracted", "newly_detected_fixes" (list of strings).
"""
        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You extract structured IT incident parameters into JSON format."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            parsed = json.loads(resp.choices[0].message.content)
            llm_extracted = parsed.get("extracted", {})
            
            # Merge fields into extracted
            for k in ["user", "device", "application", "location", "impact", "urgency"]:
                if llm_extracted.get(k):
                    extracted[k] = llm_extracted[k]
                    
            if llm_extracted.get("summary") and not extracted.get("description"):
                extracted["description"] = llm_extracted["summary"]
                
            # Merge attempted fixes
            new_fixes = parsed.get("newly_detected_fixes", [])
            for fix in new_fixes:
                if fix and fix not in extracted["attempted_fixes"]:
                    extracted["attempted_fixes"].append(fix)
                    
        except Exception as e:
            print(f"Error in LLM slot extraction: {e}")
            
        # Tool call: Asset Lookup if user or device is provided
        asset_info = None
        if extracted.get("user") or extracted.get("device"):
            lookup_key = extracted.get("user") or extracted.get("device")
            asset_info = lookup_asset(lookup_key)
            if asset_info:
                if not extracted.get("device") or extracted["device"] == "laptop":
                    extracted["device"] = f"{asset_info.get('device_name')} (Asset: {asset_info.get('asset_id')})"
                if not extracted.get("location"):
                    extracted["location"] = asset_info.get("location")
                if not extracted.get("user") and asset_info.get("user"):
                    extracted["user"] = asset_info.get("user")
                    
                log_audit_event(session.get("session_id", "default"), self.role_name, "tool_asset_lookup", {
                    "lookup_key": lookup_key,
                    "result": asset_info
                })

        session["extracted_data"] = extracted

        # Check required fields
        required = ["application", "device", "location", "impact", "urgency"]
        missing = [f for f in required if not extracted.get(f)]

        is_complete = len(missing) == 0

        # Generate conversational response
        if is_complete:
            reply = (
                f"Thank you. I have collected all essential incident details:\n"
                f"- **Application/System**: {extracted.get('application')}\n"
                f"- **Device**: {extracted.get('device')}\n"
                f"- **Location**: {extracted.get('location')}\n"
                f"- **Impact & Urgency**: Impact={extracted.get('impact')}, Urgency={extracted.get('urgency')}\n"
                f"- **Attempted Fixes Recorded**: {', '.join(extracted.get('attempted_fixes')) if extracted.get('attempted_fixes') else 'None reported yet'}\n\n"
                f"Let me now check for matching support articles and active outages before proceeding."
            )
        else:
            # Generate targeted follow-up question asking ONLY for what is missing
            follow_up_prompt = f"""You are the Issue Intake Agent. Generate a polite, concise follow-up response (1-2 sentences).
Already Known:
- Application: {extracted.get('application')}
- Device: {extracted.get('device')}
- Location: {extracted.get('location')}
- Impact: {extracted.get('impact')}
- Urgency: {extracted.get('urgency')}
- Attempted fixes: {extracted.get('attempted_fixes')}

Missing fields to ask for: {missing}

Instructions:
Acknowledge what is already known briefly, and ask ONLY for the missing fields ({', '.join(missing)}).
Do not repeat questions for fields that are already known. Be concise and professional.
"""
            try:
                follow_up_resp = client.chat.completions.create(
                    model=CHAT_MODEL,
                    messages=[
                        {"role": "system", "content": "You are a helpful IT helpdesk conversational agent."},
                        {"role": "user", "content": follow_up_prompt}
                    ],
                    temperature=0.3
                )
                reply = follow_up_resp.choices[0].message.content.strip()
            except Exception:
                missing_str = ", ".join([f"**{m}**" for m in missing])
                reply = f"Could you please share your {missing_str}?"

        log_audit_event(session.get("session_id", "default"), self.role_name, "conversational_intake_turn", {
            "user_message": user_message,
            "extracted": extracted,
            "missing_fields": missing,
            "is_complete": is_complete
        })

        return {
            "status": "intake_complete" if is_complete else "gathering_info",
            "reply": reply,
            "extracted_data": extracted,
            "missing_fields": missing,
            "is_complete": is_complete
        }


class KnowledgeRetrievalAgent:
    """Agent 2: RAG retrieval over support articles, checks for duplicates & outages, recommends approved self-service steps."""

    def __init__(self):
        self.role_name = "Knowledge Retrieval Agent"

    def retrieve_guidance(self, session_data: dict) -> dict:
        extracted = session_data.get("extracted_data", {})
        query = f"{extracted.get('application', '')} {extracted.get('description', '')} {extracted.get('device', '')}"
        location = extracted.get("location")
        user = extracted.get("user")

        # Step 1: Check known outages (Innovative Workflow 2)
        outages = check_known_outages(query, location=location)

        # Step 2: Check duplicate tickets
        duplicates = check_duplicate_tickets(query, user=user)

        # Step 3: Retrieve matching knowledge articles & approved steps
        articles = retrieve_knowledge_articles(query, top_k=2)

        # Synthesize recommended steps with source citation
        top_article = articles[0] if articles else None
        recommended_step = None
        source_citation = None

        if top_article:
            source_citation = f"KB Article: [{top_article['title']}] (Source: `{top_article['source_file']}`)"
            recommended_step = top_article['approved_steps']

        result = {
            "has_outage": len(outages) > 0,
            "outages": outages,
            "has_duplicate": len(duplicates) > 0,
            "duplicates": duplicates,
            "articles": articles,
            "top_article": top_article,
            "recommended_step": recommended_step,
            "source_citation": source_citation
        }

        log_audit_event(session_data.get("session_id", "default"), self.role_name, "retrieve_guidance", {
            "query": query,
            "outages_found": len(outages),
            "duplicates_found": len(duplicates),
            "top_article": top_article.get("source_file") or top_article.get("filename") if top_article else None
        })

        return result

    def handle_resolution_feedback(self, session: dict, resolved: bool, user_notes: str = "") -> dict:
        """Innovative Workflow 4: Capture whether the step worked and use outcome to improve retrieval/routing."""
        extracted = session.get("extracted_data", {})
        session_id = session.get("session_id", "default")

        if resolved:
            log_audit_event(session_id, self.role_name, "resolution_feedback", {
                "resolved": True,
                "notes": user_notes,
                "outcome": "Resolved via self-service step. No queue escalation required."
            })
            return {
                "status": "self_resolved",
                "message": "🎉 Great! We're glad the self-service steps resolved your issue. Your session is now closed without creating an escalation ticket."
            }
        else:
            # Append recommended step to attempted fixes
            guidance = session.get("current_guidance") or {}
            top_art = guidance.get("top_article") or {}
            recent_step = top_art.get("title", "Standard self-service procedure")
            attempt_entry = f"Self-service step from {recent_step} was attempted but did not resolve the issue."
            if attempt_entry not in extracted["attempted_fixes"]:
                extracted["attempted_fixes"].append(attempt_entry)
            
            session["extracted_data"] = extracted

            log_audit_event(session_id, self.role_name, "resolution_feedback", {
                "resolved": False,
                "notes": user_notes,
                "outcome": "Self-service unsuccessful. Escalating to Ticket Routing Agent."
            })
            return {
                "status": "escalate_to_routing",
                "message": "Understood. Since the self-service steps did not resolve the issue, I have recorded your attempt in the diagnostics log and am preparing your ticket for routing."
            }


class TicketRoutingAgent:
    """Agent 3: Smart triage combining rule-based priority with semantic classification, explanations, and JSON generation."""

    def __init__(self):
        self.role_name = "Ticket Routing Agent"

    def prepare_and_route_ticket(self, session: dict) -> dict:
        extracted = session.get("extracted_data", {})
        resolver_groups = get_resolver_groups()

        # Step 1: Rule-based priority calculation
        priority_info = calculate_priority(
            extracted.get("impact", "Medium"),
            extracted.get("urgency", "Medium")
        )

        # Step 2: Semantic classification and routing explanation via LLM
        prompt = f"""You are the Ticket Routing Agent in an enterprise IT Helpdesk.
Determine the most appropriate resolver group, routing justification, and confidence score for this incident.

Incident Record:
- Application / System: {extracted.get('application')}
- Problem Description: {extracted.get('description')}
- Device & Diagnostics: {extracted.get('device')}, Location: {extracted.get('location')}
- Attempted Fixes: {extracted.get('attempted_fixes')}
- Priority Rule Assignment: {priority_info.get('priority')} ({priority_info.get('reasoning')})

Available Resolver Groups:
{json.dumps(resolver_groups, indent=2)}

Instructions:
1. Select the single best matching resolver group name.
2. Provide a clear, human-readable routing explanation (1-2 sentences) showing why this group was selected.
3. Compute a confidence score between 0.00 and 1.00 based on clarity and category match.
4. Provide a refined technical summary.
5. Return JSON format with keys:
   - "suggested_resolver_group": string
   - "routing_explanation": string
   - "confidence": float (e.g., 0.95)
   - "technical_summary": string
"""
        routing_decision = {
            "suggested_resolver_group": "IT-Service-Desk",
            "routing_explanation": "Default front-line triage group assigned for review.",
            "confidence": 0.70,
            "technical_summary": extracted.get("description", "IT Issue")
        }

        try:
            resp = client.chat.completions.create(
                model=CHAT_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": "You are an expert IT triage and ticket routing specialist."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            routing_decision = json.loads(resp.choices[0].message.content)
        except Exception as e:
            print(f"Error in LLM routing: {e}")

        confidence = float(routing_decision.get("confidence", 0.75))
        flagged_for_review = confidence < CONFIDENCE_THRESHOLD

        ticket_id = f"INC-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        final_ticket = {
            "ticket_id": ticket_id,
            "category": extracted.get("application", "General IT"),
            "summary": routing_decision.get("technical_summary", extracted.get("description")),
            "diagnostics": {
                "device": extracted.get("device", "Unspecified"),
                "location": extracted.get("location", "Unspecified"),
                "user": extracted.get("user", "Unspecified"),
                "attempted_fixes": extracted.get("attempted_fixes", [])
            },
            "evidence": f"Impact: {extracted.get('impact')}, Urgency: {extracted.get('urgency')}. SLA Target: {priority_info.get('sla_hours')} hours.",
            "priority": priority_info.get("priority"),
            "priority_factors": priority_info.get("reasoning"),
            "suggested_resolver_group": routing_decision.get("suggested_resolver_group"),
            "routing_explanation": routing_decision.get("routing_explanation"),
            "confidence": round(confidence, 2),
            "flagged_for_review": flagged_for_review,
            "status": "Ready for Submission" if not flagged_for_review else "Pending L1 Triage Review"
        }

        log_audit_event(session.get("session_id", "default"), self.role_name, "generate_ticket_route", {
            "ticket_id": ticket_id,
            "priority": final_ticket["priority"],
            "resolver_group": final_ticket["suggested_resolver_group"],
            "confidence": confidence,
            "flagged_for_review": flagged_for_review
        })

        return final_ticket