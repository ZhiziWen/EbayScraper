"""
LEGO Price Analysis - Email Report Generator

Reads the latest price comparison CSV, generates sell/hold recommendations,
and sends an HTML email report to configured recipients.
"""

import os
import glob
import json
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd


def load_config():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, 'config.json')
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"Config file not found: {config_path}\n"
            "Please copy config.json.template to config.json and fill in your Gmail App Password."
        )
    with open(config_path) as f:
        return json.load(f)


def find_latest_comparison_csv():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, 'data')
    pattern = os.path.join(data_dir, 'Price_Comparison_Results_*.csv')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError("No Price_Comparison_Results CSV found in data/. Run price_comparison.py first.")
    return max(files, key=os.path.getctime)


def add_recommendations(df):
    """Add recommendation and sort priority columns based on profit and liquidity."""
    def _recommend(row):
        pct = row['Median Price Diff %']
        sold = row['Number Sold']
        if pct >= 20 and sold >= 5:
            return ('Sell Now', 1)
        elif pct >= 10:
            return ('Consider Selling', 2)
        elif pct >= 0:
            return ('Hold', 3)
        else:
            return ('Not Worth Selling', 4)

    results = df.apply(_recommend, axis=1)
    df = df.copy()
    df['Recommendation'] = results.apply(lambda x: x[0])
    df['_sort'] = results.apply(lambda x: x[1])
    return df.sort_values(['_sort', 'Median Price Diff %'], ascending=[True, False]).drop(columns=['_sort'])


def _table_rows(df):
    rows = []
    for _, row in df.iterrows():
        profit = row['Potential Profit (Median)']
        pct = row['Median Price Diff %']
        color = '#27ae60' if profit >= 0 else '#e74c3c'
        rows.append(f"""
            <tr style="border-bottom:1px solid #eee">
                <td style="padding:7px 10px">{row['LEGO Set Number']}</td>
                <td style="padding:7px 10px">{row['Set Name']}</td>
                <td style="padding:7px 10px;color:#666">{row['Series']}</td>
                <td style="padding:7px 10px;text-align:right">€{row['My Avg Buy Price']:.2f}</td>
                <td style="padding:7px 10px;text-align:right">€{row['Market Median Price']:.2f}</td>
                <td style="padding:7px 10px;text-align:right;font-weight:bold;color:{color}">{pct:+.1f}%</td>
                <td style="padding:7px 10px;text-align:right;font-weight:bold;color:{color}">€{profit:+.2f}</td>
                <td style="padding:7px 10px;text-align:right;color:#666">{int(row['Number Sold'])}</td>
            </tr>""")
    return '\n'.join(rows)


def _section(df, title, header_color, bg_color):
    if df.empty:
        return ''
    thead = f"""
        <thead>
            <tr style="background:{header_color};color:white">
                <th style="padding:8px 10px;text-align:left">Set #</th>
                <th style="padding:8px 10px;text-align:left">Name</th>
                <th style="padding:8px 10px;text-align:left">Series</th>
                <th style="padding:8px 10px;text-align:right">Buy Price</th>
                <th style="padding:8px 10px;text-align:right">Market Median</th>
                <th style="padding:8px 10px;text-align:right">Profit %</th>
                <th style="padding:8px 10px;text-align:right">Profit</th>
                <th style="padding:8px 10px;text-align:right">Recent Sales</th>
            </tr>
        </thead>"""
    return f"""
    <h2 style="color:{header_color};margin-top:32px;margin-bottom:8px">
        {title} &nbsp;<span style="font-size:14px;font-weight:normal;color:#666">({len(df)} sets)</span>
    </h2>
    <table style="border-collapse:collapse;width:100%;font-size:13px;background:{bg_color}">
        {thead}
        <tbody>{_table_rows(df)}</tbody>
    </table>"""


def generate_html(df, csv_path):
    today = datetime.now().strftime('%Y-%m-%d')

    sell_now  = df[df['Recommendation'] == 'Sell Now']
    consider  = df[df['Recommendation'] == 'Consider Selling']
    hold      = df[df['Recommendation'] == 'Hold']
    not_worth = df[df['Recommendation'] == 'Not Worth Selling']

    actionable_profit = (
        sell_now['Potential Profit (Median)'].sum() +
        consider['Potential Profit (Median)'].sum()
    )

    sections = (
        _section(sell_now,  'Sell Now (Profit >= 20%, Recent Sales >= 5)',  '#27ae60', '#f6fff8') +
        _section(consider,  'Consider Selling (Profit 10-20%)',            '#e67e22', '#fffbf2') +
        _section(hold,      'Hold (Profit 0-10%)',                         '#2980b9', '#f4f9ff') +
        _section(not_worth, 'Not Worth Selling (Negative Profit)',         '#c0392b', '#fff5f5')
    )

    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family:Arial,sans-serif;max-width:960px;margin:0 auto;padding:24px;color:#333">

<h1 style="color:#2c3e50;border-bottom:3px solid #c0392b;padding-bottom:10px;margin-bottom:4px">
    LEGO Price Analysis Report
</h1>
<p style="color:#888;margin-top:4px">
    Date: {today} &nbsp;|&nbsp; Source: eBay Deutschland &mdash; last 30 days of sold listings
</p>

<table style="border-collapse:collapse;width:100%;margin:20px 0;text-align:center">
    <tr>
        <td style="background:#2c3e50;color:white;padding:16px;border-radius:6px 0 0 6px">
            <div style="font-size:32px;font-weight:bold">{len(df)}</div>
            <div style="font-size:12px;margin-top:4px">Sets Analyzed</div>
        </td>
        <td style="width:4px;background:white"></td>
        <td style="background:#27ae60;color:white;padding:16px">
            <div style="font-size:32px;font-weight:bold">{len(sell_now)}</div>
            <div style="font-size:12px;margin-top:4px">Sell Now</div>
        </td>
        <td style="width:4px;background:white"></td>
        <td style="background:#e67e22;color:white;padding:16px">
            <div style="font-size:32px;font-weight:bold">{len(consider)}</div>
            <div style="font-size:12px;margin-top:4px">Consider Selling</div>
        </td>
        <td style="width:4px;background:white"></td>
        <td style="background:#c0392b;color:white;padding:16px;border-radius:0 6px 6px 0">
            <div style="font-size:32px;font-weight:bold">€{actionable_profit:.0f}</div>
            <div style="font-size:12px;margin-top:4px">Est. Total Profit</div>
        </td>
    </tr>
</table>

<div style="background:#eaf4fb;padding:12px 16px;border-left:4px solid #2980b9;font-size:13px;margin-bottom:8px">
    <strong>Note:</strong> Profit = Market Median Price &minus; Median Shipping &minus; Buy Price.
    eBay fees (~13%) are not yet deducted; estimated net profit after fees: <em>Profit &times; 0.87</em>.
    "Sell Now" criteria: median profit &ge; 20% and &ge; 5 recent sales.
</div>

{sections}

<p style="margin-top:32px;color:#aaa;font-size:12px">
    Full data attached: {os.path.basename(csv_path)}
</p>
</body>
</html>"""


def send_email(config, html_body, csv_path):
    sender = config['email']['sender']
    recipients = config['email']['recipients']
    app_password = config['email']['app_password']
    today = datetime.now().strftime('%Y-%m-%d')

    msg = MIMEMultipart('mixed')
    msg['Subject'] = f'LEGO Price Analysis Report {today}'
    msg['From'] = sender
    msg['To'] = ', '.join(recipients)

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    with open(csv_path, 'rb') as f:
        attachment = MIMEBase('application', 'octet-stream')
        attachment.set_payload(f.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        'Content-Disposition',
        f'attachment; filename="{os.path.basename(csv_path)}"'
    )
    msg.attach(attachment)

    context = ssl.create_default_context()
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as smtp:
        smtp.login(sender, app_password)
        smtp.sendmail(sender, recipients, msg.as_string())

    print(f"Email sent to: {', '.join(recipients)}")


def main():
    print("Loading config...")
    config = load_config()

    print("Finding latest price comparison data...")
    csv_path = find_latest_comparison_csv()
    print(f"Using: {os.path.basename(csv_path)}")

    df = pd.read_csv(csv_path)
    df = add_recommendations(df)

    sell_now = df[df['Recommendation'] == 'Sell Now']
    print(f"\nAnalysis summary:")
    print(f"  Total sets:       {len(df)}")
    print(f"  Sell now:         {len(sell_now)}")
    print(f"  Consider selling: {len(df[df['Recommendation']=='Consider Selling'])}")
    print(f"  Hold:             {len(df[df['Recommendation']=='Hold'])}")
    print(f"  Not worth:        {len(df[df['Recommendation']=='Not Worth Selling'])}")
    if not sell_now.empty:
        print(f"\n  Top picks to sell:")
        for _, row in sell_now.head(5).iterrows():
            print(f"    {row['LEGO Set Number']} {row['Set Name']}: +{row['Median Price Diff %']:.1f}% (€{row['Potential Profit (Median)']:+.2f})")

    print("\nGenerating HTML report...")
    html_body = generate_html(df, csv_path)

    print("Sending email...")
    send_email(config, html_body, csv_path)
    print("Done!")


if __name__ == '__main__':
    main()
