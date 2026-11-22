
Hospital Staff Duty & Presence Manager
--------------------------------------
Run:
    pip install -r requirements.txt
    streamlit run app.py

Configure xAI:
    Set XAI_API_KEY in your environment, or add it to .streamlit/secrets.toml:
        XAI_API_KEY = "your-key"
    Optional:
        XAI_MODEL = "grok-4-1-fast"

Privacy and safety:
- Presence is recorded through authorized manual check-in/out; this app does not
  use facial recognition, covert tracking, or infer a person's location.
- Use only with hospital authorization, role-based access, staff notice, and
  applicable employment/privacy policies.
- AI features summarize operational data only. They must not make clinical,
  disciplinary, payroll, or autonomous staffing decisions.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, time, timedelta
from typing import Any

import pandas as pd
import streamlit as st
from openai import OpenAI

APP_TITLE = "Hospital Staff Duty & Presence Manager"
DB_PATH = os.getenv("HOSPITAL_DB_PATH", "hospital_staff.db")
DEFAULT_MODEL = os.getenv("XAI_MODEL", "grok-4.7")
XAI_BASE_URL = "https://api.x.ai/v1"

st.set_page_config(page_title=APP_TITLE, page_icon="🏥", layout="wide")

# ---------- Database ----------
def db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con

def init_db() -> None:
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                phone TEXT DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                duty_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                shift_label TEXT NOT NULL,
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(staff_id) REFERENCES staff(id)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS presence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT,
                recorded_by TEXT NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY(staff_id) REFERENCES staff(id)
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

def log_action(action: str, details: str) -> None:
    with db() as con:
        con.execute(
