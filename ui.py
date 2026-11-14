"""Look and feel. Calm, clear and easy to read on a phone in a busy corridor.

Colours: spruce ink for text and the header, one teal for actions, red ONLY for emergencies, amber for "check".
Font: Atkinson Hyperlegible Next, made for readability (bundled in static/fonts, so it also works offline).
"""
import html
from urllib.parse import quote

import streamlit as st

FALLS_COLOURS = {
    "High": ("#8E2A1F", "#FBE4E0"),
    "Medium": ("#7A4B00", "#FCEFCF"),
    "Low": ("#1F5A33", "#DDF1E4"),
}

CSS = """
<style>
@font-face { font-family: 'Atkinson'; font-weight: 400; font-display: swap; src: url('app/static/fonts/atkinson-400.woff2') format('woff2'); }
@font-face { font-family: 'Atkinson'; font-weight: 600; font-display: swap; src: url('app/static/fonts/atkinson-600.woff2') format('woff2'); }
@font-face { font-family: 'Atkinson'; font-weight: 700; font-display: swap; src: url('app/static/fonts/atkinson-700.woff2') format('woff2'); }
@font-face { font-family: 'Atkinson'; font-weight: 800; font-display: swap; src: url('app/static/fonts/atkinson-800.woff2') format('woff2'); }

:root {
  --ink: #10282C; --ink-2: #4A6165; --line: #D3DEDC; --page: #EDF2F1; --card: #FFFFFF;
  --teal: #0E7C7B; --teal-d: #0A5F5E; --teal-bg: #DDF0EE;
  --red: #B3261E; --red-bg: #FDECEA; --amber: #8A5A00; --amber-bg: #FFF3D6; --green: #1F6B3E; --green-bg: #E1F3E8;
}
html, body, [class*="st-"], .stApp, h1, h2, h3, h4, h5, h6, p, li, label, a, span, div, button, input, textarea, select {
  font-family: 'Atkinson', 'Segoe UI', system-ui, -apple-system, sans-serif !important; }
.stApp { background: var(--page); color: var(--ink); }
.stApp [data-testid="stIconMaterial"], .stApp span[class*="material"] { font-family: 'Material Symbols Rounded', 'Material Icons' !important; }
html, body { font-size: 18px; }
.block-container { padding: 1rem 1rem 6rem; max-width: 620px; }
header[data-testid="stHeader"] { background: transparent; }
#MainMenu, footer, [data-testid="stDeployButton"], [data-testid="stStatusWidget"] { visibility: hidden; }
h1, h2, h3 { letter-spacing: -0.01em; color: var(--ink); }
h2 { font-size: 1.5rem; font-weight: 800; padding: 0; }
h3 { font-size: 1.15rem; font-weight: 700; }
p, li { line-height: 1.5; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] *, .stCaption, small { color: var(--ink-2) !important; opacity: 1 !important; }

/* ---- top bar ---- */
.topbar { display:flex; align-items:center; gap:12px; background: var(--ink); color:#fff; border-radius:18px; padding:12px 14px; margin-bottom: 10px; }
.topbar .mark { width:40px; height:40px; flex:none; }
.topbar .nm { font-size:1.35rem; font-weight:800; line-height:1.1; color:#fff; }
.topbar .sub { font-size:.8rem; color:#A9C4C3; line-height:1.2; }
.topbar .demo { margin-left:auto; font-size:.74rem; font-weight:700; color:#10282C; background:#F4D58D; border-radius:999px; padding:4px 10px; white-space:nowrap; }

/* ---- generic buttons ---- */
.stButton > button, .stDownloadButton > button {
  min-height: 3rem; font-weight: 700; border-radius: 14px; border: 1.5px solid var(--line); background: var(--card);
  color: var(--ink); transition: background .12s, border-color .12s; }
.stButton > button:hover { border-color: var(--teal); color: var(--teal-d); background: #F7FBFA; }
.stButton > button p { font-weight: 700; }
.stButton > button:focus-visible { outline: 3px solid #7FC8C5; outline-offset: 2px; }
.stButton > button[kind="primary"], button[data-testid="stBaseButton-primary"] {
  background: var(--teal); border-color: var(--teal); color: #fff; }
.stButton > button[kind="primary"]:hover, button[data-testid="stBaseButton-primary"]:hover { background: var(--teal-d); border-color: var(--teal-d); color:#fff; }
.stButton > button[kind="primary"] p, button[data-testid="stBaseButton-primary"] p { color:#fff; }
.st-key-em_btn button, .st-key-em_send button { background: var(--red) !important; border-color: var(--red) !important; color:#fff !important;
  min-height: 3.4rem; font-size: 1.08rem; box-shadow: 0 6px 16px rgba(179,38,30,.28); }
.st-key-em_btn button:hover, .st-key-em_send button:hover { background:#8F1D17 !important; border-color:#8F1D17 !important; }
.st-key-em_btn button p, .st-key-em_send button p { color:#fff !important; }

/* ---- bordered containers become cards ---- */
[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card); border: 1px solid #DCE6E4 !important; border-radius: 18px; box-shadow: 0 1px 0 rgba(15,42,46,.03), 0 4px 12px rgba(15,42,46,.04); }
[class*="st-key-res_"] { background: var(--card); border-radius: 18px; }

/* ---- resident list ---- */
.rescard { display:flex; gap:14px; align-items:center; margin-bottom: 12px; }
.rescard img { width:72px; height:72px; border-radius:50%; flex:none; border:3px solid #fff; box-shadow:0 0 0 1px var(--line); }
.rescard .nm { font-size:1.2rem; font-weight:800; line-height:1.2; color: var(--ink); }
.rescard .rm { font-size:.95rem; color: var(--ink-2); margin-bottom:6px; }
.chips { display:flex; flex-wrap:wrap; gap:6px; }
.chip { display:inline-block; font-size:.8rem; font-weight:700; border-radius:999px; padding:3px 10px; line-height:1.5; }
.chip.neutral { background:#E7EEED; color:#2D4649; }
.chip.warn { background: var(--amber-bg); color: var(--amber); }
.chip.ok { background: var(--green-bg); color: var(--green); }
.taskrow { line-height: 1.45; }
.chip.allergy { background: var(--red-bg); color: var(--red); }
.pill { display:inline-block; font-size:.8rem; font-weight:700; border-radius:999px; padding:3px 10px; line-height:1.5; }

/* ---- resident header ---- */
.reshead { display:flex; gap:16px; align-items:center; margin: 6px 0 8px; }
.reshead img { width:88px; height:88px; border-radius:50%; border:3px solid #fff; box-shadow:0 0 0 1px var(--line); flex:none; }
.reshead .nm { font-size:1.6rem; font-weight:800; line-height:1.1; letter-spacing:-.01em; }
.reshead .rm { color: var(--ink-2); margin: 2px 0 8px; }

/* ---- tabs ---- */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: 1px solid var(--line); overflow-x: auto; }
.stTabs [data-baseweb="tab"] { font-weight:700; padding: 10px 12px; color: var(--ink-2); height: auto; }
.stTabs [aria-selected="true"] { color: var(--teal-d); }
.stTabs [data-baseweb="tab-highlight"] { background: var(--teal); height: 3px; }

/* ---- chat ---- */
[data-testid="stChatMessage"] { background: transparent; padding: .25rem 0; gap: .6rem; }
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessage"] [data-testid="stChatMessageAvatarAssistant"] { display:none; }
[data-testid="stChatMessageContent"] { width: 100%; }
.ubub { background: var(--teal); color:#fff; border-radius: 18px 18px 4px 18px; padding: 10px 14px; margin-left: auto;
  width: fit-content; max-width: 88%; line-height: 1.7; overflow-wrap: anywhere; }
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) [data-testid="stChatMessageContent"] { width: 100%; }

.src { display:inline-block; font-size:.78rem; font-weight:600; color:#2D4649; background:#E7EEED; border-radius:8px; padding:3px 8px; margin:2px 4px 2px 0; }
.srcrow { margin-top:8px; }
.srcrow .lbl { font-size:.78rem; color: var(--ink-2); margin-right:6px; }
.foot { font-size:.8rem; color: var(--ink-2); margin-top:6px; }
.banner { border-radius:12px; padding:10px 12px; font-weight:700; margin-bottom:8px; }
.banner.urgent { background: var(--red-bg); color: var(--red); border:1px solid #F2B8B3; }
.banner.check { background: var(--amber-bg); color: var(--amber); border:1px solid #EBD08A; }
.st-key-urg [data-testid="stVerticalBlockBorderWrapper"], [class*="st-key-urgent_"] { border-left: 6px solid var(--red) !important; }
[class*="st-key-chk_"] { border-left: 6px solid #D89B1D !important; }
.emptychat { background: var(--card); border:1px dashed var(--line); border-radius:16px; padding:14px; margin-bottom:10px; }
.emptychat b { font-size:1.05rem; }

/* ---- quick questions: two per row, also on a phone ---- */
.st-key-quick [data-testid="stHorizontalBlock"], [class*="st-key-nf_"] [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: wrap; gap: .5rem; }
.st-key-quick [data-testid="stColumn"], [class*="st-key-nf_"] [data-testid="stColumn"] { min-width: calc(50% - .5rem) !important; flex: 1 1 calc(50% - .5rem) !important; width: auto !important; }
[class*="st-key-tiles"] [data-testid="stHorizontalBlock"], .st-key-top_actions [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap; gap: .7rem; }
[class*="st-key-tiles"] [data-testid="stColumn"], .st-key-top_actions [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
.st-key-tiles_plan [data-testid="stVerticalBlock"] { gap: .5rem; }
.st-key-top_actions [data-testid="stVerticalBlock"] { gap: .6rem; }
/* action tiles: icon disc on top, label under it, left aligned */
[class*="st-key-tile_"] button { min-height: 8.2rem; border-radius: 20px; background: #FFFFFF; border: 1px solid #DCE6E4;
  box-shadow: 0 1px 0 rgba(15,42,46,.04), 0 8px 18px rgba(15,42,46,.06); padding: 14px; transition: border-color .12s, box-shadow .12s, transform .12s; }
[class*="st-key-tile_"] button:hover { border-color: var(--teal); box-shadow: 0 1px 0 rgba(15,42,46,.04), 0 10px 22px rgba(14,124,123,.16); background:#fff; }
[class*="st-key-tile_"] button:active { transform: scale(.985); }
[class*="st-key-tile_"] button, [class*="st-key-tile_"] button > div, [class*="st-key-tile_"] button > div > span {
  display: flex; flex-direction: column !important; width: 100%; align-items: flex-start; justify-content: space-between; gap: .7rem; }
[class*="st-key-tile_"] button [data-testid="stIconMaterial"] { width: 46px; height: 46px; border-radius: 50%; display: inline-flex !important; flex: none; min-width: 46px;
  align-items: center; justify-content: center; font-size: 1.6rem !important; background: var(--teal-bg); color: var(--teal-d); }
[class*="st-key-tile_"] button > div > span > span:first-child { margin: 0 !important; width: auto !important; height: auto !important; flex: none; display: inline-flex; }
[class*="st-key-tile_"] button p { white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
  font-size: 1.05rem; font-weight: 700; line-height: 1.25; text-align: left; color: var(--ink); }
[class*="st-key-tile_warn_"] button { background: #FFFAEC; border-color: #EEDDB0; }
[class*="st-key-tile_warn_"] button [data-testid="stIconMaterial"] { background: #FBE9BD; color: #7A4B00; }
/* care plan: calm rows with a chevron */
[class*="st-key-tile_"] button [data-testid="stMarkdownContainer"] { text-align: left; width: 100%; }
[class*="st-key-tile_plain_"] button { flex-direction: row !important; align-items: center; justify-content: space-between; min-height: 3.6rem;
  padding: 9px 14px 9px 10px; border-radius: 16px; box-shadow: 0 1px 0 rgba(15,42,46,.03), 0 3px 8px rgba(15,42,46,.04); }
[class*="st-key-tile_plain_"] button > div, [class*="st-key-tile_plain_"] button > div > span { flex-direction: row !important; align-items: center;
  justify-content: flex-start; gap: 12px; width: auto; flex: 1; }
[class*="st-key-tile_plain_"] button [data-testid="stIconMaterial"] { width: 38px; height: 38px; min-width: 38px; font-size: 1.3rem !important; }
[class*="st-key-tile_plain_"] button::after { content: ""; width: 9px; height: 9px; border-right: 2.5px solid #8FA8A6; border-top: 2.5px solid #8FA8A6; transform: rotate(45deg); margin: 0 6px 0 8px; flex: none; }
.tilehead { font-size: 1.05rem; font-weight: 700; color: var(--ink); margin: 1.2rem 0 .55rem; }

/* ---- resident hero ---- */
.hero { background: var(--ink); color: #fff; border-radius: 24px; padding: 18px 16px 16px; margin: 6px 0 12px; box-shadow: 0 12px 28px rgba(15,42,46,.20); }
.hero .row { display: flex; gap: 16px; align-items: center; }
.hero img { width: 92px; height: 92px; border-radius: 50%; border: 3px solid rgba(255,255,255,.92); flex: none; }
.hero .nm { font-size: 1.9rem; font-weight: 800; line-height: 1.08; letter-spacing: -.015em; color: #fff; }
.hero .rm { color: #A9C4C3; margin-top: 4px; }
.hero .chips { margin-top: 14px; }
.panelhead { display: flex; align-items: center; gap: 12px; margin: 6px 0 10px; }
.panelhead .disc { width: 42px; height: 42px; border-radius: 50%; background: var(--teal-bg); color: var(--teal-d); display: flex; align-items: center; justify-content: center; }
.panelhead .disc svg { width: 22px; height: 22px; }
.panelhead .t { font-size: 1.45rem; font-weight: 800; letter-spacing: -.01em; }
/* residents list */
.hello { font-size: 1.9rem; font-weight: 800; letter-spacing: -.02em; line-height: 1.1; margin: 8px 0 4px; }
.hellosub { color: var(--ink-2); margin-bottom: 10px; }
[class*="st-key-res_"] { box-shadow: 0 1px 0 rgba(15,42,46,.04), 0 8px 18px rgba(15,42,46,.06); border-radius: 22px; }
[class*="st-key-open_"] button { border: none; background: var(--teal-bg); color: var(--teal-d); min-height: 2.9rem; border-radius: 14px; }
[class*="st-key-open_"] button:hover { background: #CBE8E5; }
[class*="st-key-open_"] button p { color: var(--teal-d); }
[class*="st-key-open_"] button::after { content: ""; width: 9px; height: 9px; border-right: 2.5px solid var(--teal-d); border-top: 2.5px solid var(--teal-d); transform: rotate(45deg); margin-left: 10px; flex: none; }
[class*="st-key-top_"] button { border-radius: 16px; min-height: 3.2rem; }
.st-key-quick button, [class*="st-key-nf_"] button { min-height: 2.6rem; background: #E8F2F1; border-color: #C5DEDC; }
.st-key-quick button p, [class*="st-key-nf_"] button p { font-size: .95rem; }

/* ---- inputs ---- */
[data-testid="stChatInput"] { border-radius: 16px; }
[data-testid="stAudioInput"] { border-radius: 16px; }
.stSelectbox [data-baseweb="select"] > div { border-radius: 12px; background: var(--card); border-color: var(--line); min-height: 3rem; }
[data-testid="stExpander"] { border-radius: 14px; border-color: var(--line); background: var(--card); }
[data-testid="stSegmentedControl"] button, [data-testid="stSegmentedControl"] [role="radio"] { font-weight: 700; }

/* ---- RN screen ---- */
.rnhead { font-size:.8rem; font-weight:800; letter-spacing:.02em; border-radius:999px; padding:3px 10px; display:inline-block; }
.rnhead.urgent { background: var(--red-bg); color: var(--red); }
.rnhead.check { background: var(--amber-bg); color: var(--amber); }
.sec { font-size:.95rem; font-weight:700; color: var(--ink-2); margin: 14px 2px 6px; }


/* ---- shift handover board ---- */
.holine { display:flex; gap:10px; align-items:flex-start; margin:6px 0; line-height:1.4; }
.holine .ic { flex:none; width:28px; height:28px; border-radius:50%; background: var(--teal-bg); color: var(--teal-d); display:flex; align-items:center; justify-content:center; }
.holine .ic svg { width:16px; height:16px; }
.holine .lb { font-weight:700; }
.hoshift { font-size:.95rem; font-weight:700; color: var(--teal-d); margin: 14px 0 6px; padding-bottom:4px; border-bottom: 1px solid var(--line); }
.hoev { padding: 7px 0 7px 12px; border-left: 3px solid var(--line); margin: 6px 0; line-height: 1.45; }
.hoev.flag { border-left-color: #D89B1D; background: #FFFAEC; border-radius: 0 10px 10px 0; }
.hoev .t { font-weight: 800; }
.hoev .who { color: var(--ink-2); }
.hoev .chips { margin-top: 5px; }
.hoempty { color: var(--ink-2); font-style: italic; margin: 4px 0 4px 12px; }


/* ---- photo grid and care chart: an HTML tile with an invisible button laid over it ---- */
[class*="st-key-pt_"], [class*="st-key-ct_"] { position: relative; }
[class*="st-key-pt_"] [data-testid="stElementContainer"]:has(button), [class*="st-key-ct_"] [data-testid="stElementContainer"]:has(button) {
  position: absolute !important; inset: 0 !important; width: 100% !important; height: 100% !important; z-index: 3; }
[class*="st-key-pt_"] [data-testid="stElementContainer"]:has(button) > div, [class*="st-key-ct_"] [data-testid="stElementContainer"]:has(button) > div,
[class*="st-key-pt_"] [data-testid="stButton"], [class*="st-key-ct_"] [data-testid="stButton"] { width: 100% !important; height: 100% !important; }
[class*="st-key-pt_"] button, [class*="st-key-ct_"] button { width: 100% !important; height: 100% !important; min-height: 0; opacity: 0; cursor: pointer; }
[class*="st-key-grid_"] [data-testid="stHorizontalBlock"] { flex-direction: row !important; flex-wrap: nowrap; gap: .6rem; }
[class*="st-key-grid_"] [data-testid="stColumn"] { min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }
[class*="st-key-grid_"] [data-testid="stVerticalBlock"] { gap: 0; }
[class*="st-key-grid_"] > [data-testid="stVerticalBlock"] { gap: .6rem; }
.stApp .msr { font-family: 'Material Symbols Rounded' !important; font-weight: 400; font-style: normal; line-height: 1; letter-spacing: normal;
  text-transform: none; white-space: nowrap; -webkit-font-feature-settings: 'liga'; font-feature-settings: 'liga'; display: inline-block; }
.pt { background: #fff; border: 1px solid #DCE6E4; border-radius: 18px; padding: 8px 8px 10px; text-align: center;
  box-shadow: 0 1px 0 rgba(15,42,46,.04), 0 6px 14px rgba(15,42,46,.06); }
.pt .ph { position: relative; }
.pt img { width: 100%; aspect-ratio: 1/1; border-radius: 14px; object-fit: cover; display: block; background: #E7EEED; }
.pt .pn { font-weight: 800; font-size: 1.02rem; margin-top: 7px; line-height: 1.15; }
.pt .pr { font-size: .85rem; color: var(--ink-2); font-weight: 700; }
.pt .bd { position: absolute; top: -4px; right: -4px; min-width: 22px; height: 22px; border-radius: 999px; font-size: .78rem; font-weight: 800;
  display: flex; align-items: center; justify-content: center; color: #fff; border: 2px solid #fff; padding: 0 5px; }
.pt .bd.info { background: #2B6CB0; } .pt .bd.due { background: #D89B1D; right: auto; left: -4px; top: auto; bottom: -4px; }
.pt .bd.notes { background: #B3261E; top: auto; bottom: -4px; }
.pt .flag { position: absolute; top: 4px; left: 4px; width: 24px; height: 24px; border-radius: 50%; display:flex; align-items:center; justify-content:center; border: 2px solid #fff; }
.pt .flag .msr { font-size: 15px; color: #fff; }
.pt .flag.High { background: #B3261E; } .pt .flag.Medium { background: #D89B1D; }
.sumrow { display: flex; gap: .6rem; margin: 4px 0 10px; }
.sum { flex: 1; border-radius: 16px; padding: 10px 12px; background: #fff; border: 1px solid #DCE6E4; }
.sum .k { font-size: .85rem; color: var(--ink-2); font-weight: 700; }
.sum .v { font-size: 1.3rem; font-weight: 800; line-height: 1.2; }
.sum .s { font-size: .8rem; color: var(--ink-2); }
.sum.warn { background: #FDECEA; border-color: #F2B8B3; } .sum.warn .v, .sum.warn .k { color: #8E2A1F; }
.sum.ok { background: #E1F3E8; border-color: #B4DEC2; } .sum.ok .v { color: #1F6B3E; }
.ct { border-radius: 16px; padding: 8px 4px 9px; text-align: center; background: #fff; border: 1px solid #DCE6E4; min-height: 7.2rem;
  display: flex; flex-direction: column; align-items: center; gap: 3px; box-shadow: 0 1px 0 rgba(15,42,46,.03), 0 4px 10px rgba(15,42,46,.05); }
.ct .tm { font-weight: 800; font-size: .92rem; display: flex; align-items: center; gap: 3px; }
.ct .tm .msr { font-size: 16px; }
.ct .ic { font-size: 34px; color: #55706F; margin: 2px 0; }
.ct .lb { font-size: .85rem; font-weight: 700; line-height: 1.15; }
.ct .vl { font-size: .76rem; font-weight: 700; color: var(--ink-2); line-height: 1.1; }
.ct.done { background: #D3F0DA; border-color: #A3D8B0; } .ct.done .ic, .ct.done .tm { color: #1F6B3E; } .ct.done .vl { color: #1F6B3E; }
.ct.due { background: #FFF4D6; border: 2px solid #D89B1D; } .ct.due .tm { color: #7A4B00; }
.ct.overdue { background: #FDECEA; border: 2px solid #B3261E; } .ct.overdue .tm, .ct.overdue .ic { color: #8E2A1F; }
.ct.missed { background: #fff; } .ct.missed .tm { color: #8E2A1F; } .ct.missed .ic, .ct.missed .lb { opacity: .75; }
.ct.later .tm, .ct.later .ic { opacity: .85; }
.ct.rec { min-height: 6.4rem; justify-content: center; }
.ct.rec .lb { font-size: .86rem; }
.ct.rec.sel { background: #D7EFEC; border: 2px solid #0E7C7B; } .ct.rec.sel .ic, .ct.rec.sel .lb { color: #0A5F5E; }
.ct.rec.check .ic { color: #8A5A00; } .ct.rec.urgent .ic { color: #B3261E; }
.ct.rec .okmark { position: absolute; top: 5px; right: 6px; color: #0E7C7B; font-size: 20px; }
.ct.rec { position: relative; }

@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
</style>
"""

LOGO = (
    '<svg class="mark" viewBox="0 0 40 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
    '<rect width="40" height="40" rx="11" fill="#0E7C7B"/>'
    '<path d="M11 12.5h18a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H21l-5.5 4.5V26.5H11a3 3 0 0 1-3-3v-8a3 3 0 0 1 3-3z" fill="#fff"/>'
    '<path d="M16 19.6l3 3 5.5-6" fill="none" stroke="#0E7C7B" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>"
)


def inject_css():
    st.markdown(CSS, unsafe_allow_html=True)


def topbar(sub):
    st.markdown(
        f'<div class="topbar">{LOGO}<div><div class="nm">CareAsk</div><div class="sub">{html.escape(sub)}</div></div>'
        '<div class="demo">Demo · fictional data</div></div>',
        unsafe_allow_html=True,
    )


def avatar_svg(look):
    back = look["hair"] if look["long"] else look["bg"]
    stroke = "#8A8A8A" if look["long"] else look["bg"]
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" fill="{look["bg"]}"/>'
        f'<path d="M8 100 C8 76 28 68 50 68 C72 68 92 76 92 100 Z" fill="{look["cloth"]}"/>'
        f'<rect x="43" y="56" width="14" height="16" fill="{look["skin"]}"/>'
        f'<path d="M27 44 C22 74 28 82 35 82 L35 44 Z" fill="{back}" stroke="{stroke}" stroke-width="0.8"/>'
        f'<path d="M73 44 C78 74 72 82 65 82 L65 44 Z" fill="{back}" stroke="{stroke}" stroke-width="0.8"/>'
        f'<ellipse cx="50" cy="42" rx="18" ry="21" fill="{look["skin"]}"/>'
        f'<path d="M31 40 C29 16 71 16 69 40 C66 29 34 29 31 40 Z" fill="{look["hair"]}" stroke="#8A8A8A" stroke-width="0.8"/>'
        '<circle cx="43" cy="43" r="1.9" fill="#2B2B2B"/><circle cx="57" cy="43" r="1.9" fill="#2B2B2B"/>'
        '<path d="M43 51 Q50 57 57 51" fill="none" stroke="#8A4B3A" stroke-width="1.6" stroke-linecap="round"/>'
        "</svg>"
    )


def avatar_uri(look):
    return "data:image/svg+xml;utf8," + quote(avatar_svg(look))


def falls_pill(risk):
    fg, bg = FALLS_COLOURS[risk]
    return f'<span class="pill" style="color:{fg};background:{bg}">{risk} falls risk</span>'


def short_allergy(text):
    """'Penicillin (drug allergy). No known food allergies.' -> 'Penicillin'. None when there is no allergy."""
    t = (text or "").strip()
    if not t or t.lower().startswith(("none", "no known", "nil")):
        return None
    first = t.split(". ")[0]
    first = first.split("(")[0].strip(" .;,")
    return first[:28] or None


def chips(risk, allergy=None, flags=0, tasks_due=0):
    out = [falls_pill(risk)]
    short = short_allergy(allergy)
    if short:
        out.append(f'<span class="chip allergy">Allergy: {html.escape(short)}</span>')
    if flags:
        out.append(f'<span class="chip warn">{flags} to check in notes</span>')
    if tasks_due:
        out.append(f'<span class="chip warn">{tasks_due} task{"s" if tasks_due != 1 else ""} due</span>')
    return '<div class="chips">' + "".join(out) + "</div>"


def resident_row(r, allergy=None, flags=0, tasks_due=0):
    return (
        f'<div class="rescard"><img src="{avatar_uri(r["look"])}" alt="Fictional photo of {html.escape(r["name"])}">'
        f'<div><div class="nm">{html.escape(r["name"])}</div><div class="rm">Room {html.escape(str(r["room"]))}</div>'
        f"{chips(r['falls'], allergy, flags, tasks_due)}</div></div>"
    )


def resident_head(r, allergy=None, flags=0):
    return (
        f'<div class="hero"><div class="row"><img src="{avatar_uri(r["look"])}" alt="Fictional photo of {html.escape(r["name"])}">'
        f'<div><div class="nm">{html.escape(r["name"])}</div>'
        f'<div class="rm">Room {html.escape(str(r["room"]))}, age {html.escape(str(r["age"]))}</div></div></div>'
        f"{chips(r['falls'], allergy, flags)}</div>"
    )


ICON_PATHS = {
    "voice": '<path d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-3.1A7 7 0 0 0 19 11z"/>',
    "tasks": '<path d="M9 16.2l-3.5-3.5L4 14.2l5 5 11-11-1.5-1.5z"/>',
    "notes": '<path d="M4 4h12l4 4v12H4zm2 2v12h12V9h-4V6zm2 6h8v2H8zm0 4h6v2H8z"/>',
    "plan": '<path d="M6 3h12a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zm2 4v2h8V7zm0 4v2h8v-2zm0 4v2h5v-2z"/>',
}


def panel_head(title, icon="plan"):
    return (f'<div class="panelhead"><div class="disc"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">'
            f'{ICON_PATHS.get(icon, ICON_PATHS["plan"])}</svg></div><div class="t">{html.escape(title)}</div></div>')


def source_row(sources):
    if not sources:
        return ""
    tags = "".join(f'<span class="src">{html.escape(s)}</span>' for s in sources)
    return f'<div class="srcrow"><span class="lbl">Source</span>{tags}</div>'



_HO_ICONS = {
    "food": '<path d="M11 3v8H9V3H7v8H5V3H3v9a3 3 0 0 0 3 3v6h2v-6a3 3 0 0 0 3-3V3zm5 0c-2 2-3 5-3 8h3v10h2V3z"/>',
    "help": '<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm0 2c-3 0-8 1.5-8 4.5V21h16v-2.5c0-3-5-4.5-8-4.5z"/>',
    "walk": '<path d="M13.5 5.5a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM9.8 8.9L7 23h2.1l1.8-8 2.1 2v6h2v-7.5l-2.1-2 .6-3A7.3 7.3 0 0 0 19 13v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1L6 8.3V13h2V9.6z"/>',
}


def _ho_line(icon, label, text):
    return (f'<div class="holine"><span class="ic"><svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">{_HO_ICONS[icon]}</svg></span>'
            f'<div><span class="lb">{html.escape(label)}:</span> {html.escape(text)}</div></div>')


def handover_head(r, allergy, kinds):
    extra = "".join(f'<span class="chip warn">{html.escape(k)}</span>' for k in kinds)
    return (
        f'<div class="rescard hocard"><img src="{avatar_uri(r["look"])}" alt="Fictional photo of {html.escape(r["name"])}">'
        f'<div><div class="nm">{html.escape(r["name"])}</div><div class="rm">Room {html.escape(str(r["room"]))}</div>'
        f"{chips(r['falls'], allergy)}</div></div>"
        + (f'<div class="chips" style="margin:-4px 0 6px"><span class="lbl" style="margin-right:6px">Tell the RN:</span>{extra}</div>' if extra else "")
    )


def handover_body(care, groups):
    parts = []
    if care.get("food"):
        parts.append(_ho_line("food", "Eats and drinks", care["food"]))
    if care.get("meal_help"):
        parts.append(_ho_line("help", "Help at meals", care["meal_help"]))
    if care.get("mobility"):
        parts.append(_ho_line("walk", "Moving", care["mobility"]))
    for g in groups:
        parts.append(f'<div class="hoshift">{html.escape(g["title"])}</div>')
        if not g["notes"]:
            parts.append('<div class="hoempty">Nothing written down.</div>')
        for n in g["notes"]:
            tags = "".join(f'<span class="chip neutral">{html.escape(t)}</span>' for t in n["tags"])
            kinds = "".join(f'<span class="chip warn">{html.escape(k)}</span>' for k in n["kinds"])
            chip_row = f'<div class="chips">{kinds}{tags}</div>' if (tags or kinds) else ""
            parts.append(f'<div class="hoev{" flag" if n["kinds"] else ""}"><span class="t">{html.escape(n["time"])}</span> '
                         f'<span class="who">{html.escape(n["staff"])}</span><br>{html.escape(n["text"])}{chip_row}</div>')
    return "".join(parts)



FLAG_ICON = '<span class="flag {risk}"><span class="msr">flag</span></span>'


def photo_tile(r, allergy=None, due=0, notes=0):
    first = r["name"].split()[0]
    initial = r["name"].split()[-1][0]
    risk = r["falls"]
    flag = FLAG_ICON.format(risk=risk) if risk in ("High", "Medium") else ""
    badges = ""
    if short_allergy(allergy):
        badges += '<span class="bd info">i</span>'
    if due:
        badges += f'<span class="bd due">{due}</span>'
    return (f'<div class="pt"><div class="ph"><img src="{avatar_uri(r["look"])}" alt="Fictional photo of {html.escape(r["name"])}">'
            f'{flag}{badges}</div><div class="pn">{html.escape(first)} {html.escape(initial)}.</div>'
            f'<div class="pr">Room {html.escape(str(r["room"]))}</div></div>')


def chart_summary(fl, meals):
    cls = "warn" if fl["behind"] else ("ok" if fl["had"] >= fl["expected"] and fl["had"] else "")
    note = "Behind: offer a drink" if fl["behind"] else f"Aim {fl['target']} ml a day"
    m_cls = "ok" if meals["due"] and meals["eaten"] >= meals["due"] else ("warn" if meals["due"] > meals["eaten"] and meals["due"] else "")
    return (f'<div class="sumrow"><div class="sum {cls}"><div class="k">Drinks today</div><div class="v">{fl["had"]} ml</div>'
            f'<div class="s">{html.escape(note)}</div></div>'
            f'<div class="sum {m_cls}"><div class="k">Meals recorded</div><div class="v">{meals["eaten"]} of {meals["total"]}</div>'
            f'<div class="s">{meals["due"]} due by now</div></div></div>')


def chart_tile(t):
    state = t["state"]
    check = '<span class="msr">check_circle</span>' if state == "done" else ""
    when = t["done_at"] if state == "done" and t["done_at"] else t["due"]
    vl = f'<div class="vl">{html.escape(t["value"])}</div>' if t["value"] else ""
    return (f'<div class="ct {state}"><div class="tm">{check}{html.escape(when)}</div>'
            f'<span class="msr ic">{html.escape(t["icon"])}</span><div class="lb">{html.escape(t["label"])}</div>{vl}</div>')


def record_tile(t, selected):
    cls = "rec " + (t.get("level", "") or "") + (" sel" if selected else "")
    mark = '<span class="msr okmark">check_circle</span>' if selected else ""
    return (f'<div class="ct {cls.strip()}">{mark}<span class="msr ic">{html.escape(t["icon"])}</span>'
            f'<div class="lb">{html.escape(t["label"])}</div></div>')
