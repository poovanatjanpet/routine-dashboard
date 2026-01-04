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
        "<h3>📝 Daily Routine</h3>"
        "<form method='post' action='/save'>"
        f"วันที่:<br><input type='date' name='day' value='{today}'><br><br>"
        "เวลา:<br><input type='time' name='time'><br><br>"
        "ลำดับ:<br><input type='number' name='seq' value='1'><br><br>"
        "Routine:<br><input type='text' name='routine'><br><br>"
        "Status:<br>"
        "<select name='status'>"
        "<option>Planned</option>"
        "<option>Done</option>"
        "<option>Miss</option>"
        "</select><br><br>"
        "Note:<br><textarea name='note'></textarea><br><br>"
        "<button type='submit'>Save</button>"
        "</form>"
        "<br><a href='/dashboard'>⬅ Dashboard</a>"
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
def dashboard():
    conn = sqlite3.connect(DB)

    total = conn.execute("SELECT COUNT(*) FROM routines").fetchone()[0]
    done = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Done'").fetchone()[0]
    miss = conn.execute("SELECT COUNT(*) FROM routines WHERE status='Miss'").fetchone()[0]
    percent = int(done / total * 100) if total else 0

    rows = conn.execute(
        "SELECT day, SUM(status='Done'), SUM(status='Miss') "
        "FROM routines GROUP BY day ORDER BY day DESC LIMIT 14"
    ).fetchall()

    conn.close()

    days = [r[0] for r in rows]
    done_data = [r[1] for r in rows]
    miss_data = [r[2] for r in rows]

    html = (
        "<html><head>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
        "</head><body style='font-family:Arial;background:#f4f6fa;padding:12px'>"
        "<h2>📊 Dashboard</h2>"
        f"<p><b>Overall:</b> {percent}% | Total {total} | Done {done} | Miss {miss}</p>"
        "<canvas id='chart'></canvas><br><br>"
        "<h4>📅 เลือกวันย้อนหลัง</h4>"
        "<input type='date' onchange=\"if(this.value)location='/detail/'+this.value\"><br><br>"
        "<h4>📜 History</h4>"
        "<table border='1' cellpadding='6'>"
        "<tr><th>Day</th><th>Done</th><th>Miss</th><th>Detail</th></tr>"
    )

    for d, dn, ms in rows:
        html += (
            f"<tr><td>{d}</td><td>{dn}</td><td>{ms}</td>"
            f"<td><a href='/detail/{d}'>🔍</a></td></tr>"
        )

    html += (
        "</table><br>"
        "<a href='/daily'>➕ Add Routine</a>"
        "<script>"
        "new Chart(document.getElementById('chart'), {"
        "type:'bar',"
        "data:{labels:" + str(days[::-1]) + ",datasets:["
        "{label:'Done',data:" + str(done_data[::-1]) + ",backgroundColor:'green'},"
        "{label:'Miss',data:" + str(miss_data[::-1]) + ",backgroundColor:'red'}]},"
        "options:{onClick:(e,els)=>{"
        "if(els.length>0){"
        "let i=els[0].index;"
        "location='/detail/'+" + str(days[::-1]) + "[i];}}}});"
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
        "SELECT id,time,seq,routine,status,note FROM routines "
        "WHERE day=? ORDER BY seq,time",
        (day,)
    ).fetchall()
    conn.close()

    html = f"<h3>📅 {day}</h3><table border='1' cellpadding='6'>"
    html += "<tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th><th>Action</th></tr>"
    for rid,t,seq,r,s,n in rows:
        html += (
            f"<tr><td>{seq}</td><td>{t}</td><td>{r}</td><td>{s}</td>"
            f"<td><a href='/edit/{rid}'>✏️</a></td></tr>"
        )
    html += "</table><br><a href='/dashboard'>⬅ Back</a>"
    return html

# =====================
# EDIT
# =====================
@app.get("/edit/{rid}", response_class=HTMLResponse)
def edit(rid: int):
    conn = sqlite3.connect(DB)
    d,t,sq,r,st,n = conn.execute(
        "SELECT day,time,seq,routine,status,note FROM routines WHERE id=?",
        (rid,)
    ).fetchone()
    conn.close()

    return (
        "<h3>✏️ Edit Routine</h3>"
        "<form method='post'>"
        f"วันที่:<br><input type='date' name='day' value='{d}'><br><br>"
        f"เวลา:<br><input type='time' name='time' value='{t}'><br><br>"
        f"ลำดับ:<br><input type='number' name='seq' value='{sq}'><br><br>"
        f"Routine:<br><input type='text' name='routine' value='{r}'><br><br>"
        "Status:<br>"
        "<select name='status'>"
        f"<option {'selected' if st=='Planned' else ''}>Planned</option>"
        f"<option {'selected' if st=='Done' else ''}>Done</option>"
        f"<option {'selected' if st=='Miss' else ''}>Miss</option>"
        "</select><br><br>"
        f"Note:<br><textarea name='note'>{n}</textarea><br><br>"
        "<button>Save</button>"
        "</form>"
    )

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
        (day,time,seq,routine,status,note,rid)
    )
    conn.commit()
    conn.close()
    return RedirectResponse("/detail/" + day, status_code=303)
