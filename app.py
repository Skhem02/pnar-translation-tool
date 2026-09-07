import time
import uuid

import requests
import streamlit as st


# ============================================================
# CONFIGURATION
# ============================================================

APPS_SCRIPT_URL = st.secrets["APPS_SCRIPT_URL"]

REQUEST_TIMEOUT = 12
MAX_RETRIES = 3


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
        padding-top: 1rem;
        padding-bottom: 1.25rem;
        padding-left: 0.9rem;
        padding-right: 0.9rem;
    }

    div.stButton > button {
        min-height: 46px;
        border-radius: 10px;
        font-size: 1rem;
    }

    textarea {
        font-size: 1rem !important;
    }

    @media (max-width: 600px) {
        .block-container {
            padding-top: 0.55rem;
            padding-left: 0.65rem;
            padding-right: 0.65rem;
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
    """Small, fast backend call with short exponential retry."""

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

            if result.get("retry"):
                last_error = result.get("error", "Temporary backend busy.")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(0.25 * (2 ** attempt))
                    continue

            return result

        except (requests.RequestException, ValueError) as exc:
            last_error = str(exc)

            if attempt < MAX_RETRIES - 1:
                time.sleep(0.25 * (2 ** attempt))

    return {
        "ok": False,
        "retry": True,
        "error": "Temporary connection problem.",
        "details": last_error or "",
    }


# ============================================================
# CLAIM A SENTENCE
# ============================================================

def claim_sentence():
    result = backend_request(
        "claim",
        {"annotator": "abc"},
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
# START SCREEN
# ============================================================

def start_screen():

    st.title("📝 Pnar Translation Tool")

    st.markdown(
        """
        <div style="
            border: 1px solid rgba(128,128,128,0.30);
            border-radius: 14px;
            padding: 14px;
            margin: 4px 0 10px 0;
            background: rgba(128,128,128,0.08);
            line-height: 1.45;
        ">
        <div style="font-size: 1rem; font-weight: 700; margin-bottom: 6px;">
            Cha phi ki bru Pnar
        </div>
        <div style="font-size: 0.92rem;">
            Wan iada i ia ka ktien yong i ha kam kani ka juk AI!
            Ka thong toh yow pynman ia ka ktien Pnar iow tip ki bru ha waroh ka pyrthai,
            kam ka Khasi. Kani ka kreh ym ye u leh samen.
            Toh ka kamram yong i yow iada, pynneh wei pynman ia ka ktien yong i kawa im.
        </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="
            border: 1px solid rgba(128,128,128,0.30);
            border-radius: 14px;
            padding: 14px;
            margin: 0 0 14px 0;
            background: rgba(128,128,128,0.08);
            line-height: 1.45;
        ">
        <div style="font-size: 1rem; font-weight: 700; margin-bottom: 6px;">
            To the Pnar people
        </div>
        <div style="font-size: 0.92rem;">
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

    if row is None and english is None and claim_id is None:
        st.error(
            "⚠️ The translation service is busy. Please try again."
        )

        if st.button(
            "Try again",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.pop("current_row", None)
            st.session_state.pop("current_english", None)
            st.session_state.pop("current_claim_id", None)
            st.rerun()

        return

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
                        "The server is busy. Your translation is still here. "
                        "Please press Save & Next again."
                    )
                else:
                    st.error(
                        result.get(
                            "error",
                            "The translation could not be saved. "
                            "Your text is still here.",
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
