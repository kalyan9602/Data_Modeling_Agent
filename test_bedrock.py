#!/usr/bin/env python3
"""
test_bedrock.py
Quick connection test for AWS Bedrock — run before starting DataMind.

Usage:
    python test_bedrock.py
    python test_bedrock.py --region us-west-2
    python test_bedrock.py --key AKIA... --secret your_secret
"""

import argparse
import json
import sys
import boto3
from botocore.exceptions import ClientError, NoCredentialsError


# ── CLI args ──────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Test AWS Bedrock connectivity")
parser.add_argument("--region", default="us-east-1",          help="AWS region (default: us-east-1)")
parser.add_argument("--key",    default=None,                  help="AWS Access Key ID (or set env var)")
parser.add_argument("--secret", default=None,                  help="AWS Secret Access Key (or set env var)")
parser.add_argument("--model",  default="us.anthropic.claude-sonnet-4-20250514-v1:0", help="Model ID to test")
args = parser.parse_args()

# ── Helpers ───────────────────────────────────────────────────────────────────
def ok(msg):   print(f"  ✅  {msg}")
def fail(msg): print(f"  ❌  {msg}")
def info(msg): print(f"  ℹ️   {msg}")
def section(title): print(f"\n{'─'*55}\n  {title}\n{'─'*55}")


# ── Test 1: boto3 + credentials resolve ───────────────────────────────────────
section("TEST 1 — Credentials")
try:
    session_kwargs = {"region_name": args.region}
    if args.key and args.secret:
        session_kwargs["aws_access_key_id"]     = args.key
        session_kwargs["aws_secret_access_key"] = args.secret
        info("Using credentials passed via --key / --secret flags")
    else:
        info("No flags given — using credentials from environment / ~/.aws/credentials")

    session = boto3.Session(**session_kwargs)
    identity = session.client("sts").get_caller_identity()
    ok(f"Authenticated as: {identity['Arn']}")
    ok(f"Account ID      : {identity['Account']}")
    ok(f"Region          : {args.region}")
except NoCredentialsError:
    fail("No credentials found. Set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY or pass --key / --secret")
    sys.exit(1)
except ClientError as e:
    fail(f"STS error: {e.response['Error']['Code']} — {e.response['Error']['Message']}")
    sys.exit(1)


# ── Test 2: Bedrock client creation ───────────────────────────────────────────
section("TEST 2 — Bedrock Client")
try:
    bedrock = session.client("bedrock", region_name=args.region)
    ok("bedrock client created")
except Exception as e:
    fail(f"Could not create bedrock client: {e}")
    sys.exit(1)


# ── Test 3: List available models (checks bedrock:ListFoundationModels) ────────
section("TEST 3 — Model Access")
try:
    response  = bedrock.list_foundation_models(byProvider="Anthropic")
    models    = response.get("modelSummaries", [])
    claude_models = [m for m in models if "claude" in m["modelId"].lower()]

    if claude_models:
        ok(f"Found {len(claude_models)} Claude model(s) available in {args.region}:")
        for m in claude_models:
            status = m.get("modelLifecycle", {}).get("status", "ACTIVE")
            print(f"       • {m['modelId']}  [{status}]")
    else:
        fail(f"No Claude models found in region '{args.region}'")
        info("Try --region us-east-1 or us-west-2")

except ClientError as e:
    code = e.response["Error"]["Code"]
    msg  = e.response["Error"]["Message"]
    fail(f"{code}: {msg}")
    if code == "AccessDeniedException":
        info("Your IAM user needs bedrock:ListFoundationModels permission")


# ── Test 4: Actual model invocation ───────────────────────────────────────────
section(f"TEST 4 — Invoke Model\n  Model: {args.model}")
try:
    bedrock_rt = session.client("bedrock-runtime", region_name=args.region)

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 64,
        "messages": [
            {"role": "user", "content": "Reply with exactly: DATAMIND_CONNECTION_OK"}
        ],
    }

    response = bedrock_rt.invoke_model(
        modelId=args.model,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(payload),
    )

    body  = json.loads(response["body"].read())
    reply = body["content"][0]["text"].strip()

    ok(f"Model responded  : {reply}")
    ok(f"Input tokens     : {body['usage']['input_tokens']}")
    ok(f"Output tokens    : {body['usage']['output_tokens']}")
    ok(f"Stop reason      : {body['stop_reason']}")

except ClientError as e:
    code = e.response["Error"]["Code"]
    msg  = e.response["Error"]["Message"]
    fail(f"{code}: {msg}")
    if code == "AccessDeniedException":
        info("Your IAM user needs bedrock:InvokeModel permission")
        info("Also check that model access is granted in the Bedrock console:")
        info("  Bedrock → Model access → Claude 3.5 Sonnet v2 → Access granted")
    elif code == "ValidationException":
        info("Model ID may be wrong or not available in this region")
        info("Try one of the model IDs listed in TEST 3 above")
    elif code == "ResourceNotFoundException":
        info("Model not found — check Model access in Bedrock console")


# ── Summary ───────────────────────────────────────────────────────────────────
section("SUMMARY")
print("""
  If all 4 tests show ✅  — you're ready to run DataMind!
  
  Start the app:
    streamlit run app.py

  If TEST 4 failed:
    1. Go to AWS Console → Bedrock → Model access
    2. Click "Modify model access"
    3. Check the box next to Claude 3.5 Sonnet v2
    4. Click Save — takes ~1 min to activate
    5. Re-run this script
""")
