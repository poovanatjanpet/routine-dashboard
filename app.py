from fastapi import FastAPI, Form, Query
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
# DB INIT
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
# DAILY
# =========================
@app.get("/daily", response_class=HTMLResponse)
def daily():
    return """
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Daily Routine</title>
    </head>
    <body style="font-family:Arial;padding:15px">
      <h3>📝 Daily Routine</h3>

      <form method="post" action="/save">
        วันที่:<br>
        <input type="date" name="day" required><br><br>

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
    </body>
    </html>
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
        INSERT INTO routines (day, time, seq, routine, status, note)
        VALUES (?,?,?,?,?,?)
    """, (str(day), time, seq, routine, status, note))
    conn.commit()
    conn.close()
    return RedirectResponse("/daily", status_code=303)

@app.get("/save")
def save_get():
    return RedirectResponse("/daily")

# =========================
# DELETE
# =========================
@app.post("/delete/{rid}")
def delete(rid: int):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM routines WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", status_code=303)

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

    daily = conn.execute("""
        SELECT day,
               SUM(status='Done'),
               SUM(status='Miss')
        FROM routines
        GROUP BY day
        ORDER BY day
    """).fetchall()

    conn.close()

    labels = [d[0] for d in daily]
    done_data = [d[1] for d in daily]
    miss_data = [d[2] for d in daily]

    return f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
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

    <h3>📊 Dashboard</h3>

    <div class="card">
      <b>Overall Discipline</b>
      <div class="gauge"><span>{percent}%</span></div>
      <div style="text-align:center">
        Total: {total} | Done: {done} | Miss: {miss}
      </div>
    </div>

    <div class="card">
      <b>📈 Daily Performance</b>
      <canvas id="dailyChart"></canvas>
    </div>

    <div class="card">
      <a href="/daily">➕ Add Routine</a>
    </div>

    <script>
    new Chart(document.getElementById("dailyChart"), {{
      type: 'bar',
      data: {{
        labels: {labels},
        datasets: [
          {{
            label: 'Done',
            data: {done_data},
            backgroundColor: '#16a34a'
          }},
          {{
            label: 'Miss',
            data: {miss_data},
            backgroundColor: '#dc2626'
          }}
        ]
      }},
      options: {{
        responsive:true,
        plugins: {{ legend: {{ position:'bottom' }} }}
      }}
    }});
    </script>

    </body>
    </html>
    """

# =========================
# DETAIL
# =========================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute("""
        SELECT id, seq, time, routine, status, note
        FROM routines
        WHERE day=?
        ORDER BY seq,time
    """,(day,)).fetchall()
    conn.close()

    html=f"<h3>{day}</h3><table border=1 cellpadding=6>"
    html+="<tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th><th>Note</th><th>🗑</th></tr>"
    for rid,seq,t,r,s,n in rows:
        col="green" if s=="Done" else "red" if s=="Miss" else "gray"
        html+=f"""
        <tr>
          <td>{seq}</td><td>{t or ""}</td><td>{r}</td>
          <td style='color:{col}'>{s}</td><td>{n or ""}</td>
          <td>
            <form method="post" action="/delete/{rid}"
              onsubmit="return confirm('Delete?');">
              <button>ลบ</button>
            </form>
          </td>
        </tr>
        """
    html+="</table><br><a href='/dashboard'>⬅ Back</a>"
    return html
