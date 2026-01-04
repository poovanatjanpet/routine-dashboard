from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import date

app = FastAPI()
DB = "routine.db"

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return RedirectResponse("/dashboard")

# =========================
# INIT DB
# =========================
def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS routines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT,
            time TEXT,
            seq INTEGER,
            routine TEXT,
            status TEXT,
            note TEXT
        )
    """)
    conn.close()

init_db()

# =========================
# DAILY ADD
# =========================
@app.get("/daily", response_class=HTMLResponse)
def daily():
    today = date.today()
    return f"""
    <h3>📝 Daily Routine</h3>

    <form method="post" action="/save">
      วันที่:<br>
      <input type="date" name="day" value="{today}" required><br><br>

      เวลา:<br>
      <input type="time" name="time"><br><br>

      ลำดับ:<br>
      <input type="number" name="seq" value="1"><br><br>

      Routine:<br>
      <input type="text" name="routine" required><br><br>

      Status:<br>
      <select name="status">
        <option>Planned</option>
        <option>Done</option>
        <option>Miss</option>
      </select><br><br>

      Note:<br>
      <textarea name="note"></textarea><br><br>

      <button type="submit"
        onclick="this.disabled=true;this.innerText='Saving...';this.form.submit();">
        Save
      </button>
    </form>

    <br>
    <a href="/dashboard">⬅ Dashboard</a>
    """

# =========================
# SAVE
# =========================
@app.post("/save")
def save(
    day: date = Form(...),
    time: str = Form(""),
    seq: int = Form(1),
    routine: str = Form(...),
    status: str = Form(...),
    note: str = Form("")
):
    conn = sqlite3.connect(DB)
    conn.execute("""
        INSERT INTO routines (day,time,seq,routine,status,note)
        VALUES (?,?,?,?,?,?)
    """, (str(day), time, seq, routine, status, note))
    conn.commit()
    conn.close()
    return RedirectResponse("/daily", status_code=303)

@app.get("/save")
def save_get():
    return RedirectResponse("/daily")

# =========================
# DASHBOARD
# =========================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    conn = sqlite3.connect(DB)

    total = conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Done'").fetchone()[0]
    miss = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Miss'").fetchone()[0]
    percent = int(done / total * 100) if total else 0

    rows = conn.execute("""
        SELECT day,
               SUM(status='Done') AS done,
               SUM(status='Miss') AS miss
        FROM routines
        GROUP BY day
        ORDER BY day DESC
        LIMIT 14
    """).fetchall()

    conn.close()

    days = [r[0] for r in rows]
    done_data = [r[1] for r in rows]
    miss_data = [r[2] for r in rows]

    return f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body {{ font-family:Arial;background:#f4f6fa;padding:12px }}
        .card {{ background:white;padding:12px;border-radius:10px;margin-bottom:12px }}
        table {{ width:100%;border-collapse:collapse }}
        th,td {{ border:1px solid #ddd;padding:6px;text-align:center }}
        th {{ background:#eef2ff }}
        tr:hover {{ background:#f1f5f9 }}
