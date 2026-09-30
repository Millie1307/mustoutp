
import streamlit as st
import pandas as pd
import sys
import os

# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Outpatient Data Quality Improvement System",
    page_icon="📊",
    layout="wide"
)


# ---------------------------------------------------------
# Load validation engine
# ---------------------------------------------------------

sys.path.append(os.path.dirname(__file__))

from validation_engine import validate_outpatient_data


# ---------------------------------------------------------
# File paths
# ---------------------------------------------------------

DATA_PATH = os.path.join(
    os.path.dirname(__file__),
    "outpatient_merged.csv"
)


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)


# ---------------------------------------------------------
# Patient record definition
# ---------------------------------------------------------

def get_patient_records(df):

    structural_pt_values = [
        "Patient No",
        "PATIENT NO",
        "PATIENT NUMBER"
    ]

    is_patient = (
        df["PT NO."].notna()
        & ~df["PT NO."].astype("string").str.strip().isin(
            structural_pt_values
        )
    )

    return df[is_patient].copy()


# ---------------------------------------------------------
# Load and validate
# ---------------------------------------------------------

try:

    raw_df = load_data()

    patient_df = get_patient_records(raw_df)

    validation_df = validate_outpatient_data(
        patient_df
    )

except Exception as e:

    st.error(
        f"Unable to load or validate the outpatient data: {e}"
    )

    st.stop()


# ---------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------

st.sidebar.title("📊 Data Quality System")

page = st.sidebar.radio(
    "Navigate to",
    [
        "Overview",
        "Data Quality Summary",
        "Completeness",
        "Validity & Consistency",
        "Identifier Validation",
        "Duplicates & Structural Records",
        "Review Queue",
        "How to Use"
    ]
)


# ---------------------------------------------------------
# Overview
# ---------------------------------------------------------

if page == "Overview":

    st.title(
        "Outpatient Data Quality Improvement System"
    )

    st.markdown(
        """
        This system assesses the quality of outpatient
        medical records by checking completeness, validity,
        consistency, identifiers, and possible duplicates.

        It identifies records that may require review,
        correction, or standardization before the data
        is used for analysis or reporting.
        """
    )

    st.info(
        "The system validates patient records using predefined "
        "data-quality rules. It does not automatically alter "
        "the original records."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Total records",
            f"{len(raw_df):,}"
        )

    with col2:
        st.metric(
            "Patient records",
            f"{len(patient_df):,}"
        )

    with col3:
        st.metric(
            "Structural / non-patient",
            f"{len(raw_df) - len(patient_df):,}"
        )

    st.divider()

    st.subheader("What does the system check?")

    checks = pd.DataFrame({
        "Area": [
            "Completeness",
            "Validity",
            "Consistency",
            "Identifiers",
            "Duplicates"
        ],
        "Purpose": [
            "Checks whether expected information has been recorded.",
            "Checks whether values follow expected formats or ranges.",
            "Checks whether values follow agreed categories and conventions.",
            "Checks category-specific registration and PF requirements.",
            "Identifies exact duplicates and repeated observation numbers."
        ]
    })

    st.dataframe(
        checks,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# Data Quality Summary
# ---------------------------------------------------------

elif page == "Data Quality Summary":

    st.title("📊 Data Quality Summary")

    actionable = validation_df["NEEDS_ACTION"].sum()
    no_action = len(validation_df) - actionable

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Patient records",
            f"{len(validation_df):,}"
        )

    with col2:
        st.metric(
            "Require action / review",
            f"{actionable:,}"
        )

    with col3:
        st.metric(
            "No actionable finding",
            f"{no_action:,}"
        )

    st.divider()

    st.subheader("Overall validation results")

    summary = (
        validation_df["OVERALL_RESULT"]
        .value_counts()
        .rename_axis("Result")
        .reset_index(name="Records")
    )

    summary["Percentage"] = (
        summary["Records"]
        / len(validation_df)
        * 100
    ).round(2)

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# Completeness
# ---------------------------------------------------------

elif page == "Completeness":

    st.title("📝 Completeness")

    st.markdown(
        """
        Completeness describes whether expected information
        has been recorded.

        A missing value is only treated as an actionable
        issue where the field is considered required or
        expected under the validation rules.
        """
    )

    fields = [
        "DATE",
        "DIAGNOSIS",
        "AGE",
        "GENDER",
        "STATUS",
        "CATEGORY",
        "PATIENT NAME"
    ]

    completeness = []

    for field in fields:

        missing = (
            validation_df[field].isna()
            | validation_df[field].astype("string").str.strip().eq("")
        ).sum()

        complete = len(validation_df) - missing

        completeness.append({
            "Field": field,
            "Complete": complete,
            "Missing": missing,
            "Completeness (%)": round(
                complete / len(validation_df) * 100,
                2
            )
        })

    completeness_df = pd.DataFrame(
        completeness
    )

    st.dataframe(
        completeness_df,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# Validity & Consistency
# ---------------------------------------------------------

elif page == "Validity & Consistency":

    st.title("🔍 Validity & Consistency")

    st.markdown(
        """
        These checks determine whether values follow the
        agreed validation rules.

        The system does not automatically correct ambiguous
        values. Records requiring human verification are
        sent to the review queue.
        """
    )

    result_columns = {
        "AGE_RESULT": "Age",
        "DATE_RESULT": "Date",
        "GENDER_RESULT": "Gender",
        "STATUS_RESULT": "Status",
        "DIAGNOSIS_RESULT": "Diagnosis",
        "REVISIT_RESULT": "RE-VISIT"
    }

    rows = []

    for column, field in result_columns.items():

        counts = (
            validation_df[column]
            .value_counts()
            .to_dict()
        )

        for result, count in counts.items():

            rows.append({
                "Field": field,
                "Result": result,
                "Records": count
            })

    validity_df = pd.DataFrame(rows)

    st.dataframe(
        validity_df,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# Identifier Validation
# ---------------------------------------------------------

elif page == "Identifier Validation":

    st.title("🪪 Identifier & Cross-field Validation")

    st.markdown(
        """
        Identifier rules depend on patient category.

        **Student:** Registration No. expected.

        **Employee, Dependant and Private Citizen:**
        PF No. expected.

        **OPD No.:** treated as optional because it may be
        issued during a patient's first outpatient visit and
        not necessarily repeated on subsequent visits.
        """
    )

    identifier_columns = [
        "REGISTRATION_RESULT",
        "PF_RESULT",
        "OPD_RESULT"
    ]

    rows = []

    for column in identifier_columns:

        counts = (
            validation_df[column]
            .value_counts()
            .to_dict()
        )

        for result, count in counts.items():

            rows.append({
                "Identifier": column.replace(
                    "_RESULT",
                    ""
                ),
                "Result": result,
                "Records": count
            })

    identifier_df = pd.DataFrame(rows)

    st.dataframe(
        identifier_df,
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# Duplicates & Structural Records
# ---------------------------------------------------------

elif page == "Duplicates & Structural Records":

    st.title("♻️ Duplicates & Structural Records")

    raw_structural = len(raw_df) - len(patient_df)

    exact_duplicates = (
        validation_df["EXACT_DUPLICATE_RESULT"]
        .eq("Review")
        .sum()
    )

    repeated_observations = (
        validation_df["OBSERVATION_RESULT"]
        .eq("Review")
        .sum()
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Structural / non-patient records",
            f"{raw_structural:,}"
        )

    with col2:
        st.metric(
            "Exact duplicate records",
            f"{exact_duplicates:,}"
        )

    with col3:
        st.metric(
            "Repeated observation records",
            f"{repeated_observations:,}"
        )

    st.info(
        "Repeated observation numbers are not automatically "
        "treated as duplicate patients. They require review "
        "because they may represent multiple service transactions."
    )


# ---------------------------------------------------------
# Review Queue
# ---------------------------------------------------------

elif page == "Review Queue":

    st.title("⚠️ Review Queue")

    st.markdown(
        """
        These records contain at least one actionable
        validation finding.

        **Review does not mean the record is definitely wrong.**
        The original source record should be checked before
        making a correction.
        """
    )

    review_df = validation_df[
        validation_df["NEEDS_ACTION"]
    ].copy()

    st.metric(
        "Records requiring action",
        f"{len(review_df):,}"
    )

    display_columns = [
        "CATEGORY",
        "DATE",
        "AGE",
        "GENDER",
        "STATUS",
        "DIAGNOSIS",
        "RE-VISIT",
        "AGE_RESULT",
        "GENDER_RESULT",
        "STATUS_RESULT",
        "DIAGNOSIS_RESULT",
        "REVISIT_RESULT",
        "OVERALL_RESULT",
        "ACTIONABLE_FLAG_COUNT"
    ]

    available_columns = [
        column
        for column in display_columns
        if column in review_df.columns
    ]

    st.dataframe(
        review_df[available_columns],
        use_container_width=True,
        hide_index=True
    )


# ---------------------------------------------------------
# How to Use
# ---------------------------------------------------------

elif page == "How to Use":

    st.title("📖 How to Use the Validation System")

    st.subheader("Validation key")

    key = pd.DataFrame({
        "Result": [
            "Pass",
            "Review",
            "Invalid",
            "Standardize",
            "Context-dependent",
            "Informational",
            "Missing"
        ],
        "Meaning": [
            "The record meets the validation rule.",
            "The value is unusual or potentially problematic and should be checked.",
            "The value clearly violates the expected format or range.",
            "The value is conceptually usable but should be converted to the standard format.",
            "Interpretation depends on the service context and is not automatically an error.",
            "No correction is required under the current rule.",
            "Expected information was not recorded."
        ],
        "Action": [
            "No immediate action.",
            "Check the original record.",
            "Verify and correct after checking the source.",
            "Standardize while preserving the original value.",
            "Interpret using the relevant service context.",
            "No correction required.",
            "Check whether the information can be recovered."
        ]
    })

    st.dataframe(
        key,
        use_container_width=True,
        hide_index=True
    )

    st.divider()

    st.subheader("Important principle")

    st.warning(
        "The validation system supports data-quality review. "
        "It does not replace verification against the original "
        "medical record and does not automatically overwrite "
        "source data."
    )
