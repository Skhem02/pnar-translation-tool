import json
import time
import uuid

import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]

REQUEST_TIMEOUT = 20
MAX_RETRIES = 4


st.set_page_config(
    page_title="Pnar Translation Tool",
    page_icon="📝",
    layout="centered",
)


# ============================================================
# USER INTERFACE
# ============================================================

st.markdown(
    """
    <style>
    [data-testid="stToolbar"] { visibility: hidden; }
    [data-testid="stStatusWidget"] { display: none; }
    [data-testid="stDeployButton"] { display: none; }
    footer { visibility: hidden; }

    .block-container {
        max-width: 760px;
        padding-top: 1.25rem;
        padding-bottom: 1.5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    div.stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-size: 1rem;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-top: 0.75rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# BACKEND REQUEST
# ============================================================

def backend_request(action, payload=None):
    """Call Apps Script with retry/backoff for temporary quota/network errors."""

    data = {
        "action": action,
        "request_id": str(uuid.uuid4()),
    }

    if payload:
        data.update(payload)

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                APPS_SCRIPT_URL,
                json=data,
                timeout=REQUEST_TIMEOUT,
            )

            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                return result

            # Backend can explicitly tell us to retry.
            if result.get("retry"):
                time.sleep(0.7 * (2 ** attempt))
                continue

            return result

        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt < MAX_RETRIES - 1:
                time.sleep(0.7 * (2 ** attempt))

    return {
        "ok": False,
        "error": "Temporary connection problem.",
        "retry": True,
        "details": str(last_error) if last_error else "",
    }


# ============================================================
# CLAIM A SENTENCE
# ============================================================

def claim_sentence():
    result = backend_request(
        "claim",
        {
            "annotator": "abc",
        },
    )

    if result.get("ok"):
        return (
            result.get("row"),
            result.get("english"),
            result.get("claim_id"),
        )

    return None, None, None


# ============================================================
# SAVE TRANSLATION
# ============================================================

def save_translation(row, claim_id, pnar_text):
    return backend_request(
        "save",
        {
            "row": row,
            "claim_id": claim_id,
            "pnar": pnar_text,
            "annotator": "abc",
        },
    )


# ============================================================
# RELEASE CLAIM
# ============================================================

def release_sentence(row, claim_id):
    return backend_request(
        "release",
        {
            "row": row,
            "claim_id": claim_id,
        },
    )


# ============================================================
# START SCREEN
# ============================================================

def start_screen():

    st.title("📝 Pnar Translation Tool")

    st.markdown(
        """
        <div style="
            border: 1px solid rgba(128,128,128,0.35);
            border-radius: 14px;
            padding: 15px;
            margin: 6px 0 12px 0;
            background: rgba(128,128,128,0.08);
            line-height: 1.48;
        ">
        <div style="font-size: 1.02rem; font-weight: 700; margin-bottom: 7px;">
            Cha phi ki bru Pnar
        </div>
        <div style="font-size: 0.94rem;">
            Wan iada i ia ka ktien yong i ha kam kani ka juk AI!
            Ka thong toh yow pynman ia ka ktien Pnar iow tip ki bru
            ha waroh ka pyrthai, kam ka Khasi.
            Kani ka kreh ym ye u leh samen. Toh ka kamram yong i
            yow iada, pynneh wei pynman ia ka ktien yong i kawa im.
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            border: 1px solid rgba(128,128,128,0.35);
            border-radius: 14px;
            padding: 15px;
            margin: 0 0 16px 0;
            background: rgba(128,128,128,0.08);
            line-height: 1.48;
        ">
        <div style="font-size: 1.02rem; font-weight: 700; margin-bottom: 7px;">
            To the Pnar people
        </div>
        <div style="font-size: 0.94rem;">
            Let’s save our language in the age of AI!
            Our goal is to make Pnar known worldwide, just like Khasi.
            This work cannot be done alone. It is our shared duty
            to protect, preserve, and keep our language alive.
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.button(
        "Next →",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.annotator_name = "abc"
        st.session_state.review_mode = False
        st.session_state.pnar_draft = ""
        st.rerun()


# ============================================================
# LOAD NEXT SENTENCE
# ============================================================

def load_next_sentence():

    row, english, claim_id = claim_sentence()

    st.session_state.current_row = row
    st.session_state.current_english = english
    st.session_state.current_claim_id = claim_id
    st.session_state.pnar_draft = ""
    st.session_state.review_mode = False


# ============================================================
# TRANSLATION SCREEN
# ============================================================

def translation_screen():

    if "current_row" not in st.session_state:
        load_next_sentence()

    row = st.session_state.get("current_row")
    english = st.session_state.get("current_english")
    claim_id = st.session_state.get("current_claim_id")

    # Temporary backend failure: don't destroy the user's current work.
    if row is None and english is None and claim_id is None:
        st.error(
            "⚠️ The translation service is busy right now. "
            "Please wait a moment and try again."
        )

        if st.button("Try again", type="primary", use_container_width=True):
            st.session_state.pop("current_row", None)
            st.session_state.pop("current_english", None)
            st.session_state.pop("current_claim_id", None)
            st.rerun()

        return

    # ========================================================
    # NO SENTENCES REMAIN
    # ========================================================

    if row is None:

        st.success("🎉 All available sentences have been translated.")

        if st.button("Check again", use_container_width=True):
            st.session_state.pop("current_row", None)
            st.session_state.pop("current_english", None)
            st.session_state.pop("current_claim_id", None)
            st.rerun()

        return

    # ========================================================
    # REVIEW MODE
    # ========================================================

    if st.session_state.get("review_mode", False):

        st.markdown("### English")
        st.info(english)

        st.markdown("### Pnar")
        st.success(st.session_state.pnar_draft)

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✏️ Edit", use_container_width=True):
                st.session_state.review_mode = False
                st.rerun()

        with col2:
            if st.button(
                "✓ Save & Next",
                type="primary",
                use_container_width=True,
            ):
                pnar_text = st.session_state.pnar_draft.strip()

                if not pnar_text:
                    st.warning("Please enter a Pnar translation.")
                    return

                result = save_translation(
                    row,
                    claim_id,
                    pnar_text,
                )

                if result.get("ok"):
                    st.session_state.pop("current_row", None)
                    st.session_state.pop("current_english", None)
                    st.session_state.pop("current_claim_id", None)
                    st.session_state.pnar_draft = ""
                    st.session_state.review_mode = False
                    st.rerun()

                if result.get("retry"):
                    st.warning(
                        "The server is busy. Your translation is still on this screen. "
                        "Please press Save & Next again."
                    )
                else:
                    st.error(
                        result.get(
                            "error",
                            "The translation could not be saved. "
                            "Your text is still on this screen.",
                        )
                    )

        return

    # ========================================================
    # TRANSLATION MODE
    # ========================================================

    st.markdown("### English")
    st.info(english)

    st.markdown("### Pnar")

    pnar = st.text_area(
        "Type the Pnar translation",
        value=st.session_state.get("pnar_draft", ""),
        height=150,
        placeholder="Type the correct Pnar translation here...",
        key="pnar_input",
        label_visibility="collapsed",
    )

    if st.button(
        "OK",
        type="primary",
        use_container_width=True,
    ):

        if not pnar.strip():
            st.warning("Please enter a Pnar translation.")
            return

        st.session_state.pnar_draft = pnar.strip()
        st.session_state.review_mode = True
        st.rerun()


# ============================================================
# MAIN
# ============================================================

if "annotator_name" not in st.session_state:
    start_screen()
else:
    translation_screen()