"""
utils/bedrock_client.py
Handles AWS Bedrock API calls using boto3 (server-side — credentials stay safe).
Falls back to smart demo mode if no credentials are provided.
"""

import json
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class BedrockError(Exception):
    pass


def call_bedrock(
    history: list,
    system_prompt: str,
    region: str,
    access_key: str,
    secret_key: str,
    model_id: str,
) -> str:
    if not access_key or not secret_key:
        return _smart_demo_response(history)

    try:
        client = boto3.client(
            "bedrock-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 8096,
            "system": system_prompt,
            "messages": history,
        }
        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(payload),
        )
        body = json.loads(response["body"].read())
        return body["content"][0]["text"]

    except NoCredentialsError:
        raise BedrockError("Invalid or missing AWS credentials.")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg  = e.response["Error"]["Message"]
        raise BedrockError(f"{code}: {msg}")
    except Exception as e:
        raise BedrockError(f"Unexpected error: {type(e).__name__}: {str(e)}")


def _smart_demo_response(history: list) -> str:
    last_msg = ""
    for m in reversed(history):
        if m["role"] == "user":
            last_msg = m["content"].lower().strip()
            break

    msg_count = sum(1 for m in history if m["role"] == "user")

    greetings = ["hi", "hello", "hey", "howdy", "good morning", "good afternoon", "good evening", "sup", "hiya"]
    if any(last_msg == g or last_msg.startswith(g + " ") or last_msg.startswith(g + ",") for g in greetings):
        return json.dumps({
            "message": "Hey! 👋 Great to have you here. I'm DataMind, your data modeling assistant.\n\nI can take your source system fields and design a complete data model — star schema, ER diagram, DDL SQL, and a Python ETL pipeline.\n\nTo get started, just tell me:\n• What's your source system? (e.g. banking transactions, e-commerce orders, healthcare records)\n• Or paste your field list directly and I'll get to work!",
            "state": "gathering", "questions": [], "model": None
        })

    thanks = ["thanks", "thank you", "thx", "ty", "great", "awesome", "perfect", "nice", "cool", "sounds good", "got it"]
    if any(last_msg.startswith(t) for t in thanks):
        return json.dumps({
            "message": "You're welcome! 😊 Want to continue refining the model, or start on something new?\n\nI can:\n• Add more dimensions (e.g. DIM_SALES_REP, DIM_WAREHOUSE)\n• Create a separate fact table for returns\n• Adjust the grain or SCD strategy\n• Model a completely different source system\n\nJust let me know!",
            "state": "gathering", "questions": [], "model": None
        })

    if "help" in last_msg or "what can you do" in last_msg or "how does" in last_msg:
        return json.dumps({
            "message": "Here's what I can do for you:\n\n📥 Input — paste a CSV mapping sheet, upload a file, or describe your source system in plain English\n\n🏗️ Modeling — I'll design a star or snowflake schema with fact and dimension tables, surrogate keys, and SCD Type 2\n\n📊 Downloads — ER Diagram, Field Lineage CSV, DDL SQL, and a Python ETL pipeline\n\nTry saying: 'I have a banking transactions source system'",
            "state": "gathering", "questions": [], "model": None
        })

    domains = {
        "bank": "banking transactions", "transact": "financial transactions",
        "financ": "financial data", "ecomm": "e-commerce orders",
        "order": "e-commerce orders", "health": "healthcare records",
        "patient": "healthcare patient data", "retail": "retail sales",
        "sales": "sales transactions", "hr": "HR / employee data",
        "employee": "HR data", "payroll": "payroll data",
        "inventory": "inventory management", "crm": "CRM / customer data",
        "logistic": "logistics data", "supply": "supply chain data",
        "insurance": "insurance claims", "claim": "insurance claims",
    }
    detected_domain = None
    for keyword, domain_name in domains.items():
        if keyword in last_msg:
            detected_domain = domain_name
            break

    if detected_domain:
        return json.dumps({
            "message": f"Got it — {detected_domain}! A few quick questions before I start designing:",
            "state": "clarifying",
            "questions": [
                "What's the reporting grain? (e.g. one row per transaction, per day, per account?)",
                "Do you have existing master data or should I create those as dimensions?",
                "Any specific KPIs or metrics you need to measure?",
                "Should any dimensions track historical changes over time (SCD Type 2)?"
            ],
            "model": None
        })

    has_csv_data = (
        ("," in last_msg and len(last_msg.split("\n")) > 3)
        or "source_field" in last_msg
        or "[uploaded:" in last_msg
    )
    if has_csv_data:
        field_count = len([l for l in last_msg.split("\n") if "," in l and len(l) > 5])
        return json.dumps({
            "message": f"I can see your mapping sheet with around {field_count} fields. A couple of quick questions before I start modeling:",
            "state": "clarifying",
            "questions": [
                "What's the business domain? (e.g. banking, e-commerce, healthcare)",
                "What should the reporting grain be?",
                "Any fields that need historical versioning (SCD Type 2)?",
                "Any specific KPIs your team needs to report on?"
            ],
            "model": None
        })

    answering_keywords = ["per ", "yes", "no", "line item", "grain", "scd", "revenue",
                          "kpi", "type 2", "snapshot", "daily", "monthly", "transaction", "each", "one row"]
    if msg_count >= 2 and any(k in last_msg for k in answering_keywords):
        from utils.demo_data import DEMO_RESPONSES
        return json.dumps(DEMO_RESPONSES[1])

    refinements = ["add", "include", "expand", "refine", "update", "change", "modify", "sales rep", "warehouse"]
    if any(k in last_msg for k in refinements):
        return json.dumps({
            "message": "Sure! Which of these would you like to add?",
            "state": "clarifying",
            "questions": [
                "FACT_RETURN — separate fact table for returns?",
                "DIM_SALES_REP — dimension for sales reps with territory?",
                "DIM_WAREHOUSE — fulfillment location dimension?",
                "Something else? Just describe what you need!"
            ],
            "model": None
        })

    return json.dumps({
        "message": "I want to make sure I understand! Could you tell me a bit more?\n\nYou can:\n• Describe your source system (e.g. 'I have banking transaction data')\n• Paste your field list as CSV\n• Upload a mapping sheet via the sidebar\n• Ask me to refine an existing model",
        "state": "gathering", "questions": [], "model": None
    })