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
    conn.execute(
        "CREATE TABLE IF NOT EXISTS routines ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "day TEXT,"
        "time TEXT,"
        "seq INTEGER,"
        "routine TEXT,"
        "status TEXT,"
        "note TEXT)"
    )
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
    return (
        "<html><head><meta name='viewport' content='width=device-width, initial-scale=1'></head>"
        "<body style='font-family:Segoe UI,Arial;padding:14px'>"
        "<h3>📝 Daily Routine</h3>"
        "<form method='post' action='/save'>"
        f"วันที่:<br><input type='date' name='day' value='{today}'><br><br>"
        "เวลา:<br><input type='time' name='time'><br><br>"
        "ลำดับ:<br><input type='number' name='seq' value='1'><br><br>"
        "Routine:<br><input type='text' name='routine' required><br><br>"
        "Status:<br>"
        "<select name='status'>"
        "<option>Planned</option>"
        "<option>Done</option>"
        "<option>Miss</option>"
        "</select><br><br>"
        "Note:<br><textarea name='note'></textarea><br><br>"
        "<button type='submit'>Save</button>"
        "</form><br>"
        "<a href='/dashboard'>⬅ Dashboard</a>"
        "</body></html>"
    )

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
def dashboard(month: int = None, year: int = None):
    conn = sqlite3.connect(DB)

    where = ""
    params = []
    if month and year:
        where = "WHERE strftime('%m', day)=? AND strftime('%Y', day)=?"
        params = [f"{month:02d}", str(year)]

    total = conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Done'").fetchone()[0]
    miss = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Miss'").fetchone()[0]
    percent = int(done / total * 100) if total else 0

    rows = conn.execute(
        "SELECT day, SUM(status='Done'), SUM(status='Miss') "
        "FROM routines "
        + where +
        " GROUP BY day ORDER BY day DESC LIMIT 7",
        params
    ).fetchall()

    conn.close()

    days = [r[0] for r in rows][::-1]
    done_data = [r[1] for r in rows][::-1]
    miss_data = [r[2] for r in rows][::-1]

    html = (
        "<html><head>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
        "<style>"
        "body{font-family:Segoe UI,Arial;background:#f4f6fb;padding:14px;margin:0}"
        ".card{background:#fff;border-radius:10px;padding:14px;margin-bottom:14px;"
        "box-shadow:0 2px 6px rgba(0,0,0,.05)}"
        "table{width:100%;border-collapse:collapse;font-size:14px}"
        "th{background:#eef2ff;padding:8px}"
        "td{padding:8px;border-bottom:1px solid #e5e7eb;text-align:center}"
        "</style></head><body>"
        "<h2>📊 Dashboard</h2>"

        "<div class='card'>"
        "<div style='color:#6b7280'>Overall Discipline</div>"
        f"<div style='font-size:24px;color:#2563eb;font-weight:bold'>{percent}%</div>"
        f"Total {total} | Done {done} | Miss {miss}"
        "</div>"

        "<div class='card'>"
        "<b>Filter</b><br><br>"
        "<form method='get'>"
        "Month <input type='number' name='month' min='1' max='12' style='width:60px'> "
        "Year <input type='number' name='year' value='2026' style='width:80px'> "
        "<button>Apply</button>"
        "</form></div>"

        "<div class='card'>"
        "<b>Daily Performance</b><br><br>"
        "<canvas id='chart' style='max-height:220px'></canvas>"
        "</div>"

        "<div class='card'>"
        "<b>📜 History</b>"
        "<table>"
        "<tr><th>Day</th><th>Done</th><th>Miss</th><th>Detail</th></tr>"
    )

    for d, dn, ms in rows:
        html += (
            f"<tr><td>{d}</td><td>{dn}</td><td>{ms}</td>"
            f"<td><a href='/detail/{d}'>🔍</a></td></tr>"
        )

    html += (
        "</table></div>"
        "<div class='card'><a href='/daily'>➕ Add Routine</a></div>"
        "<script>"
        "new Chart(document.getElementById('chart'),{"
        "type:'bar',"
        "data:{labels:" + str(days) + ",datasets:["
        "{label:'Done',data:" + str(done_data) + ",backgroundColor:'#16a34a'},"
        "{label:'Miss',data:" + str(miss_data) + ",backgroundColor:'#dc2626'}]},"
        "options:{responsive:true,maintainAspectRatio:false,"
        "plugins:{legend:{position:'bottom'}},"
        "onClick:(e,els)=>{"
        "if(els.length>0){"
        "let i=els[0].index;"
        "location='/detail/'+" + str(days) + "[i];}}}});"
        "</script></body></html>"
    )

    return html

# =====================
# DETAIL
# =====================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT id,time,seq,routine,status,note "
        "FROM routines WHERE day=? ORDER BY seq,time",
        (day,)
    ).fetchall()
    conn.close()

    html = (
        f"<html><body style='font-family:Segoe UI,Arial;padding:14px'>"
        f"<h3>📅 {day}</h3>"
        "<table border='1' cellpadding='6' style='border-collapse:collapse'>"
        "<tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th><th>Action</th></tr>"
    )

    for rid,t,seq,r,s,n in rows:
        html += (
            f"<tr><td>{seq}</td><td>{t}</td><td>{r}</td><td>{s}</td>"
            f"<td><a href='/edit/{rid}'>✏️</a></td></tr>"
        )

    html += "</table><br><a href='/dashboard'>⬅ Dashboard</a></body></html>"
    return html

