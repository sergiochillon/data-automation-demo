#!/usr/bin/env python3
"""
Generates synthetic, messy business data for testing and demonstration purposes.
Contains deliberate, controlled data-quality issues:
- Completely empty rows & columns
- Exact duplicates
- Surrounding & redundant whitespace
- Mixed/all-caps casing
- Inconsistent email casing and invalid email patterns
- Inconsistent currency and numeric formatting
- CSV formula injection attempts
- Null / missing values
"""

from pathlib import Path
import pandas as pd
import numpy as np

# Deterministic seed for reproducible demo datasets
np.random.seed(42)

OUTPUT_DIR = Path(__file__).resolve().parent

DATA_RECORDS = [
    # Clean baseline
    {"customer_id": "CUST-1001", "name": "Vanguard Logistics", "email": "contact@vanguardlogistics.com", "city": "Chicago", "country": "United States", "phone": "+1-312-555-0143", "revenue": "$12,450.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1002", "name": "Helios Solar Solutions", "email": "info@heliossolar.de", "city": "Munich", "country": "Germany", "phone": "+49-89-555-0199", "revenue": "€ 8.920,00", "status": "Active", "notes_internal": None},
    
    # Empty row 1
    {"customer_id": None, "name": None, "email": None, "city": None, "country": None, "phone": None, "revenue": None, "status": None, "notes_internal": None},
    
    # Whitespace issues in name, email, revenue
    {"customer_id": "CUST-1003", "name": "  Apex   Industrial Supplies  ", "email": "   orders@apexsupplies.co.uk  ", "city": "Manchester", "country": "United Kingdom", "phone": "+44-161-555-0177", "revenue": " 18,200.50 ", "status": "Pending", "notes_internal": None},
    {"customer_id": "CUST-1004", "name": "NORDIC DATA LABS", "email": "SUPPORT@NORDICDATALABS.SE", "city": "Stockholm", "country": "Sweden", "phone": "+46-8-555-0182", "revenue": "45000", "status": "Active", "notes_internal": None},
    
    # Exact duplicate 1 of CUST-1004 (will appear again below)
    {"customer_id": "CUST-1004", "name": "NORDIC DATA LABS", "email": "SUPPORT@NORDICDATALABS.SE", "city": "Stockholm", "country": "Sweden", "phone": "+46-8-555-0182", "revenue": "45000", "status": "Active", "notes_internal": None},
    
    # Invalid email formats
    {"customer_id": "CUST-1005", "name": "Meridian Maritime Inc", "email": "maritime_sales_at_meridian.com", "city": "Rotterdam", "country": "Netherlands", "phone": "+31-10-555-0124", "revenue": "€ 24.150,00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1006", "name": "Starlight Hospitality Group", "email": "reservations@starlight", "city": "Paris", "country": "France", "phone": "+33-1-555-0191", "revenue": "€ 6.400,00", "status": "Inactive", "notes_internal": None},
    {"customer_id": "CUST-1007", "name": "Kuroshio Shipping", "email": "inquiry@kuroshio.co.jp", "city": "Yokohama", "country": "Japan", "phone": "+81-45-555-0163", "revenue": "¥ 3,200,000", "status": "Active", "notes_internal": None},

    # Empty row 2
    {"customer_id": "   ", "name": "", "email": None, "city": " ", "country": None, "phone": None, "revenue": None, "status": None, "notes_internal": None},

    # Currency format variations
    {"customer_id": "CUST-1008", "name": "Atlas Heavy Machinery", "email": "EQUIPMENT@ATLASMACHINERY.COM", "city": "Toronto", "country": "Canada", "phone": "+1-416-555-0112", "revenue": "$145,000.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1009", "name": "Castilla Consultores", "email": "javier.castilla@castillaconsult.es", "city": "Madrid", "country": "Spain", "phone": "+34-91-555-0138", "revenue": "€ 3.750,00", "status": "Active", "notes_internal": None},
    
    # Missing values
    {"customer_id": "CUST-1010", "name": "Orion Cyber Defense", "email": "security@oriondefense.io", "city": "Austin", "country": "United States", "phone": None, "revenue": None, "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1011", "name": "Lumina Medical Devices", "email": "compliance@luminamed.ch", "city": "Zurich", "country": "Switzerland", "phone": "+41-44-555-0155", "revenue": "$ 22,890.00", "status": "Pending", "notes_internal": None},

    # CSV injection attempt
    {"customer_id": "CUST-1012", "name": "=SUM(A1:A50)", "email": "finance@riskycorp.com", "city": "Dublin", "country": "Ireland", "phone": "+353-1-555-0189", "revenue": "$15,000.00", "status": "Review", "notes_internal": None},
    {"customer_id": "CUST-1013", "name": "@calc_exploit", "email": "admin@exploitdomain.com", "city": "London", "country": "United Kingdom", "phone": "+44-20-7946-0150", "revenue": "5000", "status": "Active", "notes_internal": None},

    # Exact duplicate 2 of CUST-1009
    {"customer_id": "CUST-1009", "name": "Castilla Consultores", "email": "javier.castilla@castillaconsult.es", "city": "Madrid", "country": "Spain", "phone": "+34-91-555-0138", "revenue": "€ 3.750,00", "status": "Active", "notes_internal": None},

    # More realistic rows with messy formatting
    {"customer_id": "CUST-1014", "name": "SILVERSTONE AEROSPACE", "email": "contracting@silverstoneaero.com", "city": "Seattle", "country": "United States", "phone": "+1-206-555-0178", "revenue": "$88,400.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1015", "name": "bavaria auto parts", "email": "VERTRIEB@BAVARIA-PARTS.DE", "city": "Stuttgart", "country": "Germany", "phone": "+49-711-555-0122", "revenue": "€ 14.500,00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1016", "name": "PACIFIC DRIFT FISHERIES", "email": "ops@pacificdrift.co.nz", "city": "Auckland", "country": "New Zealand", "phone": "+64-9-555-0144", "revenue": "31200", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1017", "name": "Solaria Renewable Tech", "email": "partner@solariarx..org", "city": "Milan", "country": "Italy", "phone": "+39-02-555-0168", "revenue": "€ 11.200,50", "status": "Pending", "notes_internal": None},
    {"customer_id": "CUST-1018", "name": "  zenith   robotics   corporation  ", "email": "LABS@ZENITHROBOTICS.COM", "city": "Tokyo", "country": "Japan", "phone": "+81-3-555-0184", "revenue": "$ 64,000.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1019", "name": "Alpine Timber Products", "email": "timber_sales@alpinetimber.at", "city": "Innsbruck", "country": "Austria", "phone": "+43-512-555-0111", "revenue": "€ 7.890,00", "status": "Active", "notes_internal": None},

    # Empty row 3
    {"customer_id": None, "name": None, "email": None, "city": None, "country": None, "phone": None, "revenue": None, "status": None, "notes_internal": None},

    # Non-numeric string in revenue
    {"customer_id": "CUST-1020", "name": "Beacon Pharma Labs", "email": "procurement@beaconpharma.com", "city": "Boston", "country": "United States", "phone": "+1-617-555-0193", "revenue": "UNKNOWN_PENDING", "status": "Under Review", "notes_internal": None},
    
    # Exact duplicate 3 of CUST-1014
    {"customer_id": "CUST-1014", "name": "SILVERSTONE AEROSPACE", "email": "contracting@silverstoneaero.com", "city": "Seattle", "country": "United States", "phone": "+1-206-555-0178", "revenue": "$88,400.00", "status": "Active", "notes_internal": None},

    # Additional standard rows to build a robust dataset
    {"customer_id": "CUST-1021", "name": "Horizon Digital Media", "email": "hello@horizondigital.ca", "city": "Vancouver", "country": "Canada", "phone": "+1-604-555-0129", "revenue": "$ 9,450.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1022", "name": "Iberia Freight Systems", "email": "LOGISTICA@IBERIAFREIGHT.ES", "city": "Valencia", "country": "Spain", "phone": "+34-96-555-0174", "revenue": "€ 16.300,00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1023", "name": "Aethelgard Consulting", "email": "claire.bennett@aethelgard.co.uk", "city": "Edinburgh", "country": "United Kingdom", "phone": "+44-131-555-0167", "revenue": "£ 21,500.00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1024", "name": "Polaris Energy Dynamics", "email": "investor_relations@polarisenergy.no", "city": "Oslo", "country": "Norway", "phone": "+47-22-555-0136", "revenue": "€ 54.000,00", "status": "Active", "notes_internal": None},
    {"customer_id": "CUST-1025", "name": "Cascade Software Works", "email": "accounts@cascade-works.com", "city": "Portland", "country": "United States", "phone": "+1-503-555-0148", "revenue": "$ 38,700.00", "status": "Active", "notes_internal": None},
]


def generate_files():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(DATA_RECORDS)

    csv_path = OUTPUT_DIR / "customers_messy.csv"
    xlsx_path = OUTPUT_DIR / "customers_messy.xlsx"

    # Export CSV
    df.to_csv(csv_path, index=False, encoding="utf-8")
    print(f"Generated demo CSV: {csv_path} ({len(df)} rows)")

    # Export Excel (.xlsx)
    df.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(f"Generated demo Excel: {xlsx_path} ({len(df)} rows)")


if __name__ == "__main__":
    generate_files()
