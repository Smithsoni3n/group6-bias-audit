import json
import sys
from pathlib import Path
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
import bias_rules

st.set_page_config(page_title="Algorithmic Hiring Bias Simulator & Audit Tool", layout="wide")

SCALE_RANGES = {"max_gap_months": (0, 24), "zip_penalty": (0, 50), "gap_penalty": (0, 50), "passing_score": (0, 100)}
WELCOME_TEXT = (
    "Welcome! Move the sliders on the left to change the robot's rules, then click Run Audit. "
    "The table above shows who passes, and this panel explains who was unfairly filtered out and why.\n\n"
    "Created by Jasmine W., Crystal R., Leilani G., and Frankie A.P.\n\n" + bias_rules.simulation_note
)

for k, v in [("applicants", []), ("flagged_zips", []), ("results", []), ("summary", {}), ("status_msg", "No applicants yet. Add an applicant in the form on the left.")]:
    if k not in st.session_state:
        st.session_state[k] = v

for rule_key, default_val in bias_rules.default_rules.items():
    if rule_key not in st.session_state:
        st.session_state[rule_key] = default_val

def sync_rules():
    for k in bias_rules.default_rules:
        bias_rules.algorithm_rules[k] = st.session_state[k]
    bias_rules.flagged_zip_codes.clear()
    bias_rules.flagged_zip_codes.extend(st.session_state.flagged_zips)

def build_diagnostics(summary, results):
    # The wording lives in bias_rules.py so the desktop app (main.py) and this
    # web preview always say the same thing.
    return bias_rules.build_diagnostics_text(summary, results)

st.title("Algorithmic Hiring Bias Simulator & Audit Tool")
st.caption("Change the robot's rules, then see who it filters out.")

c1, c2, c3, _ = st.columns((1.1, 1, 1.3, 2.6))
with c1:
    if st.button("Run Audit", type="primary", use_container_width=True):
        if not st.session_state.applicants:
            st.toast("No applicants yet — add at least one applicant first.")
        else:
            sync_rules()
            res, summ = bias_rules.run_audit(st.session_state.applicants)
            st.session_state.results, st.session_state.summary = res, summ
            st.session_state.status_msg = f"Audit finished: {summ.get('passed', 0)} passed, {summ.get('filtered', 0)} filtered out."

with c2:
    if st.button("Reset Rules", use_container_width=True):
        bias_rules.reset_rules()
        for k, v in bias_rules.default_rules.items():
            st.session_state[k] = v
        st.session_state.flagged_zips, st.session_state.applicants, st.session_state.results, st.session_state.summary = [], [], [], {}
        st.session_state.status_msg = "Rules reset and all applicants and results cleared."
        st.rerun()

with c3:
    if st.session_state.results:
        sync_rules()
        rep = {"rules_used": dict(bias_rules.algorithm_rules), "flagged_zip_codes": list(bias_rules.flagged_zip_codes), "summary": st.session_state.summary, "applicants": [
            {"name": r["applicant"]["name"], "zip": r["applicant"]["zip"], "gap_months": r["applicant"]["gap_months"], "skills_score": r["applicant"]["base_score"], "final_score": r["final_score"], "audit_result": bias_rules.outcome_labels[r["outcome"]], "points_lost": r["points_lost"], "outcome": "PASSED" if r["robot_passed"] else "FILTERED OUT", "qualified_but_filtered": r["wrongly_filtered"], "penalties": r["reasons"]}
            for r in st.session_state.results
        ]}
        st.download_button("Export Report (JSON)", data=json.dumps(rep, indent=4), file_name="audit_report.json", mime="application/json", use_container_width=True)
    elif st.button("Export Report (JSON)", use_container_width=True):
        st.toast("Click Run Audit first, then export the report.")

st.divider()
left, right = st.columns((1, 2.1), gap="large")

with left:
    with st.container(border=True):
        st.subheader("1. Algorithm Controls")
        for k, label in bias_rules.rule_labels.items():
            lo, hi = SCALE_RANGES.get(k, (0, 100))
            st.slider(label, min_value=lo, max_value=hi, key=k)

    with st.container(border=True):
        st.subheader("2. Flagged ZIP Codes")
        st.write("Flagged list: " + ", ".join(st.session_state.flagged_zips) if st.session_state.flagged_zips else "No ZIP codes flagged yet.")
        z1, z2 = st.columns((2, 1))
        z_in = z1.text_input("ZIP code", placeholder="5-digit ZIP", label_visibility="collapsed")
        if z2.button("Add ZIP", use_container_width=True):
            cz = z_in.strip()
            if not cz.isdigit() or len(cz) != 5:
                st.error("A ZIP code must be exactly 5 digits.")
            elif cz in st.session_state.flagged_zips:
                st.info(f"{cz} is already on the list.")
            else:
                st.session_state.flagged_zips.append(cz)
                st.session_state.results, st.session_state.summary = [], {}
                st.session_state.status_msg = f"Flagged ZIP code {cz}. Click Run Audit to see the effect."
                st.rerun()
        if st.session_state.flagged_zips:
            sel_z = st.selectbox("Remove ZIP", st.session_state.flagged_zips, label_visibility="collapsed")
            if st.button("Remove selected ZIP", use_container_width=True):
                st.session_state.flagged_zips.remove(sel_z)
                st.session_state.results, st.session_state.summary = [], {}
                st.session_state.status_msg = f"Un-flagged ZIP code {sel_z}. Click Run Audit to see the effect."
                st.rerun()

    with st.container(border=True):
        st.subheader("3. Test Your Own Applicant")
        with st.form("app_form", clear_on_submit=True):
            n_val, z_val, g_val, s_val = st.text_input("Name"), st.text_input("ZIP code"), st.text_input("Gap (months)"), st.text_input("Skills score (0-100)")
            if st.form_submit_button("Add Applicant", use_container_width=True):
                app, err = bias_rules.make_applicant(n_val, z_val, g_val, s_val, "")
                if err:
                    st.error(err)
                else:
                    st.session_state.applicants.append(app)
                    st.session_state.results, st.session_state.summary = [], {}
                    st.session_state.status_msg = f"Added {app['name']}. Click Run Audit to screen everyone."
                    st.rerun()

with right:
    st.subheader("Screening Results")
    if not st.session_state.results:
        rows = [{"Applicant": a["name"], "ZIP": a["zip"], "Gap (mo)": a["gap_months"], "Skills": a["base_score"], "Final": "-", "Result": "Not screened yet", "Audit flag": ""} for a in st.session_state.applicants]
    else:
        rows = [{"Applicant": r["applicant"]["name"], "ZIP": r["applicant"]["zip"], "Gap (mo)": r["applicant"]["gap_months"], "Skills": r["applicant"]["base_score"], "Final": r["final_score"], "Result": "PASSED" if r["robot_passed"] else "FILTERED OUT", "Audit flag": bias_rules.outcome_labels[r["outcome"]]} for r in st.session_state.results]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.subheader("Bias Diagnostics & Explanation")
    with st.container(border=True):
        st.text(WELCOME_TEXT if not st.session_state.results else build_diagnostics(st.session_state.summary, st.session_state.results))

st.caption("Status: " + st.session_state.status_msg)
