import pandas as pd
import numpy as np

import os

def find_data_dir(data_dir=None):
    if data_dir and os.path.exists(os.path.join(data_dir, "tickets.csv")):
        return data_dir
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        "src/data",
        "data",
        ".",
        os.path.join(script_dir, "data"),
        os.path.join(script_dir, "..", "data"),
        os.path.join(script_dir, ".."),
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, "tickets.csv")):
            return c
    return "."

def load_raw_data(data_dir=None):
    resolved_dir = find_data_dir(data_dir)
    return {
        'tickets': pd.read_csv(os.path.join(resolved_dir, "tickets.csv")),
        'agents': pd.read_csv(os.path.join(resolved_dir, "agents.csv")),
        'customers': pd.read_csv(os.path.join(resolved_dir, "customers.csv")),
        'orders': pd.read_csv(os.path.join(resolved_dir, "orders.csv")),
        'products': pd.read_csv(os.path.join(resolved_dir, "products.csv"))
    }

def clean_tickets(df):
    # 1. Deduplicate: prioritize helpdesk over legacy_fd
    df['priority_flag'] = df['source_system'].map({'helpdesk': 1, 'legacy_fd': 0})
    df = df.sort_values('priority_flag', ascending=False).drop_duplicates('ticket_id', keep='first')
    df = df.drop(columns=['priority_flag'])

    # 2. Treat CSAT 0 as missing NaN
    df['csat_score'] = df['csat_score'].replace(0, np.nan)

    # 3. Numeric refunds
    df['refund_amount_inr'] = pd.to_numeric(df['refund_amount_inr'], errors='coerce').fillna(0.0)

    # 4. Dates & broken timestamps
    for col in ['created_at', 'first_response_at', 'resolved_at']:
        df[col] = pd.to_datetime(df[col], errors='coerce')
    df['is_timestamp_broken'] = df['resolved_at'] < df['created_at']

    # 5. Distinguish genuine resolutions
    df['is_resolved_genuine'] = df['status'] == 'resolved'
    return df

def clean_data(data_dir=None):
    raw = load_raw_data(data_dir)
    return {
        'tickets': clean_tickets(raw['tickets']),
        'agents': raw['agents'],
        'customers': raw['customers'],
        'orders': raw['orders'],
        'products': raw['products']
    }
