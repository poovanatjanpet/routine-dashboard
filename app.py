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
        "<html><body style='font-family:Segoe UI,Arial;padding:14px'>"
        "<h3>📝 Daily Routine</h3>"
        "<form method='post' action='/save'>"
        f"Date:<br><input type='date' name='day' value='{today}'><br><br>"
        "Time:<br><input type='time' name='time'><br><br>"
        "Seq:<br><input type='number' name='seq' value='1'><br><br>"
        "Routine:<br><input type='text' name='routine' required><br><br>"
        "Status:<br>"
        "<select name='status'>"
        "<option>Planned</option><option>Done</option><option>Miss</option>"
        "</select><br><br>"
        "Note:<br><textarea name='note'></textarea><br><br>"
        "<button>Save</button>"
        "</form><br><a href='/dashboard'>⬅ Dashboard</a>"
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
def dashboard(month: str = None, year: str = None):
    conn = sqlite3.connect(DB)

    # ----- Safe filter -----
    where = ""
    params = []
    m = y = None
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

    html = (
        "<html><head>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        "body{font-family:Segoe UI,Arial;background:#f4f6fb;padding:14px}"
        ".card{background:#fff;border-radius:10px;padding:14px;margin-bottom:14px;"
        "box-shadow:0 2px 6px rgba(0,0,0,.05)}"
        "</style></head><body>"
        "<h2>📊 Dashboard</h2>"

        f"<div class='card'><b>Overall:</b> {percent}% | Total {total} | Done {done} | Miss {miss}</div>"

        "<div class='card'>"
        "<form method='get'>"
        "Month <input name='month' style='width:60px'> "
        "Year <input name='year' style='width:80px'> "
        "<button>Apply</button>"
        "</form>"
        "<br><a href='/overview'>📊 View Year Overview</a>"
        "</div>"

        "<div class='card'><canvas id='chart' style='max-height:220px'></canvas></div>"

        "<script>"
        "new Chart(document.getElementById('chart'),{"
        "type:'bar',"
        "data:{labels:" + str(days) + ",datasets:["
        "{label:'Done',data:" + str(done_data) + ",backgroundColor:'green'},"
        "{label:'Miss',data:" + str(miss_data) + ",backgroundColor:'red'}]},"
        "options:{onClick:(e,els)=>{"
        "if(els.length>0){let i=els[0].index;"
        "location='/detail/'+" + str(days) + "[i];}}}"
        "});</script>"

        "<a href='/daily'>➕ Add Routine</a>"
        "</body></html>"
    )
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

    return (
        "<html><head>"
        "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "</head><body style='font-family:Segoe UI,Arial;padding:14px'>"
        "<h3>📊 Year Overview</h3>"
        "<canvas id='y'></canvas>"
        "<script>"
        "new Chart(document.getElementById('y'),{"
        "type:'bar',"
        "data:{labels:" + str(months) + ",datasets:["
        "{label:'Done',data:" + str(done) + ",backgroundColor:'green'},"
        "{label:'Miss',data:" + str(miss) + ",backgroundColor:'red'}]}"
        "});</script>"
        "<br><a href='/dashboard'>⬅ Dashboard</a>"
        "</body></html>"
    )

# =====================
# DETAIL
# =====================
@app.get("/detail/{day}", response_class=HTMLResponse)
def detail(day: str):
    conn = sqlite3.connect(DB)
    rows = conn.execute(
        "SELECT time,seq,routine,status FROM routines WHERE day=? ORDER BY seq,time",
        (day,)
    ).fetchall()
    conn.close()

    html = f"<h3>{day}</h3><table border='1' cellpadding='6'>"
    html += "<tr><th>#</th><th>Time</th><th>Routine</th><th>Status</th></tr>"
    for t,seq,r,s in rows:
        html += f"<tr><td>{seq}</td><td>{t}</td><td>{r}</td><td>{s}</td></tr>"
    html += "</table><br><a href='/dashboard'>⬅ Dashboard</a>"
    return html
