import random
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="نظام تتبع SLA", page_icon="⏱️", layout="wide")
import base64
import os

st.markdown(
    """<link href="https://fonts.googleapis.com/css2?family=Tajawal:wght@400;500;700&display=swap" rel="stylesheet">
<style>
html, body, [class*='css'] {direction: rtl; text-align: right; font-family: 'Tajawal', sans-serif;}
.stApp {background: #f4faf6;}
[data-testid="stSidebar"] {background: #e3f1e8; border-left: 4px solid #1b6b3a;}
[data-testid="stMetric"] {background: white; border: 1px solid #d3e8da; border-right: 6px solid #1b6b3a;
  border-radius: 14px; padding: 14px 16px; box-shadow: 0 3px 10px rgba(27,107,58,0.10);}
[data-testid="stMetricValue"] {color: #1b6b3a; font-weight: 700;}
.stButton > button, .stFormSubmitButton > button {background: #1b6b3a; color: white; border: none;
  border-radius: 10px; padding: 8px 22px; font-weight: 700;}
.stButton > button:hover, .stFormSubmitButton > button:hover {background: #14532d; color: white;}
.stTabs [data-baseweb="tab"] {font-weight: 700; font-size: 16px;}
.stTabs [aria-selected="true"] {color: #1b6b3a;}
.stTabs [data-baseweb="tab-highlight"] {background-color: #1b6b3a;}
h2, h3 {color: #14532d;}
.hero {border-radius: 20px; padding: 26px 30px; display: flex; align-items: center; gap: 22px;
  color: white; margin-bottom: 22px; box-shadow: 0 8px 24px rgba(20,83,45,0.25);}
.hero h1 {color: white; margin: 0; font-size: 30px; line-height: 1.5;}
.hero p {margin: 4px 0 0 0; opacity: 0.92; font-size: 16px;}
</style>""",
    unsafe_allow_html=True,
)


def img_b64(*names):
    for n in names:
        if os.path.exists(n):
            mime = "image/png" if n.lower().endswith("png") else "image/jpeg"
            with open(n, "rb") as f:
                return f"data:{mime};base64," + base64.b64encode(f.read()).decode()
    return None

# ---------------------------------------------------------------
# الإعدادات والقواعد (من الوثيقة)
# ---------------------------------------------------------------
TYPES = ["فنية", "صيانة", "إدارية", "بيانات", "صلاحيات وصول", "تشغيلية"]
PRIORITIES = ["منخفضة", "متوسطة", "عالية", "حرجة"]

# المدة بالساعات: [منخفضة, متوسطة, عالية, حرجة]
# فنية وصيانة وصلاحيات وبيانات من جدول الوثيقة، وإدارية وتشغيلية قيم افتراضية من عندي
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

SLA_ICONS = {
    "On Track": "🟢 On Track",
    "Deadline Near": "🟡 Deadline Near",
    "Overdue": "🔴 Overdue",
    "Escalated": "🟣 Escalated",
}


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
def fmt(h):
    h = abs(h)
    if h >= 24:
        return f"{int(h // 24)} يوم {int(h % 24)} ساعة"
    return f"{int(h)} ساعة {int((h % 1) * 60)} دقيقة"


def enrich(raw):
    now = datetime.now()
    d = raw.copy()
    d["sla_hours"] = [SLA_HOURS[(t, p)] for t, p in zip(d["type"], d["priority"])]
    d["deadline"] = d["created"] + pd.to_timedelta(d["sla_hours"], unit="h")
    d["done"] = d["status"].isin(DONE_STATUSES)

    sla_state, progress, time_text, result = [], [], [], []
    for _, r in d.iterrows():
        if r["done"]:
            actual = (r["completed"] - r["created"]).total_seconds() / 3600
            ok = actual <= r["sla_hours"]
            result.append("ضمن المدة" if ok else "تجاوز المدة")
            sla_state.append("✅ ضمن المدة" if ok else "❌ تجاوز المدة")
            progress.append(min(actual / r["sla_hours"] * 100, 100))
            time_text.append(f"أُنجزت خلال {fmt(actual)}")
        else:
            elapsed = (now - r["created"]).total_seconds() / 3600
            pct = elapsed / r["sla_hours"] * 100
            over = elapsed - r["sla_hours"]
            if pct >= 100:
                state = "Escalated" if over >= ESC_HOURS[r["priority"]] else "Overdue"
            elif pct >= 80:
                state = "Deadline Near"
            else:
                state = "On Track"
            result.append(None)
            sla_state.append(SLA_ICONS[state])
            progress.append(min(pct, 100))
            time_text.append(f"متأخرة {fmt(over)}" if over > 0 else f"متبقي {fmt(-over)}")
    d["sla_state"] = sla_state
    d["progress"] = progress
    d["time_text"] = time_text
    d["result"] = result
    return d


def show(d):
    out = pd.DataFrame(
        {
            "الرقم": d["id"],
            "العنوان": d["title"],
            "النوع": d["type"],
            "الأولوية": d["priority"],
            "الإدارة": d["dept"],
            "الموظف": d["employee"],
            "حالة المهمة": d["status"],
            "حالة SLA": d["sla_state"],
            "الوقت": d["time_text"],
            "نسبة الاستهلاك": d["progress"],
            "الموعد النهائي": d["deadline"].dt.strftime("%Y-%m-%d %H:%M"),
        }
    )
    st.dataframe(
        out,
        hide_index=True,
        column_config={
            "نسبة الاستهلاك": st.column_config.ProgressColumn(
                "نسبة الاستهلاك", min_value=0, max_value=100, format="%d%%"
            )
        },
    )


def compliance(d):
    done = d[d["done"]]
    if len(done) == 0:
        return 0.0
    return (done["result"] == "ضمن المدة").mean() * 100


def kpis(d):
    c = st.columns(7)
    open_d = d[~d["done"]]
    c[0].metric("إجمالي المهام", len(d))
    c[1].metric("ضمن الوقت", int(open_d["sla_state"].str.contains("On Track").sum()))
    c[2].metric("قريبة من الموعد", int(open_d["sla_state"].str.contains("Near").sum()))
    c[3].metric("متأخرة", int(open_d["sla_state"].str.contains("Overdue").sum()))
    c[4].metric("مصعّدة", int(open_d["sla_state"].str.contains("Escalated").sum()))
    c[5].metric("مكتملة", int(d["done"].sum()))
    c[6].metric("نسبة الالتزام", f"{compliance(d):.0f}%")


def state_chart(d):
    open_d = d[~d["done"]]
    counts = open_d["sla_state"].value_counts()
    st.bar_chart(counts, color="#1b6b3a")


def save_task(task_id, **changes):
    t = st.session_state.tasks
    idx = t.index[t["id"] == task_id][0]
    for k, v in changes.items():
        t.loc[idx, k] = v


# ---------------------------------------------------------------
# الواجهة
# ---------------------------------------------------------------
logo = img_b64("logo.png", "logo.jpg", "logo.jpeg")
haram = img_b64("haram.jpg", "haram.jpeg", "haram.png")
if haram:
    bg = f"linear-gradient(rgba(10,70,40,.88), rgba(20,120,66,.78)), url({haram}) center/cover"
else:
    bg = "linear-gradient(135deg,#0f5132,#1f8a4c)"
if logo:
    logo_html = f'<img src="{logo}" style="height:84px;background:white;border-radius:14px;padding:8px">'
else:
    logo_html = '<div style="font-size:60px">🕋</div>'
st.markdown(
    f'<div class="hero" style="background:{bg}">{logo_html}<div>'
    "<h1>نظام إدارة المهام ومتابعة مدة الإنجاز</h1>"
    "<p>أمانة العاصمة المقدسة | وكالة التحول الرقمي | SLA Tracking System</p>"
    "</div></div>",
    unsafe_allow_html=True,
)

role = st.sidebar.radio("اختاري الدور", ["مدير النظام", "الموظف", "مدير الإدارة", "الإدارة العليا"])
if st.sidebar.button("إعادة توليد البيانات"):
    st.session_state.tasks = make_data()
    st.rerun()

data = enrich(st.session_state.tasks)

# ---------- مدير النظام ----------
if role == "مدير النظام":
    tab1, tab2, tab3, tab4 = st.tabs(["لوحة التحكم", "كل المهام", "مهمة جديدة", "قواعد SLA"])

    with tab1:
        kpis(data)
        st.subheader("المهام المفتوحة حسب حالة SLA")
        state_chart(data)

    with tab2:
        show(data)

    with tab3:
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
                hours = SLA_HOURS[(t, p)]
                st.success(f"تم إنشاء المهمة {new_id}. مدة SLA: {hours} ساعة (تحسب تلقائيًا من النوع والأولوية).")

    with tab4:
        st.subheader("مدة الإنجاز (بالساعات) حسب النوع والأولوية")
        rules = pd.DataFrame(BASE_HOURS, index=PRIORITIES).T
        st.dataframe(rules)
        st.subheader("قواعد التصعيد")
        st.dataframe(
            pd.DataFrame(
                {"الأولوية": list(ESC_HOURS), "التصعيد بعد تجاوز الموعد (ساعة)": list(ESC_HOURS.values())}
            ),
            hide_index=True,
        )

# ---------- الموظف ----------
elif role == "الموظف":
    me = st.sidebar.selectbox("الموظف", ALL_EMPLOYEES)
    mine = data[data["employee"] == me]
    st.subheader(f"مهام {me}")
    show(mine)

    st.subheader("تحديث المهام المفتوحة")
    for _, r in mine[~mine["done"]].iterrows():
        with st.expander(f"{r['id']} - {r['title']} | {r['sla_state']} | {r['time_text']}"):
            st.progress(int(r["progress"]))
            c1, c2 = st.columns(2)
            if r["status"] in ("جديدة", "مسندة"):
                if c1.button("بدء العمل", key=f"s{r['id']}"):
                    save_task(r["id"], status="قيد التنفيذ", started=pd.Timestamp(datetime.now()))
                    st.rerun()
            if r["status"] == "قيد التنفيذ":
                if c1.button("إنهاء المهمة", key=f"c{r['id']}"):
                    save_task(r["id"], status="مكتملة", completed=pd.Timestamp(datetime.now()))
                    st.rerun()
            note = st.text_input("ملاحظة", key=f"n{r['id']}")
            if c2.button("حفظ الملاحظة", key=f"b{r['id']}") and note:
                save_task(r["id"], notes=(r["notes"] + " | " + note).strip(" |"))
                st.rerun()
            if r["notes"]:
                st.caption(f"الملاحظات: {r['notes']}")

# ---------- مدير الإدارة ----------
elif role == "مدير الإدارة":
    dept = st.sidebar.selectbox("الإدارة", list(DEPT_EMPLOYEES))
    d = data[data["dept"] == dept]
    st.subheader(f"إدارة {dept}")
    kpis(d)

    st.subheader("مهام تحتاج متابعة (قريبة من الموعد / متأخرة / مصعّدة)")
    attention = d[(~d["done"]) & (~d["sla_state"].str.contains("On Track"))]
    show(attention)

    st.subheader("أداء الموظفين")
    perf = d.groupby("employee").apply(
        lambda g: pd.Series(
            {
                "المنجزة": int(g["done"].sum()),
                "المنجزة ضمن المدة": int((g["result"] == "ضمن المدة").sum()),
                "المتأخرة حاليًا": int(g["sla_state"].str.contains("Overdue|Escalated").sum()),
            }
        ),
        include_groups=False,
    )
    st.dataframe(perf)

# ---------- الإدارة العليا ----------
else:
    st.subheader("المهام المصعّدة")
    show(data[data["sla_state"].str.contains("Escalated")])

    st.subheader("نسب الالتزام بالـ SLA لكل إدارة")
    comp = pd.Series({dp: compliance(data[data["dept"] == dp]) for dp in DEPT_EMPLOYEES})
    st.bar_chart(comp, color="#1b6b3a")
    st.dataframe(comp.round(1).rename("نسبة الالتزام %"))
