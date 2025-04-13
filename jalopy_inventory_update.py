import requests
from bs4 import BeautifulSoup
import pandas as pd
import hashlib
import random
import time
from datetime import datetime
from collections import defaultdict
import os
import yagmail
from dotenv import load_dotenv

# ---------- CONFIGURATION ----------
BASE_URL = "https://inventory.pickapartjalopyjungle.com"
CSV_OLD = "jalopy_inventory.csv"
CSV_NEW = "jalopy_inventory.csv"
CSV_NEW_ONLY = "jalopy_inventory_new_vehicles.csv"
TODAY = datetime.today().strftime('%Y-%m-%d')

YARDS = {
    "BOISE": "1020",
    "CALDWELL": "1021",
    "GARDEN CITY": "1119",
    "NAMPA": "1022",
    "TWIN FALLS": "1099"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/x-www-form-urlencoded"
}

# ---------- HELPERS ----------
def generate_fingerprint(vehicle):
    key = f"{vehicle['yard_id']}|{vehicle['make']}|{vehicle['model']}|{vehicle['year']}|{vehicle['row']}"
    return hashlib.sha256(key.encode()).hexdigest()

# ---------- LOAD PREVIOUS SNAPSHOT ----------
try:
    prev_df = pd.read_csv(CSV_OLD)
except FileNotFoundError:
    print(f"File '{CSV_OLD}' not found. Ensure it is the file directory")
    exit(1)

prev_df['fingerprint'] = prev_df.apply(generate_fingerprint, axis=1)
prev_df = prev_df.drop_duplicates(subset='fingerprint', keep='first')
prev_fp_map = prev_df.set_index('fingerprint').to_dict('index')

# ---------- SCRAPE CURRENT INVENTORY ----------
all_vehicles = []
potential_new = []

for yard_name, yard_id in YARDS.items():
    try:
        make_resp = requests.post(f"{BASE_URL}/Home/GetMakes", data={"yardId": yard_id}, headers=HEADERS)
        makes = make_resp.json()
        # time.sleep(random.uniform(0.4, 0.8))
        time.sleep(0.02)

        for make_entry in makes:
            make = make_entry['makeName']
            model_resp = requests.post(f"{BASE_URL}/Home/GetModels", data={"yardId": yard_id, "makeName": make}, headers=HEADERS)
            models = model_resp.json()
            # time.sleep(random.uniform(0.4, 0.8))
            time.sleep(0.02)

            for model_entry in models:
                model = model_entry['model']
                form_data = {"YardId": yard_id, "VehicleMake": make, "VehicleModel": model}
                inv_resp = requests.post(BASE_URL + "/", data=form_data, headers=HEADERS)
                soup = BeautifulSoup(inv_resp.text, 'html.parser')
                rows = soup.select("table.table tr")[1:]

                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) == 4:
                        vehicle = {
                            "yard": yard_name,
                            "yard_id": yard_id,
                            "make": make,
                            "model": model,
                            "year": tds[0].text.strip(),
                            "row": tds[3].text.strip()
                        }
                        vehicle["fingerprint"] = generate_fingerprint(vehicle)

                        if vehicle["fingerprint"] not in prev_fp_map:
                            vehicle["date_added"] = TODAY
                            potential_new.append(vehicle)
                        else:
                            vehicle["date_added"] = prev_fp_map[vehicle["fingerprint"]]["date_added"]

                        all_vehicles.append(vehicle)
                # time.sleep(random.uniform(1.0, 2.0))
                time.sleep(0.02)
    except Exception as e:
        print(f"Error in yard {yard_name}: {e}")
    time.sleep(random.uniform(3.0, 5.0))

# ---------- ROW REPLACEMENT HEURISTIC ----------
row_grouped = defaultdict(list)
for v in potential_new:
    row_grouped[(v["yard"], v["row"])].append(v)

rows_to_replace = {key for key, vehicles in row_grouped.items() if len(vehicles) >= 3}

# ---------- FINAL MERGE ----------
updated_vehicles = []
new_vehicles_final = []

for v in all_vehicles:
    fp = v["fingerprint"]
    row_key = (v["yard"], v["row"])

    if fp not in prev_fp_map:
        new_vehicles_final.append(v)
        updated_vehicles.append(v)
    elif row_key in rows_to_replace:
        v["date_added"] = TODAY
        new_vehicles_final.append(v)
        updated_vehicles.append(v)
    else:
        updated_vehicles.append(v)

# ---------- EXPORT ----------
df_full = pd.DataFrame(updated_vehicles)
df_new = pd.DataFrame(new_vehicles_final)

# ---------- ENSURE HISTORY FOLDER EXISTS ----------
full_inventory_history = "full_inventory_history"
new_inventory_history = "new_inventory_history"
os.makedirs(full_inventory_history, exist_ok=True)
os.makedirs(new_inventory_history, exist_ok=True)

# ---------- EXPORT: Latest Versions ----------
df_full.to_csv("jalopy_inventory.csv", index=False)
df_new.to_csv("jalopy_new_vehicles.csv", index=False)

# ---------- EXPORT: Historical Archives ----------
history_full_path = os.path.join(full_inventory_history, f"jalopy_full_inventory_{TODAY}.csv")
history_new_path = os.path.join(new_inventory_history, f"jalopy_new_vehicles_{TODAY}.csv")

df_full.to_csv(history_full_path, index=False)
df_new.to_csv(history_new_path, index=False)

print(f"Full inventory: jalopy_inventory_updated.csv ({len(df_full)} vehicles)")
print(f"New vehicles only: jalopy_inventory_new_vehicles.csv ({len(df_new)} vehicles)")
print(f"Historical archives saved")

# Load environment variables from .env
load_dotenv()
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECIPIENT = os.environ["EMAIL_RECIPIENT"]

# Only send email if there are new vehicles
if not df_new.empty:
    # Reorder and rename columns for readability
    pretty_df = df_new[["yard", "row", "year", "make", "model", "date_added"]].copy()
    pretty_df.columns = ["Yard", "Row", "Year", "Make", "Model", "Date Added"]

    # Build Gmail-friendly HTML table using inline styles (compact)
    table_rows = ""
    for _, row in pretty_df.iterrows():
        table_rows += (
            f"<tr>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Yard']}</td>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Row']}</td>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Year']}</td>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Make']}</td>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Model']}</td>"
            f"<td style='border:1px solid #ddd; padding:6px;'>{row['Date Added']}</td>"
            f"</tr>"
        )

    html_table = (
        f"<table style='border-collapse:collapse; width:100%; font-family:Arial, sans-serif; font-size:14px;'>"
        f"<thead>"
        f"<tr style='background-color:#F05A28; color:white;'>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Yard</th>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Row</th>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Year</th>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Make</th>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Model</th>"
        f"<th style='border:1px solid #ddd; padding:8px;'>Date Added</th>"
        f"</tr>"
        f"</thead>"
        f"<tbody>{table_rows}</tbody>"
        f"</table>"
    )

    # Compose the email body with spacing & styling
    subject = f"🚗 {len(df_new)} New Vehicles Added - {TODAY}"
    body = (
        f"<p style='font-family: Arial, sans-serif; font-size: 15px;'>"
        f"Hello,<br><br>"
        f"<strong>{len(df_new)}</strong> new vehicle(s) were added to the Jalopy Jungle Inventory on "
        f"<strong>{TODAY}</strong>."
        f"</p>"
        f"<p style='font-family: Arial, sans-serif; font-size: 15px;'>Here is a detailed list:</p>"
        f"{html_table}"
        f"<p style='font-family: Arial, sans-serif; font-size: 15px;'>"
        f"Best regards,<br><strong>Jalopy Inventory Bot</strong></p>"
    )

    # Send email with HTML as primary content
    yag = yagmail.SMTP(EMAIL_SENDER, EMAIL_PASSWORD)
    yag.send(
        to=EMAIL_RECIPIENT,
        subject=subject,
        contents=[body]  # HTML first to make it preferred
    )

    print("Email sent successfully!")

else:
    print("No new vehicles — no email sent.")