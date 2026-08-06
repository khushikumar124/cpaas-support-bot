from __future__ import annotations

from datasources.google_sheets_source import (
    COLUMN_MAPS,
    _normalize_row,
    _rows_from_values,
)


def test_rows_from_values_tolerates_duplicate_and_blank_headers():
    rows = _rows_from_values(
        [
            ["VMN/Number ", "", "Status", "Status", "Operator"],
            ["9223071030", "ignored", "Active", "duplicate", "Jio"],
            ["9152001212", "", "Inactive"],
        ]
    )

    assert rows == [
        {"VMN/Number": "9223071030", "Status": "Active", "Operator": "Jio"},
        {"VMN/Number": "9152001212", "Status": "Inactive", "Operator": ""},
    ]


def test_vmn_header_aliases_normalize_to_canonical_fields():
    row = _normalize_row(
        {
            "Phone Number": " 9223071030 ",
            "State": " Active ",
            "Provider": " Jio ",
            "Number Type": " Longcode ",
        },
        COLUMN_MAPS["vmn"],
    )

    assert row == {
        "number": "9223071030",
        "status": "Active",
        "operator": "Jio",
        "number_type": "Longcode",
    }


def test_gateway_header_aliases_normalize_to_canonical_fields():
    row = _normalize_row(
        {
            "GW ID": " 470 ",
            "Company Name": " Acme ",
            "Status": " Active ",
            "Gateway Type": " SMPP ",
        },
        COLUMN_MAPS["gateway"],
    )

    assert row == {
        "gateway_id": "470",
        "company_name": "Acme",
        "status": "Active",
        "gateway_type": "SMPP",
    }
