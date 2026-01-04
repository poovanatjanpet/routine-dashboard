from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import date

app = FastAPI()
DB = "routine.db"

# =====================
# INIT DATABASE
# =====================
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

# =====================
# ROOT
# =====================
@app.get("/")
def root():
    return RedirectResponse("/dashboard")

# =====================
# DAILY ADD
# =====================
@app.get("/daily", response_class=HTMLResponse)
def daily():
    today = date.today()
    return f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>📝 Daily Routine</h3>
    <form method="post" action="/save">
      Date:<br><input type="date" name="day" value="{today}" required><br><br>
      Time:<br><input type="time" name="time"><br><br>
      Seq:<br><input type="number" name="seq" value="1"><br><br>
      Routine:<br><input type="text" name="routine" required><br><br>
      Status:<br>
      <select name="status">
        <option>Planned</option>
        <option>Done</option>
        <option>Miss</option>
      </select><br><br>
      Note:<br><textarea name="note"></textarea><br><br>
      <button type="submit">Save</button>
    </form>
    <br><a href="/dashboard">⬅ Dashboard</a>
    </body></html>
    """

# =====================
# SAVE
# =====================
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
    conn.execute(
        "INSERT INTO routines (day,time,seq,routine,status,note) VALUES (?,?,?,?,?,?)",
        (str(day), time, seq, routine, status, note)
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", status_code=303)

# =====================
# DASHBOARD
# =====================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(month: str = None, year: str = None):
    conn = sqlite3.connect(DB)

    # ----- safe filter -----
    where = ""
    params = []
    try:
        if month and year:
            m = int(month)
            y = int(year)
            where = "WHERE strftime('%m', day)=? AND strftime('%Y', day)=?"
            params = [f"{m:02d}", str(y)]
    except ValueError:
        pass

    total = conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Done'").fetchone()[0]
    miss = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Miss'").fetchone()[0]
    percent = int(done / total * 100) if total else 0

    rows = conn.execute(
        "SELECT day, SUM(status='Done'), SUM(status='Miss') "
        "FROM routines " + where +
        " GROUP BY day ORDER BY day DESC LIMIT 7",
        params
    ).fetchall()

    conn.close()

    days = [r[0] for r in rows][::-1]
    done_data = [r[1] for r in rows][::-1]
    miss_data = [r[2] for r in rows][::-1]

    html = f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
      <style>
        body {{ font-family:Segoe UI,Arial;background:#f4f6fb;padding:14px }}
        .card {{ background:#fff;border-radius:10px;padding:14px;margin-bottom:14px;
                 box-shadow:0 2px 6px rgba(0,0,0,.05) }}
        table {{ width:100%;border-collapse:collapse }}
        th {{ background:#eef2ff;padding:8px }}
        td {{ padding:8px;border-bottom:1px solid #e5e7eb;text-align:center }}
      </style>
    </head>
    <body>

    <h2>📊 Dashboard</h2>

    <div class="card">
      <b>Overall Discipline</b><br>
      <span style="font-size:24px;color:#2563eb;font-weight:bold">{percent}%</span><br>
      Total {total} | Done {done} | Miss {miss}
    </div>

    <div class="card">
      <form method="get">
        Month <input name="month" style="width:60px">
        Year <input name="year" style="width:80px">
        <button>Apply</button>
      </form>
      <br>
      <a href="/overview">📊 View Year Overview</a>
    </div>

    <div class="card">
      <canvas id="chart" style="max-height:220px"></canvas>
    </div>

    <div class="card">
      <b>📜 History</b>
      <table>
        <tr><th>Day</th><th>Done</th><th>Miss</th><th>Detail</th></tr>
        {''.join(
            f"<tr><td>{d}</td><td>{dn}</td><td>{ms}</td>"
            f"<td><a href='/detail/{d}'>🔍</a></td></tr>"
            for d, dn, ms in rows
        )}
      </table>
    </div>

    <div class="card">
      <a href="/daily">➕ Add Routine</a>
    </div>

    <script>
    new Chart(document.getElementById("chart"), {{
      type: "bar",
      data: {{
        labels: {days},
        datasets: [
          {{ label: "Done", data: {done_data}, backgroundColor: "#16a34a" }},
          {{ label: "Miss", data: {miss_data}, backgroundColor: "#dc2626" }}
        ]
      }},
      options: {{
        onClick:(e,els)=>{{
          if(els.length>0){{
            let i = els[0].index;
            location = "/detail/" + {days}[i];
          }}
        }}
      }}
    }});
    </script>

    </body></html>
    """
    return html

# =====================
# YEAR OVERVIEW
# =====================
@app.get("/overview", response_class=HTMLResponse)
def overview():
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT strftime('%m', day), SUM(status='Done'), SUM(status='Miss') "
        "FROM routines GROUP BY strftime('%m', day) ORDER BY strftime('%m', day)"
    ).fetchall()
    conn.close()

    months = [r[0] for r in rows]
    done = [r[1] for r in rows]
    miss = [r[2] for r in rows]

    return f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>📊 Year Overview</h3>
    <canvas id="y"></canvas>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
    new Chart(document.getElementById("y"), {{
      type:"bar",
      data:{{ labels:{months},
              datasets:[
                {{label:"Done",data:{done},backgroundColor:"green"}},
                {{label:"Miss",data:{miss},backgroundColor:"red"}}
              ]}}
    }});
    </script>
    <br><a href="/dashboard">⬅ Dashboard</a>
    </body></html>
    """

# =====================
# DETAIL (VIEW / EDIT / DELETE)
# =====================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id,time,seq,routine,status FROM routines "
        "WHERE day=? ORDER BY seq,time",
        (day,)
    ).fetchall()
    conn.close()

    html = f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>📅 {day}</h3>
    <table border="1" cellpadding="6" style="border-collapse:collapse;width:100%">
    <tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th><th>Action</th></tr>
    """

    for rid, t, seq, r, s in rows:
        html += f"""
        <tr>
          <td>{seq}</td>
          <td>{t or ""}</td>
          <td>{r}</td>
          <td>{s}</td>
          <td>
            <a href="/edit/{rid}">✏️</a>
            <form method="post" action="/delete/{rid}" style="display:inline">
              <button onclick="return confirm('Delete this routine?')">🗑</button>
            </form>
          </td>
        </tr>
        """

    html += "</table><br><a href='/dashboard'>⬅ Dashboard</a></body></html>"
    return html

# =====================
# EDIT
# =====================
@app.get("/edit/{rid}", response_class=HTMLResponse)
def edit(rid: int):
    conn = sqlite3.connect(DB)
    d, t, seq, r, s, n = conn.execute(
        "SELECT day,time,seq,routine,status,note FROM routines WHERE id=?",
        (rid,)
    ).fetchone()
    conn.close()

    return f"""
    <html><body style="font-family:Segoe UI,Arial;padding:14px">
    <h3>✏️ Edit Routine</h3>
    <form method="post">
      Date:<br><input type="date" name="day" value="{d}"><br><br>
      Time:<br><input type="time" name="time" value="{t or ""}"><br><br>
      Seq:<br><input type="number" name="seq" value="{seq}"><br><br>
      Routine:<br><input type="text" name="routine" value="{r}"><br><br>
      Status:<br>
      <select name="status">
        <option {"selected" if s=="Planned" else ""}>Planned</option>
        <option {"selected" if s=="Done" else ""}>Done</option>
        <option {"selected" if s=="Miss" else ""}>Miss</option>
      </select><br><br>
      Note:<br><textarea name="note">{n or ""}</textarea><br><br>
      <button>Save</button>
    </form>
    </body></html>
    """

@app.post("/edit/{rid}")
def edit_save(
    rid: int,
    day: str = Form(...),
    time: str = Form(""),
    seq: int = Form(1),
    routine: str = Form(...),
    status: str = Form(...),
    note: str = Form("")
):
    conn = sqlite3.connect(DB)
    conn.execute(
        "UPDATE routines SET day=?,time=?,seq=?,routine=?,status=?,note=? WHERE id=?",
        (day, time, seq, routine, status, note, rid)
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/detail/" + day, status_code=303)

# =====================
# DELETE
# =====================
@app.post("/delete/{rid}")
def delete(rid: int):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM routines WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", status_code=303)
