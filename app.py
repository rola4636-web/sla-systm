import base64
import html as ihtml
import os
import random
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="نظام تتبع SLA | أمانة العاصمة المقدسة",
    page_icon="🕋",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------
# الإعدادات والقواعد (من الوثيقة)
# ---------------------------------------------------------------
TYPES = ["فنية", "صيانة", "إدارية", "بيانات", "صلاحيات وصول", "تشغيلية"]
PRIORITIES = ["منخفضة", "متوسطة", "عالية", "حرجة"]

# المدة بالساعات: [منخفضة, متوسطة, عالية, حرجة]
# فنية وصيانة وصلاحيات وبيانات من جدول الوثيقة، وإدارية وتشغيلية قيم افتراضية
BASE_HOURS = {
    "فنية": [72, 48, 24, 4],
    "صيانة": [120, 72, 24, 8],
    "صلاحيات وصول": [72, 48, 24, 4],
    "بيانات": [120, 72, 48, 24],
    "إدارية": [96, 72, 48, 8],
    "تشغيلية": [96, 48, 24, 6],
}
SLA_HOURS = {(t, p): BASE_HOURS[t][i] for t in TYPES for i, p in enumerate(PRIORITIES)}

# التصعيد: ساعات بعد تجاوز الموعد النهائي
ESC_HOURS = {"منخفضة": 72, "متوسطة": 48, "عالية": 24, "حرجة": 0}

DEPT_EMPLOYEES = {
    "تقنية المعلومات": ["أحمد العتيبي", "سارة الغامدي", "خالد الزهراني"],
    "الصيانة": ["محمد القرشي", "نورة السلمي", "فهد الحربي"],
    "الشؤون الإدارية": ["ريم الشهري", "عبدالله المالكي", "هند الدوسري"],
    "البيانات والتحليل": ["لمى العمري", "سلطان البقمي", "جود الحازمي"],
}
EMP_DEPT = {e: d for d, es in DEPT_EMPLOYEES.items() for e in es}
ALL_EMPLOYEES = list(EMP_DEPT)

TITLES = [
    "تحديث بيانات النظام", "إصلاح عطل", "مراجعة الصلاحيات", "إعداد تقرير",
    "فحص دوري", "معالجة طلب", "تجهيز بيئة العمل", "متابعة شكوى",
]
TASK_STATUSES = ["جديدة", "مسندة", "قيد التنفيذ", "مكتملة", "مغلقة"]
DONE_STATUSES = ["مكتملة", "مغلقة"]

COLORS = {
    "On Track": "#2e9e5b",
    "Deadline Near": "#e0a800",
    "Overdue": "#e04848",
    "Escalated": "#7b3fb0",
    "Within": "#1b6b3a",
    "Breached": "#d9480f",
}
LABELS = {
    "On Track": "On Track",
    "Deadline Near": "Deadline Near",
    "Overdue": "Overdue",
    "Escalated": "Escalated",
    "Within": "ضمن المدة",
    "Breached": "تجاوز المدة",
}
STATE_AR = {
    "On Track": "ضمن الوقت",
    "Deadline Near": "قريبة من الموعد",
    "Overdue": "متأخرة",
    "Escalated": "مصعّدة",
}
PRIO_COLORS = {
    "منخفضة": ("#e8f3ec", "#2f6f4a"),
    "متوسطة": ("#e3efff", "#1d4ed8"),
    "عالية": ("#fff0dc", "#c2570c"),
    "حرجة": ("#ffe3e3", "#c92a2a"),
}
ROLES = ["مدير النظام", "الموظف", "مدير الإدارة", "الإدارة العليا"]
ROLE_ICONS = {"مدير النظام": "🛠️", "الموظف": "👤", "مدير الإدارة": "🏢", "الإدارة العليا": "🏛️"}


# ---------------------------------------------------------------
# التصميم (ألوان خضراء وبيضاء + نقش إسلامي)
# ---------------------------------------------------------------
PAT_W = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='64' height='64' "
    "viewBox='0 0 64 64'%3E%3Cg fill='none' stroke='%23ffffff' stroke-opacity='0.13' stroke-width='1.2'%3E"
    "%3Cpath d='M32 2 L62 32 L32 62 L2 32 Z'/%3E%3Cpath d='M16 16 L48 16 L48 48 L16 48 Z'/%3E"
    "%3Ccircle cx='32' cy='32' r='11'/%3E%3C/g%3E%3C/svg%3E\")"
)
PAT_G = PAT_W.replace("%23ffffff", "%231b6b3a").replace("0.13", "0.07")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700;800&display=swap');
@keyframes rise {from {opacity:0; transform:translateY(14px);} to {opacity:1; transform:none;}}
@keyframes shine {0% {transform:translateX(120%);} 100% {transform:translateX(-120%);}}
@keyframes fillbar {from {width:0;}}

html, body, [class*='css'] {direction:rtl; text-align:right; font-family:'Tajawal', sans-serif;}
.stApp {background:#f2f9f5 __PAT_G__;}
.block-container {padding-top:1.4rem; max-width:1250px;}
footer {visibility:hidden;}
[data-testid="stToolbar"] {display:none;}
[data-testid="stHeader"] {background:transparent;}

.hero {position:relative; overflow:hidden; border-radius:24px; padding:30px 34px; display:flex; align-items:center;
  gap:26px; color:#fff; margin-bottom:18px; border-bottom:5px solid #c9a227;
  box-shadow:0 14px 34px rgba(15,81,50,.30); animation:rise .7s ease both;}
.hero::before {content:""; position:absolute; inset:0; background:__PAT_W__;}
.hero::after {content:""; position:absolute; top:0; bottom:0; width:40%;
  background:linear-gradient(100deg, transparent, rgba(255,255,255,.16), transparent); animation:shine 6s ease-in-out infinite;}
.hero > * {position:relative; z-index:1;}
.h-title {color:#fff; font-size:32px; font-weight:800; line-height:1.5;}
.h-sub {margin:2px 0 12px; opacity:.95; font-size:16px;}
.pill {display:inline-block; background:rgba(255,255,255,.18); border:1px solid rgba(255,255,255,.35); padding:4px 14px;
  border-radius:999px; font-size:13px; margin-left:8px;}
.pill.gold {background:#c9a227; border-color:#c9a227; color:#0b3d24; font-weight:700;}

.sec {display:flex; align-items:center; gap:10px; font-size:22px; font-weight:800; color:#0f5132; margin:26px 0 12px;}
.sec::before {content:""; width:6px; height:26px; border-radius:4px; background:linear-gradient(#1b6b3a, #c9a227);}

.card {background:#fff; border:1px solid #d6e9dd; border-radius:20px; padding:20px 22px;
  box-shadow:0 6px 20px rgba(27,107,58,.08); animation:rise .6s ease both;}
.card-t {font-weight:800; color:#14532d; font-size:17px; margin-bottom:14px;}

.kpis {display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:14px; margin:6px 0;}
.kpi {position:relative; background:#fff; border-radius:18px; padding:18px 16px; border:1px solid #d6e9dd;
  box-shadow:0 6px 18px rgba(27,107,58,.08); overflow:hidden; transition:.25s; animation:rise .6s ease both;}
.kpi::before {content:""; position:absolute; top:0; right:0; left:0; height:5px; background:var(--c);}
.kpi:hover {transform:translateY(-5px); box-shadow:0 14px 28px rgba(27,107,58,.18);}
.kpi .ico {font-size:26px;}
.kpi .num {font-size:38px; font-weight:800; color:var(--c); line-height:1.2;}
.kpi .lbl {color:#4b6355; font-size:14px; font-weight:500;}

.tbl-wrap {max-height:560px; overflow:auto; border-radius:18px; border:1px solid #d6e9dd; background:#fff;
  box-shadow:0 6px 20px rgba(27,107,58,.08); animation:rise .6s ease both;}
.tbl {width:100%; border-collapse:collapse; font-size:14px; min-width:980px;}
.tbl th {position:sticky; top:0; background:linear-gradient(135deg, #0f5132, #1f7a47); color:#fff; padding:13px 12px;
  text-align:right; font-weight:700; white-space:nowrap; z-index:2;}
.tbl td {padding:11px 12px; border-bottom:1px solid #edf5f0; white-space:nowrap; color:#1f3a2a;}
.tbl tr:nth-child(even) td {background:#f8fcf9;}
.tbl tr:hover td {background:#e8f5ed;}
.tbl .id {font-weight:800; color:#1b6b3a;}
.badge {display:inline-block; padding:4px 12px; border-radius:999px; color:#fff; font-weight:700; font-size:12.5px;}
.chip {display:inline-block; padding:3px 11px; border-radius:8px; font-weight:700; font-size:12.5px;}
.bar {display:inline-block; vertical-align:middle; width:110px; height:10px; background:#e3eee7; border-radius:999px; overflow:hidden;}
.bar > div {height:100%; border-radius:999px; animation:fillbar 1.2s ease both;}
.bar.big {display:block; width:100%; height:12px;}
.pct {font-size:12.5px; font-weight:700; margin-right:8px; color:#35523f;}
.empty {text-align:center; padding:40px; background:#fff; border:2px dashed #b9dcc6; border-radius:18px;
  color:#3c6a4d; font-size:18px; font-weight:700;}

.ringbox {display:flex; align-items:center; gap:22px;}
.ring {width:150px; height:150px; border-radius:50%; display:grid; place-items:center; flex-shrink:0;}
.ring-in {width:114px; height:114px; border-radius:50%; background:#fff; display:grid; place-items:center;
  font-size:34px; font-weight:800; color:#1b6b3a; box-shadow:inset 0 0 0 1px #e1eee6;}
.ring-lbl {color:#4b6355; font-size:15px; line-height:1.8;}
.donut {width:150px; height:150px; border-radius:50%; display:grid; place-items:center; flex-shrink:0;}
.donut-in {width:100px; height:100px; border-radius:50%; background:#fff; display:flex; flex-direction:column;
  align-items:center; justify-content:center; font-weight:800; color:#0f5132; font-size:28px; line-height:1.1;}
.donut-in small {font-size:11px; color:#6b8575; font-weight:500;}
.legend {display:grid; gap:8px; font-size:14.5px; color:#2d4a38;}
.dot {display:inline-block; width:12px; height:12px; border-radius:50%; margin-left:8px; vertical-align:middle;}

.brow {display:flex; align-items:center; gap:12px; margin:12px 0;}
.bname {width:150px; font-weight:700; color:#244a33; font-size:14.5px;}
.btrack {flex:1; height:16px; background:#e3eee7; border-radius:999px; overflow:hidden;}
.bfill {height:100%; border-radius:999px; background:linear-gradient(90deg, #0f5132, #2e9e5b 60%, #c9a227);
  animation:fillbar 1.2s ease both;}

.tcard {background:#fff; border:1px solid #d6e9dd; border-radius:16px; padding:16px 18px; margin-top:14px;
  box-shadow:0 5px 16px rgba(27,107,58,.08); animation:rise .5s ease both;}
.tc-top {display:flex; justify-content:space-between; align-items:center; gap:10px; font-size:16px; color:#14532d;}
.tc-meta {color:#5b7767; font-size:13.5px; margin:8px 0 10px;}
.tc-time {margin-top:8px; font-size:13.5px; color:#35523f; font-weight:500;}
.foot {text-align:center; color:#5b7767; font-size:13px; margin-top:34px; padding-top:16px; border-top:1px solid #d6e9dd;}

div[role="radiogroup"] {gap:10px; flex-wrap:wrap;}
div[role="radiogroup"] > label {background:#fff; border:1px solid #cfe5d7; border-radius:999px; padding:8px 20px;
  box-shadow:0 3px 10px rgba(27,107,58,.08); transition:.2s; cursor:pointer;}
div[role="radiogroup"] > label:hover {transform:translateY(-2px);}
div[role="radiogroup"] > label:has(input:checked) {background:#1b6b3a; border-color:#1b6b3a;}
div[role="radiogroup"] > label:has(input:checked) p {color:#fff !important;}
.stButton > button, .stFormSubmitButton > button {background:linear-gradient(135deg, #0f5132, #1f8a4c); color:#fff; border:none;
  border-radius:12px; padding:8px 22px; font-weight:700; box-shadow:0 4px 12px rgba(27,107,58,.25);}
.stButton > button:hover, .stFormSubmitButton > button:hover {filter:brightness(1.12); color:#fff;}
.stTabs [data-baseweb="tab"] {font-weight:700; font-size:16px;}
.stTabs [aria-selected="true"] {color:#1b6b3a;}
.stTabs [data-baseweb="tab-highlight"] {background-color:#1b6b3a;}
div[data-baseweb="select"] > div, .stTextInput input, .stTextArea textarea {border-radius:12px;}
</style>
"""
_css = CSS.replace("__PAT_G__", PAT_G).replace("__PAT_W__", PAT_W)
_css = "\n".join(line.strip() for line in _css.splitlines() if line.strip())
st.markdown(_css, unsafe_allow_html=True)


# ---------------------------------------------------------------
# أدوات مساعدة للعرض
# ---------------------------------------------------------------
esc = ihtml.escape


def img_b64(*names):
    for n in names:
        if os.path.exists(n):
            mime = "image/png" if n.lower().endswith("png") else "image/jpeg"
            with open(n, "rb") as f:
                return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return None


def fmt(h):
    h = abs(h)
    if h >= 24:
        return f"{int(h // 24)} يوم {int(h % 24)} ساعة"
    return f"{int(h)} ساعة {int((h % 1) * 60)} دقيقة"


def hrs(h):
    return f"{h // 24} يوم" if h >= 24 and h % 24 == 0 else f"{h} ساعة"


def badge(key):
    return f"<span class='badge' style='background:{COLORS[key]}'>{LABELS[key]}</span>"


def chip(p):
    bg, fg = PRIO_COLORS[p]
    return f"<span class='chip' style='background:{bg};color:{fg}'>{p}</span>"


def bar(pct, key="Within", big=False):
    cls = "bar big" if big else "bar"
    return (
        f"<div class='{cls}'><div style='width:{pct:.0f}%;background:{COLORS[key]}'></div></div>"
        + ("" if big else f"<span class='pct'>{pct:.0f}%</span>")
    )


def section(title):
    st.markdown(f"<div class='sec'>{title}</div>", unsafe_allow_html=True)


def card(title, body):
    st.markdown(f"<div class='card'><div class='card-t'>{title}</div>{body}</div>", unsafe_allow_html=True)


def simple_table(headers, rows):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    st.markdown(
        f"<div class='tbl-wrap'><table class='tbl' style='min-width:0'><thead><tr>{head}</tr></thead>"
        f"<tbody>{body}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def show(d):
    if len(d) == 0:
        st.markdown("<div class='empty'>🎉 ما فيه مهام هنا</div>", unsafe_allow_html=True)
        return
    rows = ""
    for _, r in d.iterrows():
        rows += (
            f"<tr><td class='id'>{r['id']}</td><td>{esc(str(r['title']))}</td><td>{r['type']}</td>"
            f"<td>{chip(r['priority'])}</td><td>{r['dept']}</td><td>{r['employee']}</td>"
            f"<td>{r['status']}</td><td>{badge(r['sla_key'])}</td>"
            f"<td>{bar(r['progress'], r['sla_key'])}</td><td>{r['time_text']}</td>"
            f"<td>{r['deadline'].strftime('%Y-%m-%d %H:%M')}</td></tr>"
        )
    heads = ["الرقم", "العنوان", "النوع", "الأولوية", "الإدارة", "الموظف", "حالة المهمة",
             "حالة SLA", "نسبة الاستهلاك", "الوقت", "الموعد النهائي"]
    head = "".join(f"<th>{h}</th>" for h in heads)
    st.markdown(
        f"<div class='tbl-wrap'><table class='tbl'><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------
# البيانات الوهمية
# ---------------------------------------------------------------
def make_data(n=60):
    rnd = random.Random(42)
    now = datetime.now()
    rows = []
    for i in range(1, n + 1):
        t = rnd.choice(TYPES)
        p = rnd.choice(PRIORITIES)
        emp = rnd.choice(ALL_EMPLOYEES)
        hours = SLA_HOURS[(t, p)]
        created = now - timedelta(hours=rnd.randint(1, 240))
        status = rnd.choices(TASK_STATUSES, weights=[5, 15, 25, 35, 20])[0]
        started, completed = pd.NaT, pd.NaT
        if status in ["قيد التنفيذ"] + DONE_STATUSES:
            started = created + timedelta(minutes=30)
        if status in DONE_STATUSES:
            completed = created + timedelta(hours=hours * rnd.uniform(0.3, 1.4))
            completed = min(completed, now - timedelta(minutes=5))
            completed = max(completed, created + timedelta(minutes=45))
        rows.append(
            {
                "id": f"T-{i:03d}",
                "title": rnd.choice(TITLES),
                "type": t,
                "priority": p,
                "dept": EMP_DEPT[emp],
                "employee": emp,
                "status": status,
                "created": created,
                "started": started,
                "completed": completed,
                "notes": "",
            }
        )
    df = pd.DataFrame(rows)
    for c in ["created", "started", "completed"]:
        df[c] = pd.to_datetime(df[c])
    return df


if "tasks" not in st.session_state:
    st.session_state.tasks = make_data()


# ---------------------------------------------------------------
# الحسابات التلقائية (الموعد النهائي، الوقت المتبقي، حالة SLA...)
# ---------------------------------------------------------------
def enrich(raw):
    now = datetime.now()
    d = raw.copy()
    d["sla_hours"] = [SLA_HOURS[(t, p)] for t, p in zip(d["type"], d["priority"])]
    d["deadline"] = d["created"] + pd.to_timedelta(d["sla_hours"], unit="h")
    d["done"] = d["status"].isin(DONE_STATUSES)

    keys, progress, time_text, result = [], [], [], []
    for _, r in d.iterrows():
        if r["done"]:
            actual = (r["completed"] - r["created"]).total_seconds() / 3600
            ok = actual <= r["sla_hours"]
            result.append("ضمن المدة" if ok else "تجاوز المدة")
            keys.append("Within" if ok else "Breached")
            progress.append(min(actual / r["sla_hours"] * 100, 100))
            time_text.append(f"أُنجزت خلال {fmt(actual)}")
        else:
            elapsed = (now - r["created"]).total_seconds() / 3600
            pct = elapsed / r["sla_hours"] * 100
            over = elapsed - r["sla_hours"]
            if pct >= 100:
                key = "Escalated" if over >= ESC_HOURS[r["priority"]] else "Overdue"
            elif pct >= 80:
                key = "Deadline Near"
            else:
                key = "On Track"
            result.append(None)
            keys.append(key)
            progress.append(min(pct, 100))
            time_text.append(f"متأخرة {fmt(over)}" if over > 0 else f"متبقي {fmt(-over)}")
    d["sla_key"] = keys
    d["progress"] = progress
    d["time_text"] = time_text
    d["result"] = result
    return d


def compliance(d):
    done = d[d["done"]]
    if len(done) == 0:
        return 0.0
    return (done["result"] == "ضمن المدة").mean() * 100


def count(d, key):
    return int(((~d["done"]) & (d["sla_key"] == key)).sum())


def kpi_cards(d):
    items = [
        ("📋", "إجمالي المهام", len(d), "#1b6b3a"),
        ("🟢", "ضمن الوقت", count(d, "On Track"), COLORS["On Track"]),
        ("🟡", "قريبة من الموعد", count(d, "Deadline Near"), COLORS["Deadline Near"]),
        ("🔴", "متأخرة", count(d, "Overdue"), COLORS["Overdue"]),
        ("🟣", "مصعّدة", count(d, "Escalated"), COLORS["Escalated"]),
        ("✅", "مكتملة", int(d["done"].sum()), "#0f5132"),
    ]
    html = "".join(
        f"<div class='kpi' style='--c:{c}'><div class='ico'>{i}</div><div class='num'>{v}</div><div class='lbl'>{l}</div></div>"
        for i, l, v, c in items
    )
    st.markdown(f"<div class='kpis'>{html}</div>", unsafe_allow_html=True)


def ring_html(pct, label):
    return (
        f"<div class='ringbox'><div class='ring' style='background:conic-gradient(#1b6b3a {pct:.0f}%, #dcebe1 0)'>"
        f"<div class='ring-in'>{pct:.0f}%</div></div><div class='ring-lbl'>{label}</div></div>"
    )


def donut_html(d):
    keys = ["On Track", "Deadline Near", "Overdue", "Escalated"]
    counts = [count(d, k) for k in keys]
    total = sum(counts)
    stops, acc = [], 0
    for k, c in zip(keys, counts):
        start = acc / total * 100 if total else 0
        acc += c
        end = acc / total * 100 if total else 0
        stops.append(f"{COLORS[k]} {start:.1f}% {end:.1f}%")
    grad = ", ".join(stops) if total else "#dcebe1 0% 100%"
    legend = "".join(
        f"<div><span class='dot' style='background:{COLORS[k]}'></span>{STATE_AR[k]} <b>{c}</b></div>"
        for k, c in zip(keys, counts)
    )
    return (
        f"<div class='ringbox'><div class='donut' style='background:conic-gradient({grad})'>"
        f"<div class='donut-in'>{total}<small>مهمة مفتوحة</small></div></div><div class='legend'>{legend}</div></div>"
    )


def bars_html(values):
    return "".join(
        f"<div class='brow'><span class='bname'>{k}</span>"
        f"<div class='btrack'><div class='bfill' style='width:{v:.0f}%'></div></div><b>{v:.0f}%</b></div>"
        for k, v in values.items()
    )


def dept_compliance(d):
    vals = {dp: compliance(d[d["dept"] == dp]) for dp in DEPT_EMPLOYEES}
    return dict(sorted(vals.items(), key=lambda x: -x[1]))


def save_task(task_id, **changes):
    t = st.session_state.tasks
    idx = t.index[t["id"] == task_id][0]
    for k, v in changes.items():
        t.loc[idx, k] = v


# ---------------------------------------------------------------
# الواجهة
# ---------------------------------------------------------------
current_role = st.session_state.get("role", ROLES[0])
logo = img_b64("logo.png", "logo.jpg", "logo.jpeg")
haram = img_b64("haram.jpg", "haram.jpeg", "haram.png")
if haram:
    bg = f"linear-gradient(rgba(8,60,35,.90), rgba(20,120,66,.78)), url({haram}) center/cover"
else:
    bg = "linear-gradient(135deg, #0a3d24, #1b6b3a 55%, #2e9e5b)"
if logo:
    logo_html = f'<img src="{logo}" style="height:92px;background:#fff;border-radius:16px;padding:8px">'
else:
    logo_html = '<div style="font-size:64px">🕋</div>'
st.markdown(
    f'<div class="hero" style="background:{bg}">{logo_html}<div>'
    '<div class="h-title">نظام إدارة المهام ومتابعة مدة الإنجاز</div>'
    '<div class="h-sub">أمانة العاصمة المقدسة · وكالة التحول الرقمي · الإدارة العامة للحلول الرقمية</div>'
    f'<span class="pill gold">SLA Tracking System</span>'
    f'<span class="pill">{ROLE_ICONS[current_role]} {current_role}</span>'
    '<span class="pill">بيانات تجريبية</span>'
    "</div></div>",
    unsafe_allow_html=True,
)

role = st.radio("الدور", ROLES, horizontal=True, key="role", label_visibility="collapsed")
data = enrich(st.session_state.tasks)

# ---------- مدير النظام ----------
if role == "مدير النظام":
    tab1, tab2, tab3, tab4 = st.tabs(["📊 لوحة التحكم", "📋 كل المهام", "➕ مهمة جديدة", "⚙️ قواعد SLA"])

    with tab1:
        section("نظرة عامة")
        kpi_cards(data)
        c1, c2 = st.columns(2)
        with c1:
            card("نسبة الالتزام بالـ SLA", ring_html(compliance(data), "المهام المنجزة ضمن المدة ÷ إجمالي المهام المنجزة"))
        with c2:
            card("المهام المفتوحة حسب حالة SLA", donut_html(data))
        section("التزام الإدارات")
        card("مقارنة الإدارات", bars_html(dept_compliance(data)))
        section("🚨 تحتاج تدخل عاجل")
        show(data[(~data["done"]) & data["sla_key"].isin(["Overdue", "Escalated"])].head(8))

    with tab2:
        section("كل المهام")
        show(data)

    with tab3:
        section("إنشاء مهمة جديدة")
        with st.form("new_task"):
            title = st.text_input("العنوان")
            desc = st.text_area("الوصف")
            c1, c2, c3 = st.columns(3)
            t = c1.selectbox("النوع", TYPES)
            p = c2.selectbox("الأولوية", PRIORITIES)
            emp = c3.selectbox("إسناد إلى", ALL_EMPLOYEES)
            submitted = st.form_submit_button("إنشاء المهمة")
        if submitted:
            if not title.strip():
                st.error("العنوان مطلوب")
            else:
                new_id = f"T-{len(st.session_state.tasks) + 1:03d}"
                row = {
                    "id": new_id, "title": title, "type": t, "priority": p,
                    "dept": EMP_DEPT[emp], "employee": emp, "status": "مسندة",
                    "created": pd.Timestamp(datetime.now()),
                    "started": pd.NaT, "completed": pd.NaT, "notes": desc,
                }
                st.session_state.tasks = pd.concat(
                    [st.session_state.tasks, pd.DataFrame([row])], ignore_index=True
                )
                st.success(
                    f"تم إنشاء المهمة {new_id}. مدة SLA: {hrs(SLA_HOURS[(t, p)])} (تحسب تلقائيًا من النوع والأولوية)."
                )
                st.balloons()

    with tab4:
        section("مدة الإنجاز حسب النوع والأولوية")
        simple_table(
            ["نوع المهمة"] + PRIORITIES,
            [[f"<b>{t}</b>"] + [hrs(h) for h in BASE_HOURS[t]] for t in TYPES],
        )
        section("قواعد التصعيد")
        simple_table(
            ["الأولوية", "التصعيد بعد تجاوز الموعد النهائي"],
            [[chip(p), "مباشرة" if h == 0 else f"{h} ساعة"] for p, h in ESC_HOURS.items()],
        )

# ---------- الموظف ----------
elif role == "الموظف":
    me = st.selectbox("اختاري الموظف", ALL_EMPLOYEES)
    mine = data[data["employee"] == me]
    section(f"مهام {me}")
    kpi_cards(mine)

    section("المهام المفتوحة")
    open_tasks = mine[~mine["done"]]
    if len(open_tasks) == 0:
        st.markdown("<div class='empty'>🎉 خلصتي كل مهامك</div>", unsafe_allow_html=True)
    for _, r in open_tasks.iterrows():
        st.markdown(
            f"<div class='tcard' style='border-right:6px solid {COLORS[r['sla_key']]}'>"
            f"<div class='tc-top'><b>{r['id']} · {esc(str(r['title']))}</b>{badge(r['sla_key'])}</div>"
            f"<div class='tc-meta'>{r['type']} · {chip(r['priority'])} · {r['status']}</div>"
            f"{bar(r['progress'], r['sla_key'], big=True)}"
            f"<div class='tc-time'>{r['time_text']} · الموعد النهائي: {r['deadline'].strftime('%Y-%m-%d %H:%M')} · "
            f"استهلاك {r['progress']:.0f}%</div></div>",
            unsafe_allow_html=True,
        )
        if r["notes"]:
            st.caption(f"📝 {r['notes']}")
        c1, c2, c3 = st.columns([3, 1, 1])
        note = c1.text_input("ملاحظة", key=f"n{r['id']}", placeholder="اكتبي ملاحظة أو تحديث", label_visibility="collapsed")
        if c2.button("حفظ الملاحظة", key=f"b{r['id']}") and note:
            save_task(r["id"], notes=(str(r["notes"]) + " | " + note).strip(" |"))
            st.rerun()
        if r["status"] in ("جديدة", "مسندة"):
            if c3.button("▶ بدء العمل", key=f"s{r['id']}"):
                save_task(r["id"], status="قيد التنفيذ", started=pd.Timestamp(datetime.now()))
                st.rerun()
        elif r["status"] == "قيد التنفيذ":
            if c3.button("✔ إنهاء المهمة", key=f"c{r['id']}"):
                save_task(r["id"], status="مكتملة", completed=pd.Timestamp(datetime.now()))
                st.rerun()

    section("كل مهامي")
    show(mine)

# ---------- مدير الإدارة ----------
elif role == "مدير الإدارة":
    dept = st.selectbox("الإدارة", list(DEPT_EMPLOYEES))
    d = data[data["dept"] == dept]
    section(f"إدارة {dept}")
    kpi_cards(d)
    c1, c2 = st.columns(2)
    with c1:
        card("التزام الإدارة بالمدة المحددة", ring_html(compliance(d), f"نسبة التزام إدارة {dept}"))
    with c2:
        card("المهام المفتوحة حسب الحالة", donut_html(d))

    section("⚠️ مهام تحتاج متابعة")
    show(d[(~d["done"]) & (d["sla_key"] != "On Track")])

    section("أداء الموظفين")
    rows = []
    for emp in DEPT_EMPLOYEES[dept]:
        g = d[d["employee"] == emp]
        done = g[g["done"]]
        within = int((g["result"] == "ضمن المدة").sum())
        late = int(g["sla_key"].isin(["Overdue", "Escalated"]).sum())
        rate = within / len(done) * 100 if len(done) else 0
        rows.append([f"<b>{emp}</b>", len(done), within, late, bar(rate, "Within")])
    simple_table(["الموظف", "المنجزة", "المنجزة ضمن المدة", "المتأخرة حاليًا", "نسبة الالتزام"], rows)

# ---------- الإدارة العليا ----------
else:
    section("نظرة شاملة")
    kpi_cards(data)
    c1, c2 = st.columns(2)
    with c1:
        card("نسبة الالتزام العامة", ring_html(compliance(data), "على مستوى جميع الإدارات"))
    with c2:
        card("المهام المفتوحة حسب الحالة", donut_html(data))

    section("🟣 المهام المصعّدة")
    show(data[(~data["done"]) & (data["sla_key"] == "Escalated")])

    section("مقارنة الإدارات بنسبة الالتزام")
    card("الترتيب من الأعلى إلى الأدنى", bars_html(dept_compliance(data)))

st.markdown("<div class='foot'>أمانة العاصمة المقدسة · وكالة التحول الرقمي · نموذج أولي ببيانات تجريبية</div>", unsafe_allow_html=True)
if st.button("🔄 إعادة توليد البيانات الوهمية"):
    st.session_state.tasks = make_data()
    st.rerun()

st.markdown("<div class='foot'>أمانة العاصمة المقدسة · وكالة التحول الرقمي · نموذج أولي ببيانات تجريبية</div>", unsafe_allow_html=True)
if st.button("🔄 إعادة توليد البيانات الوهمية"):
    st.session_state.tasks = make_data()
    st.rerun()
