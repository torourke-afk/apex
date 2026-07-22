"""
Operations Command — Signal Deck design system
------------------------------------------------
Approval Queue / Directive Review page.
Two-column layout: left = queue list, right = selected directive detail.
"""
import streamlit as st

from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.components.filter_bar import get_global_filters

# ── Page chrome ──────────────────────────────────────────────────────────
page_chrome(title="Operations Command", category="OPERATIONS")
filters = get_global_filters()

# ── Design tokens ────────────────────────────────────────────────────────
_mono = "'JetBrains Mono',monospace"
_ff = "'Space Grotesk',system-ui,sans-serif"

# ── Queue data ───────────────────────────────────────────────────────────
_QUEUE = [
    {
        "id": 0, "tool": "NBD_OPTIMIZER", "conf": 92,
        "title": "Shift $140K from Display → SEM in DMA 602",
        "status": "PENDING", "dot": "var(--cyan)", "risk": "LOW",
        "rationale": (
            "Display CPAs in DMA 602 have risen 34% over the past 3 weeks while SEM conquest "
            "terms maintain a $218 CPA — 41% below display. Reallocating $140K would yield an "
            "estimated 640 additional funded accounts at current conversion rates."
        ),
        "impact": {"savings": "$61K", "timeline": "14 days", "accounts": "+640", "confidence": "92%"},
        "chain": [
            "Pull $140K from Display insertion orders in DMA 602",
            "Create SEM campaign mirrors for checking conquest",
            "Set bid ceiling at $4.20 CPC (non-branded)",
            "Monitor CPA daily for 14-day evaluation window",
        ],
    },
    {
        "id": 1, "tool": "CREATIVE_ROTATE", "conf": 87,
        "title": "Pause fatigued Savings Hero across Social",
        "status": "PENDING", "dot": "var(--amber)", "risk": "MEDIUM",
        "rationale": (
            "The Savings Hero creative has been in rotation for 42 days. CTR has declined 28% "
            "from peak, and frequency has reached 4.7× against the target audience. Refreshing "
            "with the pre-approved Q3 variant is projected to recover 15–20% of lost engagement."
        ),
        "impact": {"savings": "$22K", "timeline": "7 days", "accounts": "+180", "confidence": "87%"},
        "chain": [
            "Pause Savings Hero across Meta and TikTok placements",
            "Activate Q3 Savings Variant B (pre-approved)",
            "Set frequency cap to 3× per 7 days",
            "A/B test against Variant C at 20% traffic",
        ],
    },
    {
        "id": 2, "tool": "BID_ADJUST", "conf": 94,
        "title": "Increase SEM bids +12% for checking conquest",
        "status": "APPROVED", "dot": "var(--green)", "risk": "LOW",
        "rationale": (
            "Checking conquest impression share has dropped to 62% as competitor bids have "
            "increased. A 12% bid increase would recover an estimated 8 percentage points of "
            "impression share while keeping CPA within the $290 ceiling."
        ),
        "impact": {"savings": "$0 (investment)", "timeline": "3 days", "accounts": "+310", "confidence": "94%"},
        "chain": [
            "Increase max CPC bids by 12% across checking conquest campaigns",
            "Maintain CPA ceiling at $290",
            "Enable automated bid adjustments within ±5%",
            "Report impression share recovery after 72 hours",
        ],
    },
    {
        "id": 3, "tool": "GEO_REBALANCE", "conf": 78,
        "title": "Reduce Brand TV in DMA 501, redistribute to digital",
        "status": "DEFERRED", "dot": "var(--text3)", "risk": "HIGH",
        "rationale": (
            "Brand TV in DMA 501 (Washington DC) is showing diminishing returns with a 1.2× "
            "ROAS vs. the 3.8× portfolio average. However, brand lift studies show strong aided "
            "awareness gains that may not be captured in direct attribution."
        ),
        "impact": {"savings": "$180K", "timeline": "30 days", "accounts": "+220", "confidence": "78%"},
        "chain": [
            "Reduce Brand TV GRPs in DMA 501 by 40%",
            "Redistribute budget to digital channels (SEM 50%, Social 30%, Display 20%)",
            "Commission brand lift study for baseline",
            "Evaluate awareness impact after 30 days",
        ],
    },
]

# ── Session state ────────────────────────────────────────────────────────
sel = st.session_state.get("ops_selected", 0)

# ── Shared styles ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
@keyframes rise { from { opacity:0; transform:translateY(10px); } to { opacity:1; transform:translateY(0); } }
@media (prefers-reduced-motion: reduce) { * { animation:none !important; transition:none !important; } }
</style>
""", unsafe_allow_html=True)

# ── Status helpers ───────────────────────────────────────────────────────
_STATUS_STYLE = {
    "PENDING":  ("var(--amber)", "rgba(242,177,76,.14)"),
    "APPROVED": ("var(--green)", "rgba(79,216,155,.14)"),
    "DEFERRED": ("var(--text3)", "var(--panel2)"),
}

_RISK_STYLE = {
    "LOW":    ("var(--green)", "rgba(79,216,155,.14)"),
    "MEDIUM": ("var(--amber)", "rgba(242,177,76,.14)"),
    "HIGH":   ("var(--red)",   "rgba(255,92,114,.14)"),
}


def _status_badge(status: str, size: str = "9px") -> str:
    color, bg = _STATUS_STYLE.get(status, ("var(--text3)", "var(--panel2)"))
    return (
        f'<span style="font-family:{_mono};font-size:{size};letter-spacing:.06em;'
        f'font-weight:600;padding:3px 8px;border-radius:6px;color:{color};background:{bg};">'
        f'{status}</span>'
    )


def _risk_badge(risk: str) -> str:
    color, bg = _RISK_STYLE.get(risk, ("var(--text3)", "var(--panel2)"))
    return (
        f'<span style="font-family:{_mono};font-size:9px;letter-spacing:.06em;'
        f'font-weight:600;padding:3px 8px;border-radius:6px;color:{color};background:{bg};">'
        f'{risk} RISK</span>'
    )


# ── Pending count ────────────────────────────────────────────────────────
_n_pending = sum(1 for q in _QUEUE if q["status"] == "PENDING")

# ── Layout ───────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 2])

# ═══════════════════════════════════════════════════════════════════════════
#  LEFT PANEL — Approval Queue
# ═══════════════════════════════════════════════════════════════════════════
with col_left:
    # Build queue items HTML
    _queue_items = ""
    for i, q in enumerate(_QUEUE):
        is_selected = (i == sel)
        left_border = "border-left:3px solid var(--cyan);" if is_selected else "border-left:3px solid transparent;"
        bg = "background:rgba(52,225,212,.04);" if is_selected else ""
        delay = f"{0.06 * (i + 1):.2f}"

        _queue_items += f"""
        <div style="{left_border}{bg}padding:14px 16px;border-bottom:1px solid var(--line);
          animation:rise .4s ease-out {delay}s both;cursor:pointer;">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
            <div style="display:flex;align-items:center;gap:8px;">
              <div style="width:8px;height:8px;border-radius:50%;background:{q['dot']};flex-shrink:0;
                   box-shadow:0 0 6px {q['dot']};"></div>
              <span style="font-family:{_mono};font-size:9px;letter-spacing:.1em;color:var(--text3);">
                {q['tool']}</span>
            </div>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-family:{_mono};font-size:11px;font-weight:500;color:var(--text);">
                {q['conf']}%</span>
              {_status_badge(q['status'])}
            </div>
          </div>
          <div style="font-size:12.5px;font-weight:600;color:var(--text);line-height:1.35;
            padding-left:16px;">{q['title']}</div>
        </div>"""

    # Render the queue panel
    st.markdown(f"""
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
      overflow:hidden;animation:rise .4s ease-out both;font-family:{_ff};color:var(--text);">
      <!-- Header -->
      <div style="display:flex;align-items:center;justify-content:space-between;padding:15px 18px;
        border-bottom:1px solid var(--line);">
        <div style="display:flex;align-items:center;gap:10px;">
          <div style="width:3px;height:15px;background:var(--cyan);border-radius:3px;"></div>
          <span style="font-size:14px;font-weight:600;">Approval Queue</span>
        </div>
        <span style="font-family:{_mono};font-size:9px;letter-spacing:.06em;font-weight:600;
          padding:3px 8px;border-radius:6px;color:var(--amber);background:rgba(242,177,76,.14);">
          {_n_pending} PENDING</span>
      </div>
      <!-- Queue items -->
      {_queue_items}
    </div>
    """, unsafe_allow_html=True)

    # Interactive buttons for selection
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    btn_cols = st.columns(len(_QUEUE))
    for i, q in enumerate(_QUEUE):
        with btn_cols[i]:
            label = f"{'▸ ' if i == sel else ''}{i + 1}"
            if st.button(label, key=f"sel_{i}", use_container_width=True):
                st.session_state["ops_selected"] = i
                st.rerun()

# ═══════════════════════════════════════════════════════════════════════════
#  RIGHT PANEL — Directive Review
# ═══════════════════════════════════════════════════════════════════════════
with col_right:
    d = _QUEUE[sel]

    # Tool chain steps HTML
    _chain_html = ""
    for step_i, step in enumerate(d["chain"]):
        step_delay = f"{0.08 * (step_i + 1):.2f}"
        _chain_html += f"""
        <div style="display:flex;align-items:flex-start;gap:8px;padding:7px 0;
          animation:rise .4s ease-out {step_delay}s both;">
          <span style="font-family:{_mono};font-size:13px;color:var(--cyan);flex-shrink:0;
            line-height:1.4;">›</span>
          <span style="font-family:{_mono};font-size:12px;color:var(--text2);line-height:1.4;">
            {step}</span>
        </div>"""

    # Impact metrics
    imp = d["impact"]

    st.markdown(f"""
    <div style="border-radius:14px;border:1px solid var(--line);background:var(--panel);
      padding:24px;animation:rise .4s ease-out .06s both;font-family:{_ff};color:var(--text);">

      <!-- Top row: status + tool + confidence + risk -->
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;
        flex-wrap:wrap;gap:8px;">
        <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
          <span style="font-family:{_mono};font-size:9px;letter-spacing:.08em;font-weight:600;
            padding:4px 10px;border-radius:6px;color:var(--cyan);
            background:rgba(52,225,212,.12);">{d['tool']}</span>
          <span style="font-family:{_mono};font-size:12px;font-weight:600;color:var(--text);">
            {d['conf']}%</span>
          {_risk_badge(d['risk'])}
        </div>
        {_status_badge(d['status'], '10px')}
      </div>

      <!-- Title -->
      <div style="font-size:19px;font-weight:600;line-height:1.3;margin-bottom:22px;">
        {d['title']}</div>

      <!-- Agent Rationale -->
      <div style="margin-bottom:20px;">
        <div style="font-family:{_mono};font-size:9px;letter-spacing:.12em;color:var(--text3);
          margin-bottom:8px;">AGENT RATIONALE</div>
        <div style="font-size:13.5px;line-height:1.55;color:var(--text2);">
          {d['rationale']}</div>
      </div>

      <!-- Projected Impact card -->
      <div style="border-left:3px solid var(--cyan);border-radius:0 10px 10px 0;
        background:rgba(52,225,212,.04);padding:16px 18px;margin-bottom:20px;
        animation:rise .4s ease-out .12s both;">
        <div style="font-family:{_mono};font-size:9px;letter-spacing:.12em;color:var(--cyan);
          margin-bottom:12px;">PROJECTED IMPACT</div>
        <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(110px,1fr));gap:14px;">
          <div>
            <div style="font-family:{_mono};font-size:9px;letter-spacing:.08em;color:var(--text3);
              margin-bottom:4px;">SAVINGS</div>
            <div style="font-size:20px;font-weight:600;font-family:{_mono};
              font-variant-numeric:tabular-nums;">{imp['savings']}</div>
          </div>
          <div>
            <div style="font-family:{_mono};font-size:9px;letter-spacing:.08em;color:var(--text3);
              margin-bottom:4px;">TIMELINE</div>
            <div style="font-size:20px;font-weight:600;font-family:{_mono};
              font-variant-numeric:tabular-nums;">{imp['timeline']}</div>
          </div>
          <div>
            <div style="font-family:{_mono};font-size:9px;letter-spacing:.08em;color:var(--text3);
              margin-bottom:4px;">EST. ACCOUNTS</div>
            <div style="font-size:20px;font-weight:600;font-family:{_mono};color:var(--green);
              font-variant-numeric:tabular-nums;">{imp['accounts']}</div>
          </div>
          <div>
            <div style="font-family:{_mono};font-size:9px;letter-spacing:.08em;color:var(--text3);
              margin-bottom:4px;">CONFIDENCE</div>
            <div style="font-size:20px;font-weight:600;font-family:{_mono};color:var(--cyan);
              font-variant-numeric:tabular-nums;">{imp['confidence']}</div>
          </div>
        </div>
      </div>

      <!-- Tool Chain -->
      <div style="border-radius:10px;border:1px solid var(--line);padding:16px 18px;
        animation:rise .4s ease-out .18s both;">
        <div style="font-family:{_mono};font-size:9px;letter-spacing:.12em;color:var(--text3);
          margin-bottom:10px;">TOOL CHAIN</div>
        {_chain_html}
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Action buttons ─────────────────────────────────────────────────
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    btn_a, btn_r, btn_d, _ = st.columns([2, 1, 1, 2])
    with btn_a:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0;border-radius:10px;font-weight:600;
          font-size:13px;font-family:{_ff};cursor:pointer;
          background:var(--cyan);color:var(--cyanInk);">
          ✓ Approve &amp; Execute</div>
        """, unsafe_allow_html=True)
    with btn_r:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0;border-radius:10px;font-weight:500;
          font-size:13px;font-family:{_ff};cursor:pointer;
          border:1px solid var(--line2);background:none;color:var(--text2);">
          Reject</div>
        """, unsafe_allow_html=True)
    with btn_d:
        st.markdown(f"""
        <div style="text-align:center;padding:10px 0;border-radius:10px;font-weight:500;
          font-size:13px;font-family:{_ff};cursor:pointer;
          border:1px solid var(--line);background:none;color:var(--text3);">
          Defer</div>
        """, unsafe_allow_html=True)

# ── Chat drawer ─────────────────────────────────────────────────────────
render_chat_drawer(page_key="ops_cmd")
