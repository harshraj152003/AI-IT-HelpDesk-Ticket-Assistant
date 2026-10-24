import os
import json
import glob
import pandas as pd
import numpy as np
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
KB_DIR = os.path.join(DATA_DIR, "knowledge_base")
ASSETS_CSV = os.path.join(BASE_DIR, "assets.csv")
PRIORITY_RULES_CSV = os.path.join(BASE_DIR, "priority_rules.csv")
OUTAGES_JSON = os.path.join(DATA_DIR, "known_outages.json")
TICKETS_JSON = os.path.join(DATA_DIR, "historical_tickets.json")
RESOLVERS_JSON = os.path.join(DATA_DIR, "resolver_groups.json")

# Initialize OpenAI client with corporate GenAILab endpoint and proxy bypass
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-Ss6JJRmnYpgIUZIEjZQgqQ")
http_client = httpx.Client(verify=False)
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://genailab.tcs.in",
    http_client=http_client
)

EMBEDDING_MODEL = "azure/genailab-maas-text-embedding-3-large"
CHAT_MODEL = "azure/genailab-maas-gpt-4o-mini"

def get_text_embedding(text: str) -> np.ndarray:
    """Computes dense embedding using corporate API, with fallback to empty array if unavailable."""
    try:
        clean_text = text.replace("\n", " ").strip()
        resp = client.embeddings.create(model=EMBEDDING_MODEL, input=clean_text)
        return np.array(resp.data[0].embedding, dtype=np.float32)
    except Exception as e:
        return None

def lookup_asset(identifier: str) -> dict:
    """Tool: Looks up asset by user, asset_id, or device name in assets.csv."""
    if not os.path.exists(ASSETS_CSV) or not identifier:
        return None
    try:
        df = pd.read_csv(ASSETS_CSV)
        id_str = str(identifier).strip().lower()
        
        # Exact match or substring on asset_id, user, device_name
        for _, row in df.iterrows():
            if (id_str == str(row.get('asset_id', '')).lower() or
                id_str == str(row.get('user', '')).lower() or
                id_str in str(row.get('device_name', '')).lower() or
                str(row.get('device_name', '')).lower() in id_str):
                return row.to_dict()
    except Exception as e:
        print(f"Error in lookup_asset: {e}")
    return None

def calculate_priority(impact: str, urgency: str, category: str = None) -> dict:
    """Tool: Calculates priority from impact and urgency matrix, explaining the factors."""
    norm_impact = str(impact or "Low").capitalize()
    norm_urgency = str(urgency or "Low").capitalize()
    
    # Defaults
    priority = "P3 - Moderate"
    sla_hours = 8
    rule_desc = "Standard baseline resolution rule."

    if os.path.exists(PRIORITY_RULES_CSV):
        try:
            df = pd.read_csv(PRIORITY_RULES_CSV)
            match = df[(df['impact'].str.lower() == norm_impact.lower()) & 
                       (df['urgency'].str.lower() == norm_urgency.lower())]
            if not match.empty:
                priority = match.iloc[0]['priority']
                sla_hours = int(match.iloc[0].get('base_sla_hours', 8))
                rule_desc = match.iloc[0].get('description', rule_desc)
        except Exception as e:
            print(f"Error reading priority rules: {e}")

    # Generate explanatory breakdown
    reasoning = (
        f"Assigned {priority} based on Impact='{norm_impact}' and Urgency='{norm_urgency}'. "
        f"Factor Analysis: {rule_desc} Target response SLA is within {sla_hours} hours."
    )
    
    return {
        "priority": priority,
        "impact": norm_impact,
        "urgency": norm_urgency,
        "sla_hours": sla_hours,
        "reasoning": reasoning
    }

def check_known_outages(description: str, location: str = None) -> list:
    """Tool: Compares the user complaint with active known outages using semantic similarity and keywords."""
    if not os.path.exists(OUTAGES_JSON) or not description:
        return []
    
    try:
        with open(OUTAGES_JSON, "r", encoding="utf-8") as f:
            outages = json.load(f)
        
        matches = []
        user_emb = get_text_embedding(description)
        
        for outage in outages:
            outage_text = f"{outage.get('service', '')} {outage.get('title', '')} {outage.get('description', '')}"
            similarity = 0.0
            
            if user_emb is not None:
                outage_emb = get_text_embedding(outage_text)
                if outage_emb is not None:
                    similarity = float(np.dot(user_emb, outage_emb) / (np.linalg.norm(user_emb) * np.linalg.norm(outage_emb)))
            else:
                # TF-IDF fallback
                vectorizer = TfidfVectorizer().fit([description, outage_text])
                matrix = vectorizer.transform([description, outage_text])
                similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
            
            # Check location match if provided
            loc_matched = False
            if location and outage.get("affected_locations"):
                for loc in outage["affected_locations"]:
                    if loc.lower() in location.lower() or location.lower() in loc.lower():
                        loc_matched = True
                        break
            
            # Threshold: semantic similarity >= 0.40 or direct keyword / location match
            if similarity >= 0.40 or (loc_matched and similarity >= 0.30):
                match_data = dict(outage)
                match_data["similarity_score"] = round(similarity, 3)
                match_data["location_matched"] = loc_matched
                matches.append(match_data)
        
        # Sort highest similarity first
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches
    except Exception as e:
        print(f"Error checking outages: {e}")
        return []

def check_duplicate_tickets(description: str, user: str = None) -> list:
    """Tool: Detects potential duplicate or recently resolved tickets with high semantic similarity."""
    if not os.path.exists(TICKETS_JSON) or not description:
        return []
    
    try:
        with open(TICKETS_JSON, "r", encoding="utf-8") as f:
            tickets = json.load(f)
            
        user_emb = get_text_embedding(description)
        matches = []
        
        for t in tickets:
            t_text = f"{t.get('summary', '')} {t.get('category', '')} {t.get('resolution', '')}"
            similarity = 0.0
            
            if user_emb is not None:
                t_emb = get_text_embedding(t_text)
                if t_emb is not None:
                    similarity = float(np.dot(user_emb, t_emb) / (np.linalg.norm(user_emb) * np.linalg.norm(t_emb)))
            else:
                vectorizer = TfidfVectorizer().fit([description, t_text])
                matrix = vectorizer.transform([description, t_text])
                similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
                
            if similarity >= 0.55:
                match_entry = dict(t)
                match_entry["similarity_score"] = round(similarity, 3)
                matches.append(match_entry)
                
        matches.sort(key=lambda x: x["similarity_score"], reverse=True)
        return matches
    except Exception as e:
        print(f"Error checking duplicate tickets: {e}")
        return []

def retrieve_knowledge_articles(query: str, top_k: int = 2) -> list:
    """Tool: RAG retriever over local support articles. Returns top articles with source references."""
    kb_files = glob.glob(os.path.join(KB_DIR, "*.md"))
    if not kb_files:
        return []
    
    articles = []
    for filepath in kb_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            filename = os.path.basename(filepath)
            
            # Extract title if present
            title = filename
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line.replace("# ", "").strip()
                    break
                    
            articles.append({
                "filename": filename,
                "title": title,
                "content": content
            })
            
    query_emb = get_text_embedding(query)
    scored = []
    
    for art in articles:
        similarity = 0.0
        if query_emb is not None:
            art_emb = get_text_embedding(art["content"][:1500])
            if art_emb is not None:
                similarity = float(np.dot(query_emb, art_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(art_emb)))
        else:
            vectorizer = TfidfVectorizer().fit([query, art["content"]])
            matrix = vectorizer.transform([query, art["content"]])
            similarity = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
            
        scored.append((similarity, art))
        
    scored.sort(key=lambda x: x[0], reverse=True)
    
    results = []
    for score, art in scored[:top_k]:
        # Extract approved steps section specifically
        steps_text = ""
        in_steps = False
        for line in art["content"].splitlines():
            if "Approved Self-Service Steps" in line:
                in_steps = True
                continue
            elif in_steps and line.startswith("## "):
                break
            elif in_steps:
                steps_text += line + "\n"
                
        results.append({
            "filename": art["filename"],
            "source_file": art["filename"],
            "title": art["title"],
            "similarity_score": round(score, 3),
            "approved_steps": steps_text.strip() if steps_text else art["content"][:600],
            "full_content": art["content"]
        })
        
    return results

def get_resolver_groups() -> list:
    """Tool: Returns available resolver groups and categories."""
    if os.path.exists(RESOLVERS_JSON):
        try:
            with open(RESOLVERS_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []