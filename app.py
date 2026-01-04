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
    return """
    <h3>📝 Daily Routine</h3>
    <form method="post" action="/save">
      วันที่:<br><input type="date" name="day" required><br><br>
      เวลา:<br><input type="time" name="time"><br><br>
      ลำดับ:<br><input type="number" name="seq" value="1"><br><br>
      Routine:<br><input type="text" name="routine" required><br><br>
      Status:<br>
      <select name="status">
        <option>Planned</option>
        <option>Done</option>
        <option>Miss</option>
      </select><br><br>
      Note:<br><textarea name="note"></textarea><br><br>
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

    days = conn.execute("""
        SELECT day,
               SUM(status='Done'),
               SUM(status='Miss')
        FROM routines
        GROUP BY day
        ORDER BY day DESC
        LIMIT 7
    """).fetchall()

    conn.close()

    labels = [d[0] for d in days][::-1]
    done_data = [d[1] for d in days][::-1]
    miss_data = [d[2] for d in days][::-1]

    return f"""
    <html>
    <head>
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body {{ font-family:Arial;background:#f4f6fa;padding:12px }}
        .card {{ background:white;padding:12px;border-radius:10px;margin-bottom:12px }}
        .gauge {{
          width:160px;height:160px;border-radius:50%;
          background:conic-gradient(#2563eb {percent}%,#e5e7eb {percent}%);
          display:flex;align-items:center;justify-content:center;margin:auto
        }}
        .gauge span {{
          background:white;width:110px;height:110px;border-radius:50%;
          display:flex;align-items:center;justify-content:center;
          font-size:26px;font-weight:bold;color:#2563eb
        }}
      </style>
    </head>
    <body>

    <h2>📊 Dashboard</h2>

    <div class="card">
      <b>Overall Discipline</b>
      <div class="gauge"><span>{percent}%</span></div>
      <div style="text-align:center">
        Total: {total} | Done: {done} | Miss: {miss}
      </div>
    </div>

    <div class="card">
      <b>📈 Last 7 Days</b>
      <canvas id="chart"></canvas>
    </div>

    <div class="card">
      <a href="/daily">➕ Add Routine</a>
    </div>

    <div class="card">
      <b>📅 History</b><br>
      {"".join([f"<a href='/detail/{d[0]}'>{d[0]}</a><br>" for d in days])}
    </div>

    <script>
    new Chart(document.getElementById("chart"), {{
      type: 'bar',
      data: {{
        labels: {labels},
        datasets: [
          {{ label: 'Done', data: {done_data}, backgroundColor: '#16a34a' }},
          {{ label: 'Miss', data: {miss_data}, backgroundColor: '#dc2626' }}
        ]
      }},
      options: {{ responsive:true }}
    }});
    </script>

    </body>
    </html>
    """

# =========================
# DETAIL (VIEW / EDIT / DELETE)
# =========================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT id, time, seq, routine, status, note
        FROM routines
        WHERE day=?
        ORDER BY seq,time
    """,(day,)).fetchall()
    conn.close()

    html = f"<h3>{day}</h3><table border=1 cellpadding=6>"
    html += "<tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th><th>Note</th><th>Action</th></tr>"
