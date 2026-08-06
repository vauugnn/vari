"""Shared fixtures. The .sav fixture is synthesised with pyreadstat — we never
bundle IBM sample datasets (see CLAUDE.md: assets are out of bounds)."""
import pandas as pd
import pytest


@pytest.fixture(scope="session")
def sav_path(tmp_path_factory):
    """A small survey-shaped .sav with value labels, discrete + range missing,
    a string variable, and explicit formats."""
    import pyreadstat

    path = str(tmp_path_factory.mktemp("data") / "survey.sav")
    df = pd.DataFrame(
        {
            "id": [1.0, 2.0, 3.0, 4.0],
            "gender": [1.0, 2.0, 1.0, 9.0],       # 9 = user-missing (discrete)
            "income": [50000.0, 60000.0, 999999.0, 45000.0],  # 999999 = range-missing
            "agree": [1.0, 5.0, 3.0, 9.0],        # 9 = user-missing (discrete)
            "sname": ["al", "bo", "cy", "di"],
        }
    )
    pyreadstat.write_sav(
        df,
        path,
        column_labels=["Respondent ID", "Gender", "Annual income", "Agreement", "Subject name"],
        variable_value_labels={
            "gender": {1.0: "Male", 2.0: "Female", 9.0: "No answer"},
            "agree": {1.0: "Strongly disagree", 3.0: "Neutral", 5.0: "Strongly agree", 9.0: "No answer"},
        },
        variable_measure={
            "id": "scale",
            "gender": "nominal",
            "income": "scale",
            "agree": "ordinal",
            "sname": "nominal",
        },
        variable_format={
            "id": "F8.0",
            "gender": "F8.0",
            "income": "F8.0",
            "agree": "F8.0",
            "sname": "A8",
        },
        missing_ranges={
            "gender": [{"lo": 9.0, "hi": 9.0}],
            "income": [{"lo": 999998.0, "hi": 999999.0}],
            "agree": [{"lo": 9.0, "hi": 9.0}],
        },
    )
    return path
