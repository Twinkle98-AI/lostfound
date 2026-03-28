# 🔍 Lost & Found App

A Streamlit app where users can post lost/found items, contact owners, get notified, and chat.

---

## 📁 Project Structure

```
lost_found_app/
├── app.py           ← Main Streamlit UI (all pages + routing)
├── backend.py       ← SQLite DB + all helper functions
├── requirements.txt
├── Dockerfile
├── .env.example     ← Copy to .env and fill in values
└── .gitignore
```

---

## 🚀 How to Run Locally

### 1. Clone / unzip the project

```bash
cd lost_found_app
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
# Edit .env if you want to change Cloudinary credentials or DB path
```

### 5. Run the app

```bash
streamlit run app.py
```

Open your browser at **http://localhost:8501**

---

## 🐳 Run with Docker

```bash
# Build
docker build -t lost-found-app .

# Run (mounts .env and persists the SQLite DB)
docker run -p 8501:8501 \
  --env-file .env \
  -v $(pwd)/lost_found.db:/app/lost_found.db \
  lost-found-app
```

Open **http://localhost:8501**

---

## ✅ Features Implemented

| Step | Feature |
|------|---------|
| Step 1 | Browse page shows all items with **Contact Owner** and **I Found This** buttons |
| Step 2 | Filter by Lost / Found + keyword search |
| Step 3 | Notification panel in sidebar with unread badge count |
| Step 4 | Full item details page with owner actions (resolve / delete) |
| Step 5 | All routing connected — notifications link directly to item detail |

### User Flow
- **User A** posts a Lost item → visible in Browse
- **User B** clicks "💬 Contact Owner" or "🙋 I Found This"
- **User A** gets a notification with a link to the item
- Both can chat in the Messages page

---

## 🛠️ Notes

- Database: SQLite (`lost_found.db`) — auto-created on first run
- Image uploads: Cloudinary (credentials in `.env`)
- No email integration — notifications are in-app only
