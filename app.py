import time

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials


# ============================================================
# CONFIGURATION
# ============================================================

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


st.set_page_config(
    page_title="Pnar Translation Tool",
    page_icon="📝",
    layout="centered",
)


# ============================================================
# GOOGLE AUTHENTICATION
# ============================================================

@st.cache_resource
def get_client():

    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=SCOPES,
    )

    return gspread.authorize(credentials)


# ============================================================
# CONTROL SHEET
# ============================================================

def get_control_sheet():

    client = get_client()

    control_spreadsheet = client.open_by_key(
        st.secrets["CONTROL_SHEET_ID"]
    )

    return control_spreadsheet.sheet1


def get_active_dataset():

    worksheet = get_control_sheet()

    row = worksheet.row_values(2)

    if not row:
        return "", ""

    sheet_id = row[0].strip() if len(row) >= 1 else ""
    sheet_name = row[1].strip() if len(row) >= 2 else ""

    return sheet_id, sheet_name


# ============================================================
# WORKING DATASET
# ============================================================

def get_working_sheet():

    sheet_id, sheet_name = get_active_dataset()

    if not sheet_id:
        return None

    client = get_client()

    spreadsheet = client.open_by_key(sheet_id)

    return spreadsheet.sheet1


# ============================================================
# FIND NEXT SENTENCE
# ============================================================

def get_next_sentence(worksheet):

    values = worksheet.get_all_values()

    for row_number, row in enumerate(values[1:], start=2):

        english = row[0].strip() if len(row) >= 1 else ""
        pnar = row[1].strip() if len(row) >= 2 else ""

        # Only select sentences that have:
        # 1. English text
        # 2. No Pnar translation yet
        if english and not pnar:

            return row_number, english

    return None, None


# ============================================================
# SAVE TRANSLATION
# ============================================================

def save_translation(
    worksheet,
    row_number,
    pnar_text,
    annotator_name,
):

    worksheet.update(
        f"B{row_number}:E{row_number}",
        [[
            pnar_text,
            annotator_name,
            "done",
            str(time.time()),
        ]],
    )


# ============================================================
# LOGIN
# ============================================================

def login_screen():

    st.title("📝 Pnar Translation Tool")

    st.write(
        "Enter your name before starting the translation work."
    )

    name = st.text_input(
        "Your name",
        placeholder="Enter your full name",
    )

    if st.button(
        "Start",
        type="primary",
        use_container_width=True,
    ):

        if not name.strip():

            st.warning(
                "Please enter your name first."
            )

        else:

            st.session_state.annotator_name = name.strip()

            # Initialize translation workflow
            st.session_state.review_mode = False
            st.session_state.pnar_draft = ""

            st.rerun()


# ============================================================
# TRANSLATION SCREEN
# ============================================================

def translation_screen():

    annotator = st.session_state.annotator_name

    st.title("📝 Pnar Translation Tool")

    st.caption(
        f"Translator: **{annotator}**"
    )

    worksheet = get_working_sheet()

    if worksheet is None:

        st.error(
            "No active dataset has been configured."
        )

        return

    dataset_id, dataset_name = get_active_dataset()

    st.caption(
        f"Dataset: **{dataset_name or dataset_id}**"
    )

    # ========================================================
    # GET A NEW SENTENCE
    # ========================================================

    if "current_row" not in st.session_state:

        row_number, english = get_next_sentence(
            worksheet
        )

        st.session_state.current_row = row_number
        st.session_state.current_english = english

        # New sentence starts with empty draft
        st.session_state.pnar_draft = ""

        # Start in translation mode
        st.session_state.review_mode = False

    row_number = st.session_state.current_row
    english = st.session_state.current_english

    # ========================================================
    # NO SENTENCES REMAIN
    # ========================================================

    if row_number is None:

        st.success(
            "🎉 No untranslated sentences remain in this dataset."
        )

        if st.button(
            "Check again",
            use_container_width=True,
        ):

            st.session_state.pop(
                "current_row",
                None,
            )

            st.session_state.pop(
                "current_english",
                None,
            )

            st.session_state.pnar_draft = ""
            st.session_state.review_mode = False

            st.rerun()

        return

    # ========================================================
    # REVIEW MODE
    # ========================================================

    if st.session_state.get("review_mode", False):

        # ----------------------------------------------------
        # English
        # ----------------------------------------------------

        st.markdown("### English")

        st.info(english)

        # ----------------------------------------------------
        # Pnar
        # ----------------------------------------------------

        st.markdown("### Pnar")

        st.success(
            st.session_state.pnar_draft
        )

        st.markdown("---")

        # ----------------------------------------------------
        # TWO BUTTONS
        # ----------------------------------------------------

        col1, col2 = st.columns(2)

        # ----------------------------------------------------
        # EDIT
        # ----------------------------------------------------

        with col1:

            if st.button(
                "✏️ Edit",
                use_container_width=True,
            ):

                st.session_state.review_mode = False

                st.rerun()

        # ----------------------------------------------------
        # SAVE & NEXT
        # ----------------------------------------------------

        with col2:

            if st.button(
                "✓ Save & Next",
                type="primary",
                use_container_width=True,
            ):

                pnar_text = (
                    st.session_state
                    .pnar_draft
                    .strip()
                )

                if not pnar_text:

                    st.warning(
                        "Please enter a Pnar translation."
                    )

                    return

                # --------------------------------------------
                # PERMANENT SAVE
                # --------------------------------------------

                save_translation(
                    worksheet,
                    row_number,
                    pnar_text,
                    annotator,
                )

                # --------------------------------------------
                # REMOVE CURRENT SENTENCE FROM SESSION
                # --------------------------------------------

                st.session_state.pop(
                    "current_row",
                    None,
                )

                st.session_state.pop(
                    "current_english",
                    None,
                )

                st.session_state.pnar_draft = ""

                st.session_state.review_mode = False

                # --------------------------------------------
                # LOAD NEXT SENTENCE
                # --------------------------------------------

                st.rerun()

        return

    # ========================================================
    # TRANSLATION MODE
    # ========================================================

    # --------------------------------------------------------
    # English
    # --------------------------------------------------------

    st.markdown("### English")

    st.info(english)

    # --------------------------------------------------------
    # Pnar input
    # --------------------------------------------------------

    st.markdown("### Pnar")

    pnar = st.text_area(
        "Type the Pnar translation",
        value=st.session_state.get(
            "pnar_draft",
            "",
        ),
        height=150,
        placeholder=(
            "Type the correct Pnar translation here..."
        ),
        key="pnar_input",
    )

    # --------------------------------------------------------
    # OK BUTTON
    # --------------------------------------------------------

    if st.button(
        "OK",
        type="primary",
        use_container_width=True,
    ):

        if not pnar.strip():

            st.warning(
                "Please enter the Pnar translation."
            )

            return

        # IMPORTANT:
        # This is only stored temporarily in the user's
        # Streamlit session.
        #
        # NOTHING is saved to Google Sheets yet.

        st.session_state.pnar_draft = pnar.strip()

        # Switch from input mode to review mode
        st.session_state.review_mode = True

        st.rerun()


# ============================================================
# MAIN
# ============================================================

if "annotator_name" not in st.session_state:

    login_screen()

else:

    translation_screen()