from fastapi import FastAPI, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
import sqlite3
from datetime import date

app = FastAPI()
DB = "routine.db"

# =========================
# ROOT (กัน 404)
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
# DAILY ROUTINE
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

            กิจวัตร:<br>
            <input type="text" name="routine" required><br><br>

            สถานะ:<br>
            <select name="status">
                <option value="Planned">Planned</option>
                <option value="Done">Done</option>
                <option value="Miss">Miss</option>
            </select><br><br>

            หมายเหตุ:<br>
            <textarea name="note"></textarea><br><br>

            <button type="submit"
                onclick="this.disabled=true; this.innerText='Saving...'; this.form.submit();">
                Save
            </button>
        </form>

        <br>
        <a href="/dashboard">📊 Dashboard</a>
    </body>
    </html>
    """

# =========================
# SAVE (POST)
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
    return RedirectResponse(url="/daily", status_code=303)

# =========================
# SAVE (GET) กัน Not Found
# =========================
@app.get("/save")
def save_get():
    return RedirectResponse("/daily")

# =========================
# DELETE ROUTINE
# =========================
@app.post("/delete/{rid}")
def delete_routine(rid: int):
    conn = sqlite3.connect(DB)
    conn.execute("DELETE FROM routines WHERE id=?", (rid,))
    conn.commit()
    conn.close()
    return RedirectResponse("/dashboard", status_code=303)

# =========================
# DASHBOARD + FILTER
# =========================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    year: str = Query(""),
    month: str = Query("")
):
    conn = sqlite3.connect(DB)

    where = ""
    params = []

    if year and month:
        where = "WHERE strftime('%Y', day)=? AND strftime('%m', day)=?"
        params = [year, month]
    elif year:
        where = "WHERE strftime('%Y', day)=?"
        params = [year]

    total = conn.execute(
        f"SELECT COUNT(*) FROM routines {where}", params
    ).fetchone()[0]

    done = conn.execute(
        f"SELECT COUNT(*) FROM routines {where} {'AND' if where else 'WHERE'} status='Done'",
        params
    ).fetchone()[0]

    percent = int(done / total * 100) if total else 0

    conn.close()

    return f"""
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family:Arial;background:#f4f6fa;padding:12px }}
            .card {{ background:white;padding:12px;border-radius:10px;margin-bottom:8px }}
            .kpi {{ font-size:22px;color:#1f4ed8;font-weight:bold }}
            a {{ color:#1f4ed8;font-weight:bold;text-decoration:none }}
        </style>
    </head>
    <body>

    <h3>📊 Dashboard</h3>

    <div class="card">
        <b>Overall:</b> <span class="kpi">{percent}%</span><br>
        Total: {total} | Done: {done}
    </div>

    <div class="card">
        <a href="/daily">➕ Add Routine</a>
    </div>

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
        WHERE DATE(day)=DATE(?)
        ORDER BY seq, time
    """,(day,)).fetchall()
    conn.close()

    html=f"<h3>📅 {day}</h3><table border=1 cellpadding=6>"
    html+="<tr><th>ลำดับ</th><th>เวลา</th><th>Routine</th><th>Status</th><th>Note</th><th>🗑</th></tr>"
    for rid,seq,t,r,s,n in rows:
        col="green" if s=="Done" else "red" if s=="Miss" else "gray"
        html+=f"""
        <tr>
            <td>{seq}</td>
            <td>{t or ""}</td>
            <td>{r}</td>
            <td style='color:{col}'>{s}</td>
            <td>{n or ""}</td>
            <td>
                <form method="post" action="/delete/{rid}"
                      onsubmit="return confirm('ลบรายการนี้ใช่ไหม?');">
                    <button type="submit">ลบ</button>
                </form>
            </td>
        </tr>
        """
    html+="</table><br><a href='/dashboard'>⬅ Back</a>"
    return html
