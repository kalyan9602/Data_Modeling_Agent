# 🧠 DataMind Agent — Streamlit POC

A conversational data modeling agent powered by **AWS Bedrock (Claude)**. 
Paste or upload a source mapping sheet and the agent will design a star schema, 
generate an ER diagram, field lineage, DDL SQL, and a Python ETL pipeline.

---

## 📁 Project Structure

```
datamind/
├── app.py                  ← Main Streamlit app (run this)
├── requirements.txt        ← Python dependencies
├── .env.example            ← Copy to .env and add your AWS keys
└── utils/
    ├── bedrock_client.py   ← AWS Bedrock API calls (boto3)
    ├── generators.py       ← DDL / ETL / Lineage CSV generators
    ├── prompts.py          ← Agent system prompt
    └── demo_data.py        ← Canned demo responses (no-credential mode)
```

---

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or newer
- An AWS account with Bedrock access enabled
- Claude model enabled in your region (us-east-1 recommended)

### 2. Install dependencies

```bash
cd datamind
pip install -r requirements.txt
```

### 3. (Optional) Set AWS credentials in .env

You can also just enter them in the app sidebar at runtime.

```bash
cp .env.example .env
# Edit .env and add your AWS keys
```

### 4. Run the app

```bash
streamlit run app.py
```

The app opens automatically at **http://localhost:8501**

---

## 🎭 Demo Mode

If you don't enter AWS credentials, the app runs in **demo mode** — it cycles 
through canned E-commerce responses so you can see the full workflow without 
needing an AWS account.

---

## 💬 How to Use

1. **Describe your source** — type the domain (e.g. "E-commerce orders") or paste field names
2. **Answer the agent's questions** — grain, dimensions, KPIs, SCD strategy
3. **Upload a CSV** — use the sidebar file uploader for your mapping sheet
4. **View outputs** — ER Diagram, Field Lineage, Table Definitions tabs update live
5. **Download** — DDL SQL, ETL Python, Lineage CSV, or everything as a ZIP

---

## 📋 Sample Input (paste into chat)

```
source_field,data_type,description
OrderID,VARCHAR(50),Unique order identifier
OrderDate,DATETIME,Date order was placed
CustomerID,VARCHAR(50),Customer identifier
ProductSKU,VARCHAR(50),Product stock keeping unit
Quantity,INTEGER,Units ordered
UnitSalePrice,DECIMAL(18,2),Price per unit
DiscountPct,DECIMAL(5,2),Discount percentage
OrderStatus,VARCHAR(20),Fulfillment status
```

---

## ☁️ AWS Bedrock Setup

1. Log in to [AWS Console](https://console.aws.amazon.com)
2. Go to **Amazon Bedrock → Model access**
3. Enable **Claude 3.5 Sonnet v2** (or Haiku for lower cost)
4. Create an IAM user with `AmazonBedrockFullAccess` policy
5. Generate access keys and paste them into the app sidebar

---

## 🔧 Extending the App

| What                       | Where                        |
|----------------------------|------------------------------|
| Change the agent behavior  | `utils/prompts.py`           |
| Add download formats       | `utils/generators.py`        |
| Add new output tabs        | `app.py` (tab section)       |
| Customize demo responses   | `utils/demo_data.py`         |
| Add database connectivity  | `utils/bedrock_client.py`    |
