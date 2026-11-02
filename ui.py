"""ui.py - look and feel: colours, CSS and small visual components.
Theme idea: a railway signal-box. Deadlock is a junction where trains wait on
each other, so system state is shown on a SIGNAL GANTRY (five signal heads),
and a safe sequence is drawn as carriages running along a track."""
import streamlit as st

# status key -> (label, colour)
STATES = {
    "SAFE":       ("Safe",              "#1E8E5A"),
    "UNSAFE":     ("Unsafe",            "#E07B00"),
    "WAITING":    ("Waiting / deferred", "#2F6FB5"),
    "DEADLOCKED": ("Deadlocked",        "#D1342F"),
    "INVALID":    ("Invalid input",     "#6F7C8A"),
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500;600&display=swap');
:root { --ink:#14293D; --paper:#EDF1F4; --line:#CBD5DE; --brand:#F2B705; --soft:#5A6B7B; }
.stApp { background: var(--paper); }
html, body, .stApp, p, li, label, input, textarea { font-family:'Barlow','Segoe UI',sans-serif; font-size:1.02rem; }
h1,h2,h3,h4 { font-family:'Barlow Condensed','Arial Narrow',sans-serif !important; color:var(--ink); letter-spacing:.01em; }
h1 { font-weight:700 !important; font-size:2.9rem !important; }
h2 { font-size:1.9rem !important; }
h3 { font-size:1.5rem !important; }
h4 { font-size:1.3rem !important; }
.block-container { padding-top:1.6rem; max-width:1250px; }

/* sidebar = the signal box */
[data-testid="stSidebar"] { background:var(--ink); border-right:5px solid var(--brand); }
[data-testid="stSidebar"] * { color:#E8EEF3 !important; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:2px; }
[data-testid="stSidebar"] [role="radiogroup"] label { padding:9px 12px; border-radius:4px; width:100%; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:rgba(255,255,255,.08); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) { background:rgba(242,183,5,.18); box-shadow: inset 4px 0 0 var(--brand); font-weight:600; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }

/* buttons */
.stButton > button, .stDownloadButton > button { background:var(--ink); color:#fff; border:0; border-radius:4px; font-weight:600; padding:.5rem 1.1rem; transition:transform .12s, background .12s; }
.stButton > button:hover, .stDownloadButton > button:hover { background:#244A6D; color:#fff; transform:translateY(-1px); }
.stButton > button:active { transform:translateY(0); }

/* signal gantry */
.gantry { background:var(--ink); border-top:5px solid var(--brand); border-radius:6px; padding:14px 20px 12px; margin:4px 0 8px; }
.gantry .gt { color:#9FB2C4; font-size:.8rem; margin-bottom:8px; }
.heads { display:flex; gap:26px; flex-wrap:wrap; }
.sig { display:flex; align-items:center; gap:10px; color:#8296A8; font-size:.92rem; }
.housing { background:#0A1621; border-radius:8px; padding:7px; border:1px solid #27425A; }
.lens { width:20px; height:20px; border-radius:50%; background:#2A3E50; display:block; }
.sig.on { color:#fff; font-weight:600; }
.sig.on .lens { background:var(--c); box-shadow:0 0 14px 4px var(--c); animation: flash .7s ease-out 1; }
@keyframes flash { 0%{transform:scale(.6);opacity:.2} 60%{transform:scale(1.25)} 100%{transform:scale(1);opacity:1} }
@media (prefers-reduced-motion: reduce) { .sig.on .lens { animation:none; } }

.verdict { background:#fff; border:1px solid var(--line); border-left:7px solid var(--c); border-radius:0 6px 6px 0; padding:12px 18px; margin:6px 0 16px; }
.verdict b { color:var(--c); font-family:'Barlow Condensed',sans-serif; font-size:1.25rem; }

/* panels */
.panel { background:#fff; border:1px solid var(--line); border-top:4px solid var(--c, var(--ink)); border-radius:4px; padding:14px 18px; min-height:150px; }
.panel h4 { margin:0 0 6px 0; }
.panel p { margin:0; color:#33475A; font-size:.95rem; }
.hero { padding:6px 0 14px; }
.hero p { font-size:1.08rem; color:var(--soft); max-width:62ch; }

/* resource bars */
.rb { background:#fff; border:1px solid var(--line); border-radius:4px; padding:12px 16px; margin:8px 0; }
.rbt { font-weight:600; margin-bottom:8px; }
.rbrow { display:flex; align-items:center; gap:10px; margin:5px 0; }
.rbl { width:20px; font-weight:700; }
.rbtrack { flex:1; background:#E3E9EE; height:16px; border-radius:3px; overflow:hidden; }
.rbfill { height:100%; transition:width .35s ease; }
.rbn { width:62px; text-align:right; font-variant-numeric:tabular-nums; color:var(--soft); }

/* track of carriages */
.track { background:#fff; border:1px solid var(--line); border-radius:4px; padding:16px; margin:8px 0; display:flex; align-items:center; flex-wrap:wrap; gap:6px; position:relative; }
.car { padding:8px 16px; border-radius:6px 6px 3px 3px; font-weight:700; border:2px solid var(--ink); background:#fff; color:var(--ink); transition:background .25s; }
.car.done { background:#1E8E5A; border-color:#1E8E5A; color:#fff; }
.car.now  { background:var(--brand); border-color:var(--brand); }
.car.stuck{ background:#fff; border:2px dashed #D1342F; color:#D1342F; }
.arrow { color:var(--soft); font-weight:700; }

/* unsafe vs deadlocked diagram */
.venn { display:flex; gap:14px; align-items:stretch; margin:8px 0; flex-wrap:wrap; }
.venn > div { border-radius:6px; padding:14px 18px; }
.vs { background:#E4F3EB; border:2px solid #1E8E5A; flex:1; min-width:180px; }
.vu { background:#FDF0DC; border:2px solid #E07B00; flex:2; min-width:260px; }
.vd { background:#FBE3E1; border:2px solid #D1342F; margin-top:10px; }
.venn small { color:#4a5a69; display:block; }

/* sidebar team section */
.team-panel {
    margin-top: 1.8rem;
    padding: 14px 16px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-left: 3px solid var(--brand);
    border-radius: 6px;
}
.team-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
}
.team-icon {
    font-size: 1.1rem;
}
.team-title {
    font-family: 'Barlow Condensed', sans-serif !important;
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    letter-spacing: .04em;
    text-transform: uppercase;
    color: var(--brand) !important;
}
.team-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
}
.team-member {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 0.95rem;
    color: #E8EEF3 !important;
    font-weight: 500;
}
.team-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: rgba(242, 183, 5, 0.18);
    border: 1px solid var(--brand);
    color: var(--brand) !important;
    font-size: 0.75rem;
    font-weight: 700;
}
"""


def inject_css():
    st.markdown(f"<style>{CSS}</style>", unsafe_allow_html=True)


def gantry(key, text):
    heads = "".join(
        f'<div class="sig {"on" if k == key else ""}" style="--c:{c}"><span class="housing"><i class="lens"></i></span>{label}</div>'
        for k, (label, c) in STATES.items())
    st.markdown(f'<div class="gantry"><div class="gt">System state</div><div class="heads">{heads}</div></div>',
                unsafe_allow_html=True)
    if key:
        verdict(key, text)
    else:
        st.caption(text)


def verdict(key, text):
    label, c = STATES[key]
    st.markdown(f'<div class="verdict" style="--c:{c}"><b>{label}.</b> {text}</div>', unsafe_allow_html=True)


def panel(title, body, colour="#14293D"):
    st.markdown(f'<div class="panel" style="--c:{colour}"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)


def resource_bars(names, values, totals, title, colour="#2F6FB5"):
    rows = ""
    for n, v, t in zip(names, values, totals):
        pct = 0 if t <= 0 else max(0, min(100, 100 * v / t))
        rows += (f'<div class="rbrow"><span class="rbl">{n}</span><div class="rbtrack">'
                 f'<div class="rbfill" style="width:{pct:.0f}%;background:{colour}"></div></div>'
                 f'<span class="rbn">{int(v)} / {int(t)}</span></div>')
    st.markdown(f'<div class="rb"><div class="rbt">{title}</div>{rows}</div>', unsafe_allow_html=True)


def track(sequence, done_count, stuck=()):
    """Carriages in safe-sequence order. First `done_count` are finished."""
    parts = []
    for idx, p in enumerate(sequence):
        cls = "done" if idx < done_count else ("now" if idx == done_count else "")
        parts.append(f'<span class="car {cls}">P{p}</span>')
    parts = '<span class="arrow">&rsaquo;</span>'.join(parts)
    stuck_html = "".join(f'<span class="car stuck">P{p}</span>' for p in stuck)
    if stuck_html:
        parts += '<span class="arrow">&nbsp;|&nbsp;cannot finish:</span>' + stuck_html
    st.markdown(f'<div class="track">{parts}</div>', unsafe_allow_html=True)


def unsafe_vs_deadlock():
    st.markdown("""<div class="venn">
<div class="vs"><b>Safe</b><small>a completion order exists</small></div>
<div class="vu"><b>Unsafe</b><small>no completion order is guaranteed, but nobody is blocked yet</small>
<div class="vd"><b>Deadlocked</b><small>a group is stuck right now</small></div></div></div>""", unsafe_allow_html=True)


def team_members_sidebar():
    """Render a neat, professional team members card in the sidebar."""
    st.markdown("""<div class="team-panel">
    <div class="team-header">
        <span class="team-icon">👥</span>
        <span class="team-title">Team Members</span>
    </div>
    <div class="team-list">
        <div class="team-member"><span class="team-badge">1</span> Ragini Telange</div>
        <div class="team-member"><span class="team-badge">2</span> Sakshi Pawar</div>
        <div class="team-member"><span class="team-badge">3</span> Vedangi Patil</div>
    </div>
</div>""", unsafe_allow_html=True)

