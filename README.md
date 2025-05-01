# 🚗 Jalopy Jungle Inventory Scraper

This Python-based utility automates the process of monitoring and reporting new vehicle arrivals at **Jalopy Jungle** salvage yards. By scraping the official inventory website, it identifies new vehicle listings, updates inventory records, archives historical data, and sends HTML-formatted email notifications to subscribed recipients.

## 📌 Features

- 🔍 **Web Scraping**: Retrieves vehicle inventory data across multiple Jalopy Jungle locations.
- 🆕 **Change Detection**: Identifies newly added vehicles using a fingerprinting heuristic.
- 🧠 **Row Heuristics**: Includes logic to catch row-level replacements for improved accuracy.
- 📂 **Data Storage**:
  - Maintains current full inventory in `jalopy_inventory.csv`.
  - Extracts and saves new vehicles in `jalopy_new_vehicles.csv`.
  - Archives daily snapshots in versioned folders.
- ✉️ **Automated Email Notifications**:
  - Sends a styled, tabular email containing new vehicle details.
  - Supports multiple recipients with BCC handling.
- 🔐 **Environment Configurations**:
  - Uses `.env` file or github secrets for credentials and recipient management.
  - Secure email transmission via `yagmail`.

## 🧰 Tech Stack

- `requests` and `BeautifulSoup` — For HTTP requests and HTML parsing.
- `pandas` — For structured data handling and CSV I/O.
- `hashlib` — For fingerprinting vehicle records.
- `yagmail` — For simplified email dispatch via Gmail.
- `dotenv` — For secure credential and recipient management.

## 🛠️ Usage Instructions

### 1. Setup Environment

Create a `.env` file in the project root with the following variables:

```env
EMAIL_SENDER=your_email@gmail.com
EMAIL_PASSWORD=your_password_or_app_password
EMAIL_RECIPIENTS=recipient1@example.com, recipient2@example.com
