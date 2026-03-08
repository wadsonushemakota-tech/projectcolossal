from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import plotly.express as px
import streamlit as st

from components import api
from components.ui import badge, footer_html, header, info_card, kpi, load_css, section_header, set_page


def _safe_health() -> bool:
    try:
        api.get("/health")
        return True
    except Exception:
        return False


def _get_businesses() -> List[Dict[str, Any]]:
    return api.get("/businesses", params={"limit": 200}) or []


def _get_business(business_id: int) -> Dict[str, Any]:
    return api.get(f"/businesses/{business_id}")


def _get_wallet(business_id: int) -> Dict[str, Any]:
    return api.get(f"/businesses/{business_id}/wallet")


def _get_transactions(business_id: int) -> List[Dict[str, Any]]:
    return api.get(f"/businesses/{business_id}/transactions", params={"limit": 500}) or []


def _compute_profile(business_id: int) -> Dict[str, Any]:
    return api.post(f"/businesses/{business_id}/credit-profile/compute", json={})


def _get_profile(business_id: int) -> Dict[str, Any]:
    return api.get(f"/businesses/{business_id}/credit-profile")


def _get_loan_offer(business_id: int) -> Dict[str, Any]:
    return api.get(f"/businesses/{business_id}/loan-offer")


def _list_loans(business_id: int) -> List[Dict[str, Any]]:
    return api.get(f"/businesses/{business_id}/loans", params={"limit": 100}) or []


def _get_trainings() -> List[Dict[str, Any]]:
    return api.get("/trainings") or []


def _enroll_training(training_id: int, business_id: int) -> Dict[str, Any]:
    return api.post(f"/trainings/{training_id}/enroll", params={"business_id": business_id})


def _get_enrollments(business_id: int) -> List[Dict[str, Any]]:
    return api.get(f"/trainings/enrollments/{business_id}") or []


def _update_training_progress(enrollment_id: int, progress: float, status: Optional[str] = None, current_stage: Optional[int] = None) -> Dict[str, Any]:
    params = {"progress": progress}
    if status:
        params["status"] = status
    if current_stage is not None:
        params["current_stage"] = current_stage
    return api.post(f"/trainings/enrollments/{enrollment_id}/progress", params=params)


def _risk_badge(risk_band: str) -> str:
    if risk_band == "low":
        return badge("LOW RISK", "good")
    if risk_band == "medium":
        return badge("MEDIUM RISK", "warn")
    return badge("HIGH RISK", "bad")


def page_overview(business_id: int) -> None:
    b = _get_business(business_id)
    wallet = _get_wallet(business_id)

    st.markdown(section_header("Overview", "📊", "Business snapshot and key metrics"), unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi("Business", b["name"], f"Owner: {b['owner_name']}")
    with c2:
        kpi("Phone", b["phone"], b.get("location") or "Location not set")
    with c3:
        tin = b.get("zimra_tin") or "Not set"
        kpi("ZIMRA TIN", tin, f"Tax #: {b.get('zimra_tax_number') or '—'}")
    with c4:
        kpi("Tokens", str(wallet["tokens_balance"]), f"Earned total: {wallet['earned_total']}")

    st.divider()
    c_score, c_actions = st.columns([1, 2])
    with c_score:
        try:
            prof = _get_profile(business_id)
            st.markdown(
                f"<div class='pc-score-box'>Credit Score: {prof['score']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_risk_badge(prof["risk_band"]), unsafe_allow_html=True)
        except Exception:
            st.info("Compute profile to see score.")

    with c_actions:
        st.markdown(
            info_card(
                "Next best actions",
                [
                    "Add at least 20–30 transactions to improve confidence",
                    "Compute the credit profile",
                    "Use tokens to unlock higher loan eligibility",
                ],
                accent="blue",
            ),
            unsafe_allow_html=True,
        )

    with st.expander("Raw business data", expanded=False):
        st.json(b)


def page_onboard() -> None:
    st.markdown(
        section_header("Onboard a business", "➕", "Capture informal and women-led businesses with lightweight onboarding."),
        unsafe_allow_html=True,
    )

    # Force blue labels for the onboarding form
    st.markdown(
        """
        <style>
        [data-testid="stForm"] label p, 
        [data-testid="stWidgetLabel"] p {
            color: #3b82f6 !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
            text-shadow: 0 0 5px rgba(59, 130, 246, 0.2);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.form("onboard", clear_on_submit=True):
        name = st.text_input("Business name*", placeholder="e.g., Mbare Fresh Produce")
        owner = st.text_input("Owner name*", placeholder="e.g., Tariro M.")
        phone = st.text_input("Phone*", placeholder="e.g., +2637...")
        gender = st.selectbox("Owner gender (optional)", ["", "female", "male", "other"])
        email = st.text_input("Email (optional)")
        location = st.text_input("Location (optional)", placeholder="e.g., Harare")
        category = st.selectbox("Category (optional)", ["", "Retail", "Services", "Transport", "Food", "Agriculture", "Other"])
        is_registered = st.checkbox("Formally registered?", value=False)
        zimra_tin = st.text_input("ZIMRA TIN (optional)", placeholder="e.g., 12345678")
        zimra_tax_number = st.text_input("ZIMRA Tax Number (optional)", placeholder="e.g., TAX-001")
        submitted = st.form_submit_button("Create business")

    if submitted:
        if not name.strip() or not owner.strip() or not phone.strip():
            st.error("Please fill in the required fields: Business name, Owner name, Phone.")
            return
        payload = {
            "name": name.strip(),
            "owner_name": owner.strip(),
            "phone": phone.strip(),
            "gender": gender or None,
            "email": email.strip() or None,
            "location": location.strip() or None,
            "category": category if category else None,
            "is_registered": bool(is_registered),
            "zimra_tin": zimra_tin.strip() or None,
            "zimra_tax_number": zimra_tax_number.strip() or None,
        }
        try:
            created = api.post("/businesses", json=payload)
            st.success(f"Created business #{created['id']}: {created['name']}")
            st.info("Use the sidebar to select the business and start adding transactions.")
        except Exception as e:
            st.error(str(e))


def page_transactions(business_id: int) -> None:
    st.markdown(
        section_header("Transactions", "💸", "Add transactions to build a digital trace. Tokens are automatically minted per transaction."),
        unsafe_allow_html=True,
    )

    # Force blue labels for transactions
    st.markdown(
        """
        <style>
        [data-testid="stForm"] label p, 
        [data-testid="stWidgetLabel"] p {
            color: #3b82f6 !important;
            font-weight: 800 !important;
            font-size: 1.1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    t1, t2 = st.tabs(["Manual entry", "CSV upload"])

    with t1:
        with st.form("add_tx"):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                ttype = st.selectbox(
                    "Type",
                    ["merchant_payment", "p2p_in", "p2p_out", "airtime", "data", "cash_in", "cash_out", "purchase_supply", "tax_payment", "other"],
                )
            with c2:
                amount = st.number_input("Amount", min_value=0.0, step=1.0, value=50.0)
            with c3:
                currency = st.selectbox("Currency", ["ZWL", "USD"])
            channel = st.text_input("Channel (optional)", placeholder="EcoCash / Steward / POS")
            reference = st.text_input("Reference (optional)", placeholder="INV-001 / POS-123")
            counterparty = st.text_input("Counterparty (optional)", placeholder="Customer / Supplier")
            ts = st.text_input("Timestamp (optional ISO8601)", value="")
            submit = st.form_submit_button("Add transaction")

        if submit:
            try:
                payload = {
                    "business_id": business_id,
                    "ts": datetime.utcnow().isoformat() if not ts.strip() else ts.strip(),
                    "type": ttype,
                    "amount": float(amount),
                    "currency": currency,
                    "channel": channel.strip() or None,
                    "reference": reference.strip() or None,
                    "counterparty": counterparty.strip() or None,
                }
                created = api.post(f"/businesses/{business_id}/transactions", json=payload)
                st.success(f"Added transaction #{created['id']}")
            except Exception as e:
                st.error(str(e))

    with t2:
        st.write("Download the template CSV, then upload filled transactions.")
        sample = (Path(__file__).resolve().parent / "assets" / "sample_transactions.csv").read_bytes()
        st.download_button("Download sample CSV", data=sample, file_name="sample_transactions.csv", mime="text/csv")

        file = st.file_uploader("Upload CSV", type=["csv"])
        if file is not None:
            try:
                res = api.post(
                    f"/businesses/{business_id}/transactions/upload_csv",
                    files={"file": (file.name, file.getvalue(), "text/csv")},
                )
                st.success(f"Created: {res['created']} | Skipped: {res['skipped']}")
                if res.get("errors"):
                    st.warning("Some rows failed to ingest.")
                    st.code("\n".join(res["errors"][:20]))
            except Exception as e:
                st.error(str(e))

    st.markdown("#### Recent transactions")
    try:
        txs = _get_transactions(business_id)
        if not txs:
            st.info("No transactions yet.")
            return
        df = pd.DataFrame(txs)
        df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
        st.dataframe(
            df[["ts", "type", "amount", "currency", "channel", "reference", "counterparty"]].sort_values("ts", ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as e:
        st.error(str(e))


def page_credit_profile(business_id: int) -> None:
    st.markdown(
        section_header("Credit profile", "📈", "Score, risk band, and explainable features"),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([1, 2])

    with c1:
        if st.button("Compute / refresh profile", use_container_width=True):
            try:
                prof = _compute_profile(business_id)
                st.success("Profile computed.")
                st.session_state["__profile"] = prof
            except Exception as e:
                st.error(str(e))

        try:
            prof = st.session_state.get("__profile") or _get_profile(business_id)
        except Exception:
            prof = None

        if prof:
            st.markdown(
                f"<div class='pc-score-box'>Score: {prof['score']}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(_risk_badge(prof["risk_band"]), unsafe_allow_html=True)
            st.caption(f"Confidence: {int(100*prof['confidence'])}%")
        else:
            st.info("Compute a profile to see score, risk band, and eligibility.")
            return

    with c2:
        st.markdown("#### Why this score?")
        features = prof.get("features", {}) if prof else {}
        with st.container():
            st.json(features)


def page_wallet(business_id: int) -> None:
    st.markdown(
        section_header("Tokens & wallet", "🪙", "Balance, earned total, and loan eligibility"),
        unsafe_allow_html=True,
    )
    wallet = _get_wallet(business_id)
    c1, c2, c3 = st.columns(3)
    with c1:
        kpi("Tokens balance", str(wallet["tokens_balance"]), "Earn by using digital payments")
    with c2:
        kpi("Earned total", str(wallet["earned_total"]), "Auditable minting ledger")
    with c3:
        try:
            offer = _get_loan_offer(business_id)
            kpi("Est. max loan", f"{offer['max_amount']:.2f}", f"Term: {offer['recommended_term_months']} months")
        except Exception:
            kpi("Est. max loan", "—", "Compute profile + add transactions")

    st.markdown(
        info_card(
            "How tokens are earned",
            [
                "1 token per ~10 units transacted (capped per transaction)",
                "Bonus for merchant payments and P2P usage",
                "Designed to be explainable, bounded, and auditable",
            ],
            accent="green",
        ),
        unsafe_allow_html=True,
    )


def page_loans(business_id: int) -> None:
    st.markdown(
        section_header("Micro-loans", "💰", "Eligibility, apply, and loan history"),
        unsafe_allow_html=True,
    )
    try:
        offer = _get_loan_offer(business_id)
        st.info(
            f"Eligibility estimate: up to **{offer['max_amount']:.2f}** for **{offer['recommended_term_months']} months**."
        )
        st.caption(f"Basis: {json.dumps(offer['basis'], ensure_ascii=False)}")
    except Exception as e:
        st.warning(f"Loan offer not available yet: {e}")

    st.markdown("#### Apply for a loan")
    with st.form("loan_apply"):
        amount = st.number_input("Amount", min_value=50.0, step=50.0, value=200.0)
        currency = st.selectbox("Currency", ["ZWL", "USD"])
        term = st.selectbox("Term (months)", [3, 4, 6, 9, 12], index=0)
        purpose = st.text_area("Purpose", placeholder="Stock purchase, equipment, expansion, etc.")
        submit = st.form_submit_button("Submit application")

    if submit:
        if not purpose.strip():
            st.error("Purpose is required.")
        else:
            payload = {
                "business_id": business_id,
                "amount": float(amount),
                "currency": currency,
                "term_months": int(term),
                "purpose": purpose.strip(),
            }
            try:
                res = api.post(f"/businesses/{business_id}/loans", json=payload)
                if res["status"] in {"rejected"}:
                    st.error(f"Rejected: {res.get('decision_reason')}")
                else:
                    st.success(f"Application submitted (#{res['id']}). {res.get('decision_reason')}")
            except Exception as e:
                st.error(str(e))

    st.markdown("#### Loan history")
    try:
        loans = _list_loans(business_id)
        if not loans:
            st.info("No loan applications yet.")
            return
        df = pd.DataFrame(loans)
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        st.dataframe(
            df[["created_at", "amount", "currency", "term_months", "status", "decision_reason"]].sort_values(
                "created_at", ascending=False
            ),
            use_container_width=True,
            hide_index=True,
        )
    except Exception as e:
        st.error(str(e))


def page_analytics(business_id: int) -> None:
    st.markdown(
        section_header("Analytics", "📉", "Transaction volume and trends"),
        unsafe_allow_html=True,
    )
    txs = _get_transactions(business_id)
    if not txs:
        st.info("Add transactions to unlock analytics.")
        return
    df = pd.DataFrame(txs)
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")
    df = df.dropna(subset=["ts"])
    df["date"] = df["ts"].dt.date

    c1, c2 = st.columns(2)
    with c1:
        vol = df.groupby("date")["amount"].sum().reset_index()
        fig = px.area(vol, x="date", y="amount", title="Net amount over time")
        fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        by_type = df.groupby("type")["amount"].sum().reset_index().sort_values("amount", ascending=False)
        fig2 = px.bar(by_type, x="type", y="amount", title="Volume by transaction type")
        fig2.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)


def page_trainings(business_id: int) -> None:
    st.markdown(
        section_header("Trainings", "🎓", "Boost your skills with our curated courses for SMEs"),
        unsafe_allow_html=True,
    )

    # State management for active training
    if "active_training" not in st.session_state:
        st.session_state.active_training = None

    trainings = _get_trainings()
    enrollments = _get_enrollments(business_id)

    # If a training is active, show the training content stage by stage
    if st.session_state.active_training:
        enrollment = next((e for e in enrollments if e["id"] == st.session_state.active_training), None)
        if enrollment:
            training = next((t for t in trainings if t["id"] == enrollment["training_id"]), None)
            if training:
                stages = json.loads(training.get("stages_json", "[]"))
                curr_idx = enrollment.get("current_stage", 0)
                
                if st.button("← Back to Catalog"):
                    st.session_state.active_training = None
                    st.rerun()

                st.markdown(f"## {training['title']}")
                st.progress(enrollment["progress"] / 100.0)
                
                if stages and curr_idx < len(stages):
                    curr_stage = stages[curr_idx]
                    st.markdown(f"### Stage {curr_idx + 1}: {curr_stage['title']}")
                    
                    # Video Player
                    if curr_stage.get("video_url"):
                        st.video(curr_stage["video_url"])
                    
                    st.markdown(curr_stage.get("content", ""))
                    
                    st.divider()
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if curr_idx > 0:
                            if st.button("Previous Stage"):
                                _update_training_progress(enrollment["id"], enrollment["progress"], current_stage=curr_idx - 1)
                                st.rerun()
                    with col2:
                        btn_label = "Complete Course" if curr_idx == len(stages) - 1 else "Next Stage"
                        if st.button(btn_label, type="primary"):
                            new_idx = curr_idx + 1
                            new_progress = (new_idx / len(stages)) * 100.0
                            new_status = "completed" if new_idx >= len(stages) else "in_progress"
                            _update_training_progress(enrollment["id"], new_progress, new_status, new_idx)
                            st.rerun()
                else:
                    st.balloons()
                    st.success("Congratulations! You have completed all stages of this course.")
                    if st.button("Return to Catalog"):
                        st.session_state.active_training = None
                        st.rerun()
                return

    if not trainings:
        st.info("No training modules available at the moment.")
        # Seed comprehensive trainings with diverse video stages
        if st.button("Seed sample trainings"):
            # 1. Excel for SMEs
            api.post("/trainings", json={
                "title": "Excel for SMEs", 
                "description": "Master spreadsheets for business accounting and inventory.", 
                "requirements": "A computer with Microsoft Excel or Google Sheets.",
                "content": "Learn how to use spreadsheets to track inventory and manage finances effectively.",
                "stages_json": json.dumps([
                    {
                        "title": "Excel Basics & Interface", 
                        "video_url": "https://www.youtube.com/watch?v=rwbho0CgEAE", 
                        "content": "Welcome! In this first stage, we'll explore the Excel ribbon, cells, and how to navigate a workbook."
                    },
                    {
                        "title": "Essential Formulas (SUM, IF, VLOOKUP)", 
                        "video_url": "https://www.youtube.com/watch?v=Jl0T3mSIsSU", 
                        "content": "Learn the power of automation. We'll cover SUM for totals, IF for logic, and VLOOKUP for finding data."
                    },
                    {
                        "title": "Building an Inventory Tracker", 
                        "video_url": "https://www.youtube.com/watch?v=8L1U0X2f_GY", 
                        "content": "Apply your skills! We will build a dynamic inventory system that alerts you when stock is low."
                    }
                ]),
                "cost": 50.0, 
                "currency": "USD", 
                "module_outline": "- Interface Basics\n- Essential Formulas\n- Inventory System"
            })
            
            # 2. Digital Marketing & Social Media
            api.post("/trainings", json={
                "title": "Digital Marketing for Growth", 
                "description": "Reach more customers using WhatsApp, Facebook, and Instagram.", 
                "requirements": "A smartphone and basic internet access.",
                "content": "Learn the modern way to market your small business in 2025.",
                "stages_json": json.dumps([
                    {
                        "title": "WhatsApp Business Setup", 
                        "video_url": "https://www.youtube.com/watch?v=yP6_lF6e-Xo", 
                        "content": "Turn your WhatsApp into a sales tool. Learn to set up catalogs, auto-replies, and labels."
                    },
                    {
                        "title": "Facebook Ads for Beginners", 
                        "video_url": "https://www.youtube.com/watch?v=tabcut_fb_ads", # Placeholder for specific beginner guide
                        "content": "Learn how to spend $5/day to reach thousands of local customers in your neighborhood."
                    },
                    {
                        "title": "Content Creation with Canva", 
                        "video_url": "https://www.youtube.com/watch?v=unq8K0R-v0A", 
                        "content": "Create professional posters and videos for your products without being a designer."
                    }
                ]),
                "cost": 45.0, 
                "currency": "USD", 
                "module_outline": "- WhatsApp Sales\n- Local Facebook Ads\n- Content Design"
            })

            # 3. Financial Management & Tax
            api.post("/trainings", json={
                "title": "Financial Management & ZIMRA", 
                "description": "Understand your cash flow and stay compliant with tax laws.", 
                "requirements": "Basic understanding of your business sales.",
                "content": "Learn to manage your money and prepare for ZIMRA declarations.",
                "stages_json": json.dumps([
                    {
                        "title": "Cash Flow Basics", 
                        "video_url": "https://www.youtube.com/watch?v=XWpGv_G-vU0", 
                        "content": "Understand the difference between profit and cash. Track every dollar that enters or leaves."
                    },
                    {
                        "title": "ZIMRA & Tax Compliance", 
                        "video_url": "https://www.youtube.com/watch?v=zimra_guide_2025", 
                        "content": "A simple guide to TIN registration and VAT returns for small businesses."
                    }
                ]),
                "cost": 30.0, 
                "currency": "USD", 
                "module_outline": "- Cash Flow Mastery\n- Tax Basics"
            })
            st.rerun()
        return

    st.markdown("### Available Trainings")
    for t in trainings:
        # Check if already enrolled
        enrollment = next((e for e in enrollments if e["training_id"] == t["id"]), None)
        
        with st.expander(f"{t['title']} — {t['cost']} {t['currency']}"):
            st.write(t["description"])
            
            st.markdown("**Requirements:**")
            st.info(t.get("requirements") or "No specific requirements.")
            
            st.markdown("**Module Outline:**")
            st.write(t["module_outline"])
            
            if enrollment:
                st.success(f"Enrolled (Progress: {enrollment['progress']}%)")
                if st.button(f"Continue Training: {t['title']}", key=f"start_{t['id']}"):
                    st.session_state.active_training = enrollment["id"]
                    st.rerun()
            else:
                if st.button(f"Enroll in {t['title']}", key=f"enroll_{t['id']}"):
                    try:
                        _enroll_training(t["id"], business_id)
                        st.success(f"Successfully enrolled in {t['title']}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Enrollment failed: {e}")

    st.divider()
    st.markdown("### Your Enrollments")
    if not enrollments:
        st.caption("You haven't enrolled in any trainings yet.")
    else:
        for e in enrollments:
            t_name = next((t["title"] for t in trainings if t["id"] == e["training_id"]), "Unknown Training")
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.write(f"- **{t_name}** (Status: {e['status']})")
                st.progress(e["progress"] / 100.0)
            with col_b:
                if st.button("Go to Course", key=f"go_{e['id']}"):
                    st.session_state.active_training = e["id"]
                    st.rerun()


def page_tax_compliance(business_id: int) -> None:
    st.markdown(
        section_header("Tax & Compliance", "🏛️", "Manage ZIMRA registration and tax declarations"),
        unsafe_allow_html=True,
    )
    b = _get_business(business_id)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### ZIMRA Details")
        if not b.get("zimra_tin"):
            st.warning("This business is not yet registered with ZIMRA.")
            if st.button("Apply for ZIMRA TIN"):
                # Simulate application
                import random
                new_tin = str(random.randint(10000000, 99999999))
                new_tax = f"TAX-{random.randint(100, 999)}"
                try:
                    payload = {**b, "zimra_tin": new_tin, "zimra_tax_number": new_tax}
                    # We don't have a PUT method, let's just use POST to 'update' if backend supports it, 
                    # but backend create_business uses model_validate on payload. 
                    # For now, let's just show what it would look like.
                    st.info(f"Application sent! Suggested TIN: {new_tin}")
                except Exception as e:
                    st.error(str(e))
        else:
            st.success(f"Registered TIN: **{b['zimra_tin']}**")
            st.info(f"Tax Number: **{b['zimra_tax_number']}**")

    with c2:
        st.markdown("### Tax Declarations")
        txs = _get_transactions(business_id)
        tax_txs = [t for t in txs if t["type"] == "tax_payment"]
        if not tax_txs:
            st.info("No tax payments recorded yet.")
        else:
            df = pd.DataFrame(tax_txs)
            st.dataframe(df[["ts", "amount", "currency", "reference"]], hide_index=True)

    st.divider()
    st.markdown("### Purchasing & Supply (VAT Declaration)")
    st.write("Declare receipts from ordering goods and services for resale to claim input tax.")
    
    purchases = [t for t in txs if t["type"] == "purchase_supply"]
    if not purchases:
        st.info("No purchase transactions found.")
    else:
        df_p = pd.DataFrame(purchases)
        st.dataframe(df_p[["ts", "amount", "currency", "counterparty", "reference"]], hide_index=True)
        total_purchase = df_p["amount"].sum()
        st.metric("Total Purchases", f"{total_purchase:,.2f} {b.get('currency', 'ZWL')}")


def main() -> None:
    set_page()
    load_css()

    header()

    if not _safe_health():
        st.error("Backend API is not reachable. Start it with: `python -m uvicorn backend.main:app --reload`")
        st.stop()

    with st.sidebar:
        st.markdown(
            "<div class='pc-nav-title'>🧭 Navigation</div>",
            unsafe_allow_html=True,
        )
        page = st.radio(
            "Go to",
            ["Overview", "Onboard business", "Transactions", "Tax & Compliance", "Credit profile", "Tokens & wallet", "Loans", "Trainings", "Analytics"],
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown(
            "<div class='pc-nav-title'>🏢 Selected business</div>",
            unsafe_allow_html=True,
        )

        businesses = _get_businesses()
        if not businesses:
            st.info("No businesses yet. Onboard one first.")
            st.session_state.pop("__business_id", None)
        else:
            options = {f"#{b['id']} • {b['name']}": int(b["id"]) for b in businesses}
            default_label = next(iter(options.keys()))
            selected_label = st.selectbox("Business", list(options.keys()), index=0)
            st.session_state["__business_id"] = options.get(selected_label, options[default_label])

        st.markdown(
            "<div class='pc-sidebar-tip'><strong>Tip:</strong> Onboard, upload CSV, compute profile, then apply for a loan.</div>",
            unsafe_allow_html=True,
        )

    if page == "Onboard business":
        page_onboard()
        st.markdown(footer_html(), unsafe_allow_html=True)
        return

    business_id = st.session_state.get("__business_id")
    if not business_id:
        st.warning("Please onboard a business to continue.")
        st.markdown(footer_html(), unsafe_allow_html=True)
        return

    if page == "Overview":
        page_overview(int(business_id))
    elif page == "Transactions":
        page_transactions(int(business_id))
    elif page == "Tax & Compliance":
        page_tax_compliance(int(business_id))
    elif page == "Credit profile":
        page_credit_profile(int(business_id))
    elif page == "Tokens & wallet":
        page_wallet(int(business_id))
    elif page == "Loans":
        page_loans(int(business_id))
    elif page == "Trainings":
        page_trainings(int(business_id))
    elif page == "Analytics":
        page_analytics(int(business_id))

    st.markdown(footer_html(), unsafe_allow_html=True)


if __name__ == "__main__":
    main()

