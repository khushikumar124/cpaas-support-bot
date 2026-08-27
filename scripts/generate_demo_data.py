#!/usr/bin/env python3
"""
Regenerate the fictional demo dataset in data/.

Run from the repo root:

    python scripts/generate_demo_data.py

Deterministic: a fixed seed means re-running produces byte-identical CSVs, so
the committed data and this script never drift apart.

Two rules this script exists to enforce:

1. **Anchor rows are verbatim.** Identifiers referenced by tests, the UI quick
   commands, and the README (gateway 470, number 9152001212, ticket TKT007,
   customer CUST003, source SRC008, ...) are hardcoded below and always emitted
   first, unchanged. Generated rows are appended around them.

2. **Referential integrity holds.** Every VMN points at a real gateway, every
   ticket at a real number, every customer and source at a real gateway, and a
   VMN's company_name always matches its gateway's owner. tests/
   test_demo_dataset.py asserts all of this.

Vocabulary is constrained to the values the parsers actually emit (operator
"IDEA" not "Vodafone Idea", number_type "Toll free" not "tollfree"). A filter is
matched verbatim against this data, so inventing a new spelling here would
silently return zero rows.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SEED = 20240517

# --- Canonical vocabulary (must match the parsers) --------------------------

OPERATORS = ["Airtel", "Jio", "IDEA", "TATA", "BSNL"]
NUMBER_TYPES = [
    "transactional",
    "promotional",
    "did",
    "Toll free",
    "Dedicated Incoming SMS",
    "Dedicated Missed call",
]
ENTITY_STATUSES = ["active", "inactive", "suspended"]
TICKET_STATUSES = ["open", "resolved", "in_progress"]
PRIORITIES = ["high", "medium", "low"]
REGIONS = ["IN", "IN", "IN", "SG", "AE", "US", "UK"]

ACCOUNT_MANAGERS = [
    "Priya Sharma", "Rahul Mehta", "Anita Rao", "Vikram Singh",
    "Neha Kulkarni", "Arjun Nair", "Sneha Iyer", "Karan Malhotra",
    "Divya Menon", "Rohit Bansal", "Farah Qureshi", "Aditya Ghosh",
]

# --- Anchor rows: referenced by tests, the UI, and the README ---------------

ANCHOR_GATEWAYS = [
    ("470", "Acme Retail Pvt Ltd", "IN", "active", "2023-06-01"),
    ("531", "Beta Logistics Ltd", "IN", "active", "2023-09-15"),
    ("612", "Cirrus Fintech Pvt Ltd", "IN", "active", "2023-11-02"),
    ("704", "Delta Health Services Ltd", "IN", "inactive", "2024-01-20"),
    ("815", "Everest EdTech Pvt Ltd", "IN", "active", "2024-02-11"),
    ("926", "Frontier Travel Ltd", "SG", "suspended", "2024-03-05"),
    ("1043", "Gamma Media Networks Pvt Ltd", "IN", "active", "2024-04-18"),
    ("1157", "Horizon Bank Ltd", "IN", "active", "2024-06-09"),
    ("1268", "Indus Grocers Pvt Ltd", "AE", "inactive", "2024-07-22"),
    ("1390", "Juno Mobility Pvt Ltd", "SG", "active", "2024-09-13"),
]

ANCHOR_VMN = [
    ("9152001212", "active", "Airtel", "Acme Retail Pvt Ltd", "470", "2024-01-15", "transactional"),
    ("8100881008", "suspended", "Jio", "Acme Retail Pvt Ltd", "470", "2024-02-20", "promotional"),
    ("9152004488", "active", "IDEA", "Acme Retail Pvt Ltd", "470", "2024-02-28", "Toll free"),
    ("9152007733", "active", "Airtel", "Acme Retail Pvt Ltd", "470", "2024-05-06", "Dedicated Incoming SMS"),
    ("9223071030", "active", "IDEA", "Beta Logistics Ltd", "531", "2024-03-01", "transactional"),
    ("9876543210", "active", "Airtel", "Beta Logistics Ltd", "531", "2024-04-12", "transactional"),
    ("9223078812", "inactive", "BSNL", "Beta Logistics Ltd", "531", "2023-10-19", "promotional"),
    ("9223074455", "active", "TATA", "Beta Logistics Ltd", "531", "2024-06-21", "did"),
    ("8800112233", "active", "Jio", "Cirrus Fintech Pvt Ltd", "612", "2024-01-08", "transactional"),
    ("8800119977", "active", "Airtel", "Cirrus Fintech Pvt Ltd", "612", "2024-03-17", "Toll free"),
    ("8800115566", "suspended", "IDEA", "Cirrus Fintech Pvt Ltd", "612", "2024-07-30", "promotional"),
    ("9988776655", "inactive", "Jio", "Delta Health Services Ltd", "704", "2023-12-05", "promotional"),
    ("9988771122", "inactive", "Airtel", "Delta Health Services Ltd", "704", "2023-12-05", "transactional"),
    ("9123456789", "active", "Airtel", "Everest EdTech Pvt Ltd", "815", "2023-08-30", "transactional"),
    ("9123454422", "active", "TATA", "Everest EdTech Pvt Ltd", "815", "2024-02-14", "Dedicated Missed call"),
    ("9123458899", "active", "Jio", "Everest EdTech Pvt Ltd", "815", "2024-04-02", "transactional"),
    ("7700334455", "suspended", "BSNL", "Frontier Travel Ltd", "926", "2024-03-11", "promotional"),
    ("7700338866", "suspended", "Airtel", "Frontier Travel Ltd", "926", "2024-03-11", "transactional"),
    ("9330012345", "active", "IDEA", "Gamma Media Networks Pvt Ltd", "1043", "2024-04-25", "promotional"),
    ("9330016789", "active", "Jio", "Gamma Media Networks Pvt Ltd", "1043", "2024-05-19", "Toll free"),
    ("9330019900", "active", "Airtel", "Gamma Media Networks Pvt Ltd", "1043", "2024-08-07", "did"),
    ("8455221100", "active", "Airtel", "Horizon Bank Ltd", "1157", "2024-06-15", "transactional"),
    ("8455223344", "active", "TATA", "Horizon Bank Ltd", "1157", "2024-06-15", "Dedicated Incoming SMS"),
    ("8455227788", "active", "Jio", "Horizon Bank Ltd", "1157", "2024-09-01", "Toll free"),
    ("8455229911", "inactive", "IDEA", "Horizon Bank Ltd", "1157", "2024-10-12", "promotional"),
    ("7011445566", "inactive", "BSNL", "Indus Grocers Pvt Ltd", "1268", "2024-07-28", "promotional"),
    ("7011449988", "inactive", "Jio", "Indus Grocers Pvt Ltd", "1268", "2024-07-28", "transactional"),
    ("9660112233", "active", "Airtel", "Juno Mobility Pvt Ltd", "1390", "2024-09-20", "transactional"),
    ("9660117744", "active", "IDEA", "Juno Mobility Pvt Ltd", "1390", "2024-10-05", "did"),
    ("9660119955", "active", "TATA", "Juno Mobility Pvt Ltd", "1390", "2024-11-11", "Dedicated Missed call"),
]

ANCHOR_CUSTOMERS = [
    ("CUST001", "Acme Retail Pvt Ltd", "Priya Sharma", "active", "470"),
    ("CUST002", "Beta Logistics Ltd", "Rahul Mehta", "active", "531"),
    ("CUST003", "Cirrus Fintech Pvt Ltd", "Anita Rao", "active", "612"),
    ("CUST004", "Delta Health Services Ltd", "Vikram Singh", "inactive", "704"),
    ("CUST005", "Everest EdTech Pvt Ltd", "Priya Sharma", "active", "815"),
    ("CUST006", "Frontier Travel Ltd", "Neha Kulkarni", "suspended", "926"),
    ("CUST007", "Gamma Media Networks Pvt Ltd", "Rahul Mehta", "active", "1043"),
    ("CUST008", "Horizon Bank Ltd", "Arjun Nair", "active", "1157"),
    ("CUST009", "Indus Grocers Pvt Ltd", "Neha Kulkarni", "inactive", "1268"),
    ("CUST010", "Juno Mobility Pvt Ltd", "Arjun Nair", "active", "1390"),
]

ANCHOR_TICKETS = [
    ("TKT001", "9152001212", "OTP delivery failure", "open", "high", "2024-05-10"),
    ("TKT002", "8100881008", "Promotional route suspended", "resolved", "medium", "2024-04-22"),
    ("TKT003", "9223071030", "Latency on transactional route", "open", "high", "2024-05-12"),
    ("TKT004", "9876543210", "DLR mismatch investigation", "in_progress", "low", "2024-05-01"),
    ("TKT005", "8800115566", "Sender ID rejected by operator", "open", "high", "2024-06-03"),
    ("TKT006", "9988776655", "Number deactivation request", "resolved", "low", "2024-06-14"),
    ("TKT007", "7700334455", "Gateway suspended after billing hold", "open", "high", "2024-06-28"),
    ("TKT008", "9330012345", "Promotional traffic throttled at peak hours", "in_progress", "medium", "2024-07-09"),
    ("TKT009", "8455227788", "Toll free number not reachable from BSNL", "open", "medium", "2024-07-21"),
    ("TKT010", "9123454422", "Missed call webhook not firing", "resolved", "medium", "2024-08-02"),
    ("TKT011", "8455229911", "Bulk campaign delivery delay", "in_progress", "high", "2024-08-19"),
    ("TKT012", "7011445566", "Account reactivation after inactivity", "open", "low", "2024-09-04"),
    ("TKT013", "9660117744", "DID provisioning stuck in pending", "resolved", "medium", "2024-09-27"),
    ("TKT014", "9152004488", "Toll free IVR routing misconfiguration", "in_progress", "high", "2024-10-15"),
]

ANCHOR_SOURCES = [
    ("SRC001", "470", "SMPP", "active", "smpp1.example.com", "2775"),
    ("SRC002", "531", "SMPP", "active", "smpp2.example.com", "2775"),
    ("SRC003", "612", "HTTP", "active", "api.example.com", "443"),
    ("SRC004", "704", "SMPP", "inactive", "smpp-legacy.example.com", "2775"),
    ("SRC005", "815", "SMPP", "active", "smpp3.example.com", "2775"),
    ("SRC006", "926", "HTTP", "suspended", "api-sg.example.com", "443"),
    ("SRC007", "1043", "SMPP", "active", "smpp4.example.com", "2775"),
    ("SRC008", "1157", "SMPP", "active", "smpp-secure.example.com", "3550"),
    ("SRC009", "1157", "HTTP", "active", "api-bank.example.com", "443"),
    ("SRC010", "1268", "SMPP", "inactive", "smpp-ae.example.com", "2775"),
    ("SRC011", "1390", "HTTP", "active", "api-sg2.example.com", "443"),
    ("SRC012", "1390", "SMPP", "active", "smpp5.example.com", "2775"),
]

# --- Additional fictional companies ----------------------------------------

NEW_COMPANIES = [
    "Kinetic Sports Pvt Ltd", "Lumen Energy Ltd", "Meridian Insurance Pvt Ltd",
    "Nimbus Cloud Services Ltd", "Orbit Payments Pvt Ltd", "Pinnacle Realty Ltd",
    "Quasar Analytics Pvt Ltd", "Radiant Pharma Ltd", "Summit Auto Pvt Ltd",
    "Tandem Staffing Ltd", "Umbra Security Pvt Ltd", "Vertex Foods Ltd",
    "Westline Shipping Pvt Ltd", "Xenon Telecom Ltd", "Yield Agritech Pvt Ltd",
    "Zenith Hotels Ltd", "Aurora Fashion Pvt Ltd", "Beacon Legal Services Ltd",
    "Cobalt Manufacturing Pvt Ltd", "Drift Mobility Ltd",
]

TICKET_SUBJECTS = [
    "OTP delivery failure", "Sender ID rejected by operator", "DLR mismatch investigation",
    "Latency on transactional route", "Promotional route suspended",
    "Bulk campaign delivery delay", "Webhook callbacks not received",
    "SMPP bind failing intermittently", "Throughput below contracted TPS",
    "Toll free number not reachable", "DID provisioning stuck in pending",
    "Number porting request", "Unicode messages arriving garbled",
    "Duplicate message delivery", "Billing discrepancy on monthly invoice",
    "Route change request for peak hours", "Account reactivation after inactivity",
    "Missed call webhook not firing", "Delivery reports delayed by several hours",
    "Operator blocking template mismatch", "Long code deactivation request",
    "Failover route not engaging", "TLS certificate expiry on SMPP bind",
    "Rate limit errors during campaign", "Sender ID registration pending",
]

HOST_PREFIXES = ["smpp", "api", "gw", "msg", "relay"]


def daterange(rng: random.Random, start: date, end: date) -> str:
    span = (end - start).days
    return (start + timedelta(days=rng.randrange(span))).isoformat()


def write_csv(name: str, header: list[str], rows: list[tuple]) -> None:
    path = DATA_DIR / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)
    print(f"  {name:<20} {len(rows):>4} rows")


def main() -> None:
    rng = random.Random(SEED)
    start, end = date(2023, 1, 1), date(2025, 12, 31)

    # --- Gateways ----------------------------------------------------------
    gateways = list(ANCHOR_GATEWAYS)
    gateway_owner = {gid: company for gid, company, *_ in gateways}
    next_id = 1450

    for company in NEW_COMPANIES:
        next_id += rng.randrange(23, 97)
        gid = str(next_id)
        gateways.append(
            (gid, company, rng.choice(REGIONS),
             rng.choices(ENTITY_STATUSES, weights=[7, 2, 1])[0],
             daterange(rng, start, end))
        )
        gateway_owner[gid] = company

    # A handful of larger accounts run a second gateway.
    for company in rng.sample(NEW_COMPANIES, 6):
        next_id += rng.randrange(23, 97)
        gid = str(next_id)
        gateways.append(
            (gid, company, rng.choice(REGIONS),
             rng.choices(ENTITY_STATUSES, weights=[8, 1, 1])[0],
             daterange(rng, start, end))
        )
        gateway_owner[gid] = company

    # --- Customers ---------------------------------------------------------
    customers = list(ANCHOR_CUSTOMERS)
    for index, company in enumerate(NEW_COMPANIES, start=11):
        primary = next(g for g, owner in gateway_owner.items() if owner == company)
        customers.append((
            f"CUST{index:03d}", company, rng.choice(ACCOUNT_MANAGERS),
            rng.choices(ENTITY_STATUSES, weights=[7, 2, 1])[0], primary,
        ))

    # --- VMNs --------------------------------------------------------------
    vmn = list(ANCHOR_VMN)
    used_numbers = {row[0] for row in vmn}
    new_gateway_ids = [g for g in gateway_owner if g not in {a[0] for a in ANCHOR_GATEWAYS}]

    for gid in new_gateway_ids:
        for _ in range(rng.randrange(3, 8)):
            while True:
                number = f"{rng.choice('6789')}{rng.randrange(10**8, 10**9):09d}"[:10]
                if number not in used_numbers:
                    used_numbers.add(number)
                    break
            vmn.append((
                number,
                rng.choices(ENTITY_STATUSES, weights=[7, 2, 1])[0],
                rng.choice(OPERATORS),
                gateway_owner[gid],
                gid,
                daterange(rng, start, end),
                rng.choices(NUMBER_TYPES, weights=[5, 4, 2, 2, 1, 1])[0],
            ))

    # --- Tickets -----------------------------------------------------------
    tickets = list(ANCHOR_TICKETS)
    all_numbers = [row[0] for row in vmn]
    for index in range(15, 76):
        tickets.append((
            f"TKT{index:03d}",
            rng.choice(all_numbers),
            rng.choice(TICKET_SUBJECTS),
            rng.choices(TICKET_STATUSES, weights=[4, 4, 2])[0],
            rng.choices(PRIORITIES, weights=[3, 4, 3])[0],
            daterange(rng, start, end),
        ))

    # --- Source lines ------------------------------------------------------
    sources = list(ANCHOR_SOURCES)
    index = 13
    for gid in new_gateway_ids:
        for _ in range(rng.randrange(1, 3)):
            line_type = rng.choices(["SMPP", "HTTP"], weights=[3, 2])[0]
            port = "443" if line_type == "HTTP" else rng.choice(["2775", "2776", "3550"])
            sources.append((
                f"SRC{index:03d}", gid, line_type,
                rng.choices(ENTITY_STATUSES, weights=[8, 1, 1])[0],
                f"{rng.choice(HOST_PREFIXES)}{rng.randrange(1, 40)}.example.com",
                port,
            ))
            index += 1

    print(f"Regenerating demo data in {DATA_DIR} (seed={SEED})")
    write_csv("gateways.csv",
              ["gateway_id", "company_name", "region", "status", "created_date"], gateways)
    write_csv("customers.csv",
              ["customer_id", "company_name", "account_manager", "status", "primary_gateway"], customers)
    write_csv("vmn.csv",
              ["number", "status", "operator", "company_name", "gateway_id",
               "provisioned_date", "number_type"], vmn)
    write_csv("tickets.csv",
              ["ticket_id", "number", "subject", "status", "priority", "created_date"], tickets)
    write_csv("source_info.csv",
              ["source_id", "gateway_id", "line_type", "status", "host", "port"], sources)


if __name__ == "__main__":
    main()
