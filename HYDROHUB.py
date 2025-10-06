import streamlit as st
import hashlib
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import uuid

DATA_FILE = Path("hydrohub_data.json")

def now_iso():
    return datetime.utcnow().isoformat() + "Z"


def block_hash(block: dict):
    block_copy = {k: block[k] for k in sorted(block) if k != "hash"}
    encoded = json.dumps(block_copy, sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"ledger": []}
    else:
        return {"ledger": []}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def append_block(data, btype, author, payload):
    block = {
        "id": str(uuid.uuid4()),
        "type": btype,
        "timestamp": now_iso(),
        "author": author,
        "payload": payload,
    }
    block["hash"] = block_hash(block)
    data["ledger"].append(block)
    save_data(data)
    return block


st.set_page_config(page_title="HYDROHUB — Blockchain budget transparency", layout="wide")

st.title("HYDROHUB")

data = load_data()

with st.sidebar:
    st.header("Controls")
    st.write("Use the forms below to add records to the ledger. Each record is hashed to simulate a blockchain-style ledger for auditability.")
    if st.button("Clear all data (danger)"):
        if st.checkbox("I understand this will delete the local data file"):
            if DATA_FILE.exists():
                DATA_FILE.unlink()
            data = {"ledger": []}
            st.success("All local data cleared. Refresh the page to reload.")

    st.markdown("---")
    st.write("Export / Import")
    if st.button("Download ledger JSON"):
        st.download_button("Download JSON", json.dumps(data, indent=2), file_name="hydrohub_ledger.json")
    uploaded = st.file_uploader("Import ledger JSON", type=["json"])
    if uploaded is not None:
        try:
            imported = json.load(uploaded)
            if isinstance(imported, dict) and "ledger" in imported:
                save_data(imported)
                st.success("Imported ledger saved to disk. Refresh page to reload.")
            else:
                st.error("Invalid ledger JSON format — expected an object with a 'ledger' array.")
        except Exception as e:
            st.error(f"Failed to import JSON: {e}")

col1, col2 = st.columns([1, 1])

with col1:
    st.header("Add a new record")

    with st.form("proposal_form"):
        st.subheader("Create Proposal")
        p_title = st.text_input("Proposal title")
        p_description = st.text_area("Description")
        p_amount = st.number_input("Proposed budget (PHP)", min_value=0.0, step=100.0)
        p_author = st.text_input("Submitted by (name)")
        submitted = st.form_submit_button("Submit proposal")
        if submitted:
            payload = {
                "title": p_title,
                "description": p_description,
                "amount": float(p_amount),
            }
            block = append_block(data, "PROPOSAL", p_author or "anonymous", payload)
            st.success("Proposal recorded on the ledger.")
            st.json(block)

    st.markdown("---")

    with st.form("activity_form"):
        st.subheader("Record Activity / Resolution")
        a_ref = st.text_input("Reference (proposal ID or note)")
        a_summary = st.text_area("Summary of activity / resolution")
        a_author = st.text_input("Recorded by")
        a_outcome = st.selectbox("Outcome", ["In Progress", "Resolved", "Rejected", "On Hold"])
        a_submit = st.form_submit_button("Record activity")
        if a_submit:
            payload = {
                "ref": a_ref,
                "summary": a_summary,
                "outcome": a_outcome,
            }
            block = append_block(data, "ACTIVITY", a_author or "anonymous", payload)
            st.success("Activity/resolution recorded on the ledger.")
            st.json(block)

    st.markdown("---")

    with st.form("purchase_form"):
        st.subheader("Record Purchase")
        pur_ref = st.text_input("Reference (purchase order / proposal ID)")
        pur_desc = st.text_area("What was purchased?")
        pur_vendor = st.text_input("Vendor / Supplier")
        pur_amount = st.number_input("Amount (PHP)", min_value=0.0, step=100.0, key="pur_amount")
        pur_receipt = st.text_input("Receipt / Invoice no.")
        pur_by = st.text_input("Recorded by")
        pur_submit = st.form_submit_button("Record purchase")
        if pur_submit:
            payload = {
                "ref": pur_ref,
                "description": pur_desc,
                "vendor": pur_vendor,
                "amount": float(pur_amount),
                "receipt": pur_receipt,
            }
            block = append_block(data, "PURCHASE", pur_by or "anonymous", payload)
            st.success("Purchase recorded on the ledger.")
            st.json(block)

with col2:
    st.header("Ledger & Dashboard")

    ledger = data.get("ledger", [])

    st.subheader("Raw ledger (most recent first)")
    for b in reversed(ledger[-20:]):
        with st.expander(f"[{b['type']}] {b['id']} — {b['timestamp']}"):
            st.write(f"**Author:** {b.get('author')}")
            st.write(f"**Type:** {b.get('type')}")
            st.write(f"**Hash:** `{b.get('hash')}`")
            st.json(b.get('payload'))

    st.markdown("---")

    st.subheader("Ledger table")
    df_rows = []
    for b in ledger:
        df_rows.append({
            "id": b.get("id"),
            "type": b.get("type"),
            "timestamp": b.get("timestamp"),
            "author": b.get("author"),
            "summary": (b.get("payload") if isinstance(b.get("payload"), str) else json.dumps(b.get("payload")) ),
            "hash": b.get("hash"),
        })
    df = pd.DataFrame(df_rows)
    st.dataframe(df.sort_values("timestamp", ascending=False))

    st.markdown("---")
    st.subheader("Budget summary")

    total_proposed = sum((b.get("payload", {}).get("amount") or 0) for b in ledger if b.get("type") == "PROPOSAL")
    total_purchased = sum((b.get("payload", {}).get("amount") or 0) for b in ledger if b.get("type") == "PURCHASE")
    st.metric("Total proposed (PHP)", f"{total_proposed:,.2f}")
    st.metric("Total purchased (PHP)", f"{total_purchased:,.2f}")

    purchases = [b for b in ledger if b.get("type") == "PURCHASE"]
    if purchases:
        vendor_sums = {}
        for p in purchases:
            v = p.get("payload", {}).get("vendor") or "Unknown"
            amt = float(p.get("payload", {}).get("amount") or 0)
            vendor_sums[v] = vendor_sums.get(v, 0) + amt
        vendor_df = pd.DataFrame([{"vendor": k, "amount": v} for k, v in vendor_sums.items()])
        st.write("Spending by vendor")
        st.dataframe(vendor_df.sort_values("amount", ascending=False))

    st.markdown("---")
    st.subheader("Verify ledger integrity")
    if st.button("Run integrity check"):
        problems = []
        for b in data.get("ledger", []):
            h = b.get("hash")
            if not h:
                problems.append((b.get("id"), "missing hash"))
            else:
                recomputed = block_hash(b)
                if recomputed != h:
                    problems.append((b.get("id"), "hash mismatch"))
        if not problems:
            st.success("All blocks verified — hashes match their content.")
        else:
            st.error(f"Found {len(problems)} problem(s):")
            for pid, reason in problems:
                st.write(pid, reason)

st.markdown("---")
st.caption("This is a prototype / educational demo that simulates blockchain-style immutability by hashing each record. For a production-grade blockchain solution you would integrate with an actual distributed ledger or anchored proof service.")

st.info(f"Local ledger file: {DATA_FILE.resolve()}")

