"""
utils/generators.py
Generates DDL SQL, ETL Python, and Lineage CSV from the model dict.
Used as fallback when the LLM doesn't return these directly (e.g. demo mode).
"""

from datetime import datetime


# ── DDL Generator ─────────────────────────────────────────────────────────────
def generate_ddl(model: dict) -> str:
    """Return a complete DDL SQL script for the model."""
    # If the LLM returned DDL directly, use it
    if model.get("ddl"):
        return model["ddl"]

    # Fallback: generate from tables array
    lines = [
        "-- ============================================================",
        "-- DataMind Agent — DDL Script (auto-generated)",
        f"-- Generated : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "-- Compatible: Amazon Redshift / Snowflake / PostgreSQL",
        "-- ============================================================",
        "",
    ]

    tables = model.get("tables", [])

    # Order: dims first, then facts
    ordered = [t for t in tables if t["type"] != "fact"] + \
              [t for t in tables if t["type"] == "fact"]

    for t in ordered:
        lines += [
            f"-- {t.get('description', t['name'])}",
            f"CREATE TABLE IF NOT EXISTS {t['name']} (",
        ]
        col_lines = []
        pk_cols = []
        for c in t.get("columns", []):
            null_clause = " NOT NULL" if c.get("pk") else ""
            comment     = f"  -- {c['description']}" if c.get("description") else ""
            col_lines.append(f"  {c['name']:<32} {c.get('type','VARCHAR(255)')}{null_clause},{comment}")
            if c.get("pk"):
                pk_cols.append(c["name"])

        # Write columns (strip trailing comma from last before PRIMARY KEY)
        for i, cl in enumerate(col_lines):
            lines.append(cl)

        if pk_cols:
            lines.append(f"  PRIMARY KEY ({', '.join(pk_cols)})")
        else:
            # Remove trailing comma from last column
            if lines[-1].endswith(",") or "," in lines[-1]:
                lines[-1] = lines[-1].replace(",", "", 1).rstrip(",")

        lines += [");", ""]

        # FK constraints
        for c in t.get("columns", []):
            if c.get("fk"):
                parts = c["fk"].split(".")
                if len(parts) == 2:
                    ref_table, ref_col = parts
                    lines += [
                        f"ALTER TABLE {t['name']}",
                        f"  ADD CONSTRAINT fk_{t['name'].lower()}_{c['name'].lower()}",
                        f"  FOREIGN KEY ({c['name']}) REFERENCES {ref_table}({ref_col});",
                        "",
                    ]

        # Indexes for FK columns
        fk_cols = [c["name"] for c in t.get("columns", []) if c.get("fk")]
        for col in fk_cols:
            lines.append(f"CREATE INDEX idx_{t['name'].lower()}_{col.lower()} ON {t['name']} ({col});")
        if fk_cols:
            lines.append("")

    return "\n".join(lines)


# ── ETL Generator ─────────────────────────────────────────────────────────────
def generate_etl(model: dict) -> str:
    """Return a complete Python ETL script for the model."""
    # If the LLM returned ETL directly, use it
    if model.get("etl"):
        return model["etl"]

    # Fallback: generate skeleton from tables + lineage
    tables    = model.get("tables", [])
    lineage   = model.get("lineage", [])
    dim_names = [t["name"] for t in tables if t["type"] == "dimension"]
    fact_names= [t["name"] for t in tables if t["type"] == "fact"]
    all_names = [t["name"] for t in tables]

    def lineage_for(table):
        return [l for l in lineage if l.get("target_table") == table]

    lines = [
        '#!/usr/bin/env python3',
        '"""',
        'DataMind Agent — ETL Pipeline (auto-generated)',
        f'Generated : {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'Tables    : {", ".join(all_names)}',
        '"""',
        '',
        'import hashlib',
        'import logging',
        'import os',
        'from datetime import date, datetime',
        '',
        'import pandas as pd',
        '',
        '# ── Config ───────────────────────────────────────────────────',
        'SOURCE_FILE = "source_data.csv"',
        'OUTPUT_DIR  = "./output"',
        'logging.basicConfig(',
        '    level=logging.INFO,',
        '    format="%(asctime)s [%(levelname)s] %(message)s"',
        ')',
        'logger = logging.getLogger(__name__)',
        'os.makedirs(OUTPUT_DIR, exist_ok=True)',
        '',
        '',
        '# ── Helpers ──────────────────────────────────────────────────',
        'def sk(natural_key) -> int:',
        '    """Stable integer surrogate key from a natural key."""',
        '    return int(hashlib.md5(str(natural_key).encode()).hexdigest()[:8], 16)',
        '',
        '',
        'def to_date_sk(dt) -> int:',
        '    """Convert date/datetime to YYYYMMDD integer."""',
        '    if pd.isna(dt):',
        '        return 19000101',
        '    return int(pd.to_datetime(dt).strftime("%Y%m%d"))',
        '',
        '',
        'def save(df: pd.DataFrame, table: str):',
        '    path = f"{OUTPUT_DIR}/{table}.csv"',
        '    df.to_csv(path, index=False)',
        '    logger.info(f"  ✓ {table}: {len(df):,} rows → {path}")',
        '',
        '',
        'def scd2_upsert(existing: pd.DataFrame, incoming: pd.DataFrame,',
        '                natural_key: str, tracked_cols: list, sk_col: str) -> pd.DataFrame:',
        '    """Apply SCD Type 2 logic: expire changed records, insert new versions."""',
        '    today = date.today()',
        '    result = []',
        '    curr = existing[existing["is_current"] == True] if not existing.empty else pd.DataFrame()',
        '    for _, row in incoming.iterrows():',
        '        nk    = row[natural_key]',
        '        match = curr[curr[natural_key] == nk] if not curr.empty else pd.DataFrame()',
        '        if match.empty:',
        '            row = row.copy()',
        '            row[sk_col]          = sk(nk)',
        '            row["effective_from"] = today',
        '            row["effective_to"]   = date(9999, 12, 31)',
        '            row["is_current"]     = True',
        '        else:',
        '            existing_row = match.iloc[0]',
        '            changed = any(str(existing_row.get(c,"")) != str(row.get(c,"")) for c in tracked_cols)',
        '            if changed:',
        '                # Expire old',
        '                old = existing_row.copy()',
        '                old["effective_to"] = today',
        '                old["is_current"]   = False',
        '                result.append(old)',
        '                # New version',
        '                row = row.copy()',
        '                row[sk_col]          = sk(f"{nk}_{today}")',
        '                row["effective_from"] = today',
        '                row["effective_to"]   = date(9999, 12, 31)',
        '                row["is_current"]     = True',
        '            else:',
        '                row = existing_row',
        '        result.append(row)',
        '    return pd.DataFrame(result) if result else pd.DataFrame(columns=incoming.columns)',
        '',
        '',
        '# ── Extract ──────────────────────────────────────────────────',
        'def extract() -> pd.DataFrame:',
        '    logger.info(f"[EXTRACT] {SOURCE_FILE}")',
        '    df = pd.read_csv(SOURCE_FILE, dtype=str)',
        '    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")',
        '    logger.info(f"  {len(df):,} rows | {list(df.columns)}")',
        '    return df',
        '',
    ]

    # Dimension transforms
    for dim in dim_names:
        lins = lineage_for(dim)
        lines += [
            '',
            f'# ── Transform: {dim} {"─"*(50-len(dim))}',
            f'def transform_{dim.lower()}(df: pd.DataFrame) -> pd.DataFrame:',
            f'    logger.info("[TRANSFORM] {dim}")',
            '    out = pd.DataFrame()',
        ]
        for l in lins:
            src = l.get("source_field", "???").lower().replace(" ", "_").replace("+","").strip()
            tgt = l.get("target_column", "???")
            logic = l.get("logic", "")
            tf  = l.get("transformation", "direct")
            if tf == "direct":
                lines.append(f'    out["{tgt}"] = df.get("{src}", "")  # direct')
            elif tf == "calculated":
                lines.append(f'    # {logic}')
                lines.append(f'    out["{tgt}"] = None  # TODO: implement calculation')
            elif tf == "lookup":
                lines.append(f'    out["{tgt}"] = df.get("{src}", "")  # lookup/enrich')
            else:
                lines.append(f'    out["{tgt}"] = df.get("{src}", "")  # {tf}: {logic}')
        lines += [
            '    out["effective_from"] = date.today()',
            '    out["effective_to"]   = date(9999, 12, 31)',
            '    out["is_current"]     = True',
            f'    return out.drop_duplicates().reset_index(drop=True)',
            '',
        ]

    # Fact transforms
    for fact in fact_names:
        lins = lineage_for(fact)
        lines += [
            '',
            f'# ── Transform: {fact} {"─"*(50-len(fact))}',
            f'def transform_{fact.lower()}(df: pd.DataFrame, dim_lookups: dict) -> pd.DataFrame:',
            f'    logger.info("[TRANSFORM] {fact}")',
            '    out = pd.DataFrame()',
        ]
        for l in lins:
            src = l.get("source_field","???").lower().replace(" ","_").replace("+","").strip()
            tgt = l.get("target_column","???")
            tf  = l.get("transformation","direct")
            logic = l.get("logic","")
            if tf == "lookup":
                lines.append(f'    # {logic}')
                lines.append(f'    # out["{tgt}"] = df["{src}"].map(dim_lookups.get("{tgt}", {{}}))')
            elif tf == "calculated":
                lines.append(f'    # {logic}')
                lines.append(f'    out["{tgt}"] = None  # TODO: {logic}')
            elif tf == "derived":
                lines.append(f'    out["{tgt}"] = df.get("{src}", pd.NaT).apply(to_date_sk)  # {logic}')
            else:
                lines.append(f'    out["{tgt}"] = df.get("{src}", "")  # {tf}')
        lines += [
            '    out["load_ts"] = datetime.now()',
            '    return out.reset_index(drop=True)',
            '',
        ]

    # Main
    lines += [
        '',
        '# ── Main ─────────────────────────────────────────────────────',
        'def main():',
        '    logger.info("=" * 60)',
        '    logger.info("  DataMind ETL Pipeline — Start")',
        '    logger.info("=" * 60)',
        '    start = datetime.now()',
        '',
        '    source = extract()',
        '    dim_lookups = {}',
        '',
    ]
    for dim in dim_names:
        lines += [
            f'    df_{dim.lower()} = transform_{dim.lower()}(source)',
            f'    save(df_{dim.lower()}, "{dim}")',
            f'    dim_lookups["{dim}"] = df_{dim.lower()}',
            '',
        ]
    for fact in fact_names:
        lines += [
            f'    df_{fact.lower()} = transform_{fact.lower()}(source, dim_lookups)',
            f'    save(df_{fact.lower()}, "{fact}")',
            '',
        ]
    lines += [
        '    elapsed = (datetime.now() - start).total_seconds()',
        '    logger.info(f"Pipeline complete in {elapsed:.1f}s")',
        '    logger.info("=" * 60)',
        '',
        '',
        'if __name__ == "__main__":',
        '    main()',
    ]

    return "\n".join(lines)


# ── Lineage CSV ───────────────────────────────────────────────────────────────
def generate_lineage_csv(model: dict) -> str:
    """Return field lineage as a CSV string."""
    rows = [["source_field", "source_description", "target_table",
             "target_column", "transformation", "logic"]]
    for l in model.get("lineage", []):
        rows.append([
            l.get("source_field", ""),
            l.get("source_description", ""),
            l.get("target_table", ""),
            l.get("target_column", ""),
            l.get("transformation", ""),
            l.get("logic", ""),
        ])
    return "\n".join(",".join(f'"{str(v).replace(chr(34), chr(39))}"' for v in row) for row in rows)
