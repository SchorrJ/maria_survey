import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

st.set_page_config(page_title="Mental Health Research Survey", page_icon="🧠", layout="centered")

# ── Google Sheets connection ─────────────────────────────────────────
def get_sheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    key_data = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(key_data, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open("Survey Responses").sheet1

def save_to_sheet(gad_answers, phq_answers, gad_score, phq_score, q17, q18, q19, q20):
    try:
        sheet = get_sheet()
        # Add headers if sheet is empty
        if not sheet.get_all_values():
            headers = [
                "Timestamp",
                "GAD1", "GAD2", "GAD3", "GAD4", "GAD5", "GAD6", "GAD7",
                "PHQ1", "PHQ2", "PHQ3", "PHQ4", "PHQ5", "PHQ6", "PHQ7", "PHQ8", "PHQ9",
                "GAD Score", "PHQ Score",
                "PHQ - Seen Doctor?", "GAD - Seen Doctor?",
                "Reason No Doctor", "Time to See Doctor"
            ]
            sheet.append_row(headers)

        row = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            *[gad_answers.get(i, "") for i in range(7)],
            *[phq_answers.get(i, "") for i in range(9)],
            gad_score, phq_score,
            q17 or "", q18 or "", q19 or "", q20 or ""
        ]
        sheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Could not save to Google Sheets: {e}")
        return False

# ── session state init ──────────────────────────────────────────────
for key, val in {
    "page": 0,
    "gad_answers": {},
    "phq_answers": {},
    "q17": None, "q18": None, "q19": "", "q20": None,
    "saved": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

OPTIONS = [
    "Not at all (0)",
    "Several days (+1)",
    "More than half the days (+2)",
    "Nearly every day (+3)",
]
POINTS = {
    "Not at all (0)": 0,
    "Several days (+1)": 1,
    "More than half the days (+2)": 2,
    "Nearly every day (+3)": 3,
}

GAD_QUESTIONS = [
    "Feeling anxious, nervous, or on edge?",
    "Not being able to stop or control worrying?",
    "Worrying too much about different things?",
    "Trouble relaxing?",
    "Being so restless that it is hard to sit still?",
    "Becoming easily annoyed or irritable?",
    "Feeling afraid something awful might happen?",
]

PHQ_QUESTIONS = [
    "Little interest or pleasure in doing things?",
    "Feeling down, depressed, or hopeless?",
    "Trouble falling asleep or sleeping too much?",
    "Feeling tired or having little energy?",
    "Poor appetite or overeating?",
    "Feeling bad about yourself, or that you are a failure or have let your family down?",
    "Trouble concentrating on things, such as reading or watching TV?",
    "Moving or speaking so slowly that other people could have noticed? Or the opposite — being so fidgety or restless that you have been moving around a lot more than usual?",
    "Thoughts that you would be better off dead, or hurting yourself in some way?",
]

DOCTOR_OPTIONS = ["Yes — still am", "Yes — in the past", "No — never"]
TIME_OPTIONS = ["Immediately", "Couple of months", "1 year", "3 years", "5 years", "Longer than 5 years"]

# ── helper ──────────────────────────────────────────────────────────
def score(answers):
    return sum(POINTS[v] for v in answers.values())

def all_answered(answers, n):
    return len(answers) == n and all(v is not None for v in answers.values())

def radio(label, key, store, section=""):
    prev = store.get(key)
    idx = OPTIONS.index(prev) if prev in OPTIONS else None
    choice = st.radio(label, OPTIONS, index=idx, key=f"radio_{section}_{key}")
    store[key] = choice

# ── PAGE 0 : intro ──────────────────────────────────────────────────
if st.session_state.page == 0:
    st.title("Mental Health Research Survey")
    st.markdown(
        """
        The **GAD-7** is a screening tool used for anxiety and the **PHQ-9** is a screening tool
        used for depression that will be used in this survey.

        This survey is to better understand the delay in starting treatment of mental disorders
        such as anxiety and depression. Due to maintaining patient autonomy and the social stigma
        of mental health disorders **this survey is anonymous.**
        """
    )
    if st.button("Begin Survey →", use_container_width=True):
        st.session_state.page = 1
        st.rerun()

# ── PAGE 1 : GAD-7 ──────────────────────────────────────────────────
elif st.session_state.page == 1:
    st.title("GAD-7")
    st.caption("Over the last 2 weeks, how often have you been experiencing these problems?")
    st.divider()

    for i, q in enumerate(GAD_QUESTIONS):
        radio(f"**{i+1}. {q}**", i, st.session_state.gad_answers, section="gad")
        st.write("")

    ready = all_answered(st.session_state.gad_answers, len(GAD_QUESTIONS))
    if st.button("Next →", disabled=not ready, use_container_width=True):
        st.session_state.page = 2
        st.rerun()
    if not ready:
        st.caption("⚠️ Please answer all questions to continue.")

# ── PAGE 2 : PHQ-9 ──────────────────────────────────────────────────
elif st.session_state.page == 2:
    st.title("PHQ-9")
    st.caption("Over the last 2 weeks, how often have you been bothered by the following problems?")
    st.divider()

    for i, q in enumerate(PHQ_QUESTIONS):
        radio(f"**{i+1}. {q}**", i, st.session_state.phq_answers, section="phq")
        st.write("")

    ready = all_answered(st.session_state.phq_answers, len(PHQ_QUESTIONS))
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.page = 1
            st.rerun()
    with col2:
        if st.button("Next →", disabled=not ready, use_container_width=True):
            st.session_state.page = 3
            st.rerun()
    if not ready:
        st.caption("⚠️ Please answer all questions to continue.")

# ── PAGE 3 : follow-up (conditional) ───────────────────────────────
elif st.session_state.page == 3:
    gad = score(st.session_state.gad_answers)
    phq = score(st.session_state.phq_answers)

    show_phq_followup = phq >= 5
    show_gad_followup = gad >= 5

    if not show_phq_followup and not show_gad_followup:
        st.session_state.page = 4
        st.rerun()

    st.title("Follow-up Questions")
    st.divider()

    if show_phq_followup:
        st.session_state.q17 = st.radio(
            "**PHQ-9 — Have you talked to a medical professional or doctor about your symptoms?**",
            DOCTOR_OPTIONS,
            index=DOCTOR_OPTIONS.index(st.session_state.q17) if st.session_state.q17 in DOCTOR_OPTIONS else None,
            key="r_q17",
        )
        st.write("")

    if show_gad_followup:
        st.session_state.q18 = st.radio(
            "**GAD-7 — Have you talked to a medical professional or doctor about your symptoms?**",
            DOCTOR_OPTIONS,
            index=DOCTOR_OPTIONS.index(st.session_state.q18) if st.session_state.q18 in DOCTOR_OPTIONS else None,
            key="r_q18",
        )
        st.write("")

    answered_no = (
        (show_phq_followup and st.session_state.q17 == "No — never") or
        (show_gad_followup and st.session_state.q18 == "No — never")
    )
    answered_yes = (
        (show_phq_followup and st.session_state.q17 in ["Yes — still am", "Yes — in the past"]) or
        (show_gad_followup and st.session_state.q18 in ["Yes — still am", "Yes — in the past"])
    )

    if answered_no:
        st.session_state.q19 = st.text_area(
            "**Is there a reason why you haven't talked to a medical professional about your symptoms?** "
            "(This is anonymous — feel free to write what you want)",
            value=st.session_state.q19,
        )
        st.write("")

    if answered_yes:
        st.session_state.q20 = st.radio(
            "**How long was it from when you first started experiencing symptoms to when you made initial contact with a medical professional?**",
            TIME_OPTIONS,
            index=TIME_OPTIONS.index(st.session_state.q20) if st.session_state.q20 in TIME_OPTIONS else None,
            key="r_q20",
        )
        st.write("")

    phq_ok = (not show_phq_followup) or (st.session_state.q17 is not None)
    gad_ok = (not show_gad_followup) or (st.session_state.q18 is not None)
    ready = phq_ok and gad_ok

    col1, col2 = st.columns(2)
    with col1:
        if st.button("← Back", use_container_width=True):
            st.session_state.page = 2
            st.rerun()
    with col2:
        if st.button("See Results →", disabled=not ready, use_container_width=True):
            st.session_state.page = 4
            st.rerun()
    if not ready:
        st.caption("⚠️ Please answer all questions to continue.")

# ── PAGE 4 : results ────────────────────────────────────────────────
elif st.session_state.page == 4:
    gad = score(st.session_state.gad_answers)
    phq = score(st.session_state.phq_answers)

    # Save to sheet once
    if not st.session_state.saved:
        save_to_sheet(
            st.session_state.gad_answers,
            st.session_state.phq_answers,
            gad, phq,
            st.session_state.q17,
            st.session_state.q18,
            st.session_state.q19,
            st.session_state.q20,
        )
        st.session_state.saved = True

    st.title("Thank you for participating! 🎉")
    st.divider()
    st.subheader("Your Results")

    if gad <= 4:
        gad_label, gad_color = "Minimal Anxiety", "green"
    elif gad <= 9:
        gad_label, gad_color = "Mild Anxiety", "orange"
    elif gad <= 14:
        gad_label, gad_color = "Moderate Anxiety", "orange"
    else:
        gad_label, gad_color = "Severe Anxiety", "red"

    if phq <= 4:
        phq_label, phq_color = "Minimal Depression", "green"
    elif phq <= 9:
        phq_label, phq_color = "Mild Depression", "orange"
    elif phq <= 14:
        phq_label, phq_color = "Moderate Depression", "orange"
    elif phq <= 19:
        phq_label, phq_color = "Moderately Severe Depression", "red"
    else:
        phq_label, phq_color = "Severe Depression", "red"

    col1, col2 = st.columns(2)
    with col1:
        st.metric("GAD-7 Score (Anxiety)", f"{gad} / 21")
        st.markdown(f":{gad_color}[**{gad_label}**]")
    with col2:
        st.metric("PHQ-9 Score (Depression)", f"{phq} / 27")
        st.markdown(f":{phq_color}[**{phq_label}**]")

    st.divider()
    st.info(
        "⚠️ This survey is a self-assessment tool for research purposes only. "
        "It is not a clinical diagnosis. If you are concerned about your mental health, "
        "please speak with a qualified medical professional."
    )

    if st.button("↩ Start Over", use_container_width=True):
        for key in ["page","gad_answers","phq_answers","q17","q18","q19","q20","saved"]:
            del st.session_state[key]
        st.rerun()
