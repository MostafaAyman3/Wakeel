"""
Draw the M3 Customer Support Agent system architecture as a PNG image.

Renders the full module: API layer → LangGraph pipeline (8 nodes with
conditional routers) → tools/data layer → PostgreSQL, plus the audit trail
and review-action endpoints.

Usage:
    python scripts/draw_m3_architecture.py
Output:
    docs/architecture/m3_system_architecture.png
"""

from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import matplotlib.pyplot as plt

# ── Palette ──────────────────────────────────────────────────────────────────
C_API      = "#2563eb"   # blue
C_GRAPH    = "#7c3aed"   # purple
C_NODE     = "#0ea5e9"   # sky
C_NODE_S2  = "#14b8a6"   # teal  (Sprint 2)
C_NODE_S3  = "#f59e0b"   # amber (Sprint 3)
C_NODE_S4  = "#ef4444"   # red   (Sprint 4)
C_TOOL     = "#10b981"   # green
C_DB       = "#64748b"   # slate
C_AUDIT    = "#db2777"   # pink
C_ROUTER   = "#fbbf24"   # yellow (decision)
C_BG       = "#f8fafc"
C_TEXT     = "#0f172a"

fig, ax = plt.subplots(figsize=(18, 12))
fig.patch.set_facecolor("white")
ax.set_facecolor(C_BG)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, text, color, *, fc=None, fontsize=10, bold=True, text_color="white"):
    """Draw a rounded box with centered text. Returns (cx, cy) center."""
    fc = fc or color
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.3,rounding_size=0.8",
        linewidth=1.5, edgecolor=color, facecolor=fc, alpha=0.95, zorder=2,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2, y + h / 2, text,
        ha="center", va="center", fontsize=fontsize,
        fontweight="bold" if bold else "normal",
        color=text_color, zorder=3, wrap=True,
    )
    return (x + w / 2, y + h / 2)


def diamond(x, y, w, h, text, color):
    """Draw a decision diamond. Returns center."""
    cx, cy = x + w / 2, y + h / 2
    pts = [(cx, y + h), (x + w, cy), (cx, y), (x, cy)]
    poly = mpatches.Polygon(pts, closed=True, linewidth=1.5,
                            edgecolor=color, facecolor=color, alpha=0.95, zorder=2)
    ax.add_patch(poly)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=8.5,
            fontweight="bold", color=C_TEXT, zorder=3)
    return (cx, cy)


def arrow(p1, p2, color="#334155", style="-", lw=1.6, label=None,
          label_color="#334155", rad=0.0, label_dx=0, label_dy=0):
    a = FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=16,
        linewidth=lw, color=color, zorder=1,
        connectionstyle=f"arc3,rad={rad}", linestyle=style,
    )
    ax.add_patch(a)
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + label_dx, (p1[1] + p2[1]) / 2 + label_dy
        ax.text(mx, my, label, ha="center", va="center", fontsize=8,
                color=label_color, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.85),
                zorder=4)


def band(y, h, label, color):
    """Horizontal layer band on the left."""
    ax.add_patch(plt.Rectangle((0.5, y), 99, h, facecolor=color, alpha=0.06,
                               edgecolor="none", zorder=0))
    ax.text(1.4, y + h - 1.4, label, ha="left", va="top", fontsize=10,
            fontweight="bold", color=color, alpha=0.8, rotation=0, zorder=1)


# ── Title ────────────────────────────────────────────────────────────────────
ax.text(50, 98, "M3 — Customer Support Agent · System Architecture",
        ha="center", va="top", fontsize=18, fontweight="bold", color=C_TEXT)
ax.text(50, 94.5, "FastAPI  →  LangGraph (8 nodes)  →  Tools / Data  →  PostgreSQL   |   + Audit Trail",
        ha="center", va="top", fontsize=10.5, color="#475569")

# ── Layer bands ──────────────────────────────────────────────────────────────
band(86, 7,  "CLIENT / API",   C_API)
band(40, 45, "ORCHESTRATION · LangGraph", C_GRAPH)
band(20, 19, "TOOLS / DATA",   C_TOOL)
band(2,  17, "PERSISTENCE",    C_DB)

# ── Client + API ─────────────────────────────────────────────────────────────
customer = box(4, 88, 16, 4.5, "Customer (AR / EN)", C_API, fontsize=10)
api = box(28, 87.5, 30, 5.5,
          "FastAPI  /api/v1/support\nm3_support.py  ·  JWT auth", C_API, fontsize=10)
reviews = box(64, 87.5, 32, 5.5,
              "Review endpoints\n/approve · /reject · /escalate", C_API,
              fc="#3b82f6", fontsize=9.5)

# ── Graph entry ──────────────────────────────────────────────────────────────
graph_hdr = box(28, 80, 44, 4,
                "support_graph  ·  M3State (TypedDict, partial updates)",
                C_GRAPH, fontsize=9.5)

# ── Pipeline nodes ───────────────────────────────────────────────────────────
n_input = box(6,  72, 20, 5, "1 · InputParser\nGPT-4o-mini + regex", C_NODE, fontsize=9)
n_fetch = box(6,  63, 20, 5, "2 · DataFetcher\n4 sources · parallel", C_NODE, fontsize=9)
n_comp  = box(6,  54, 20, 5, "3 · CompletenessCheck\nscore 0 / 0.5 / 1.0", C_NODE, fontsize=9)

# router 1
r1 = diamond(31, 53.5, 13, 6, "escalation_\nneeded?", C_ROUTER)

n_class = box(50, 70, 20, 5, "4 · IssueClassifier\nGPT-4o-mini (S2)", C_NODE_S2, fontsize=9)
n_ctx   = box(50, 61, 20, 5, "5 · ContextBuilder\nstructured ctx (S2)", C_NODE_S2, fontsize=9)
n_resp  = box(50, 52, 20, 5, "6 · ResponseGenerator\nGPT-4o · 3 tiers (S3)", C_NODE_S3, fontsize=9)

n_gate  = box(50, 43, 20, 5, "7 · HumanReviewGate\nrisk rules (S4)", C_NODE_S4, fontsize=9)

# router 2
r2 = diamond(74, 42.5, 13, 6, "escalate?", C_ROUTER)

n_esc   = box(50, 33.5, 20, 5, "8 · EscalationNode\nsummary + audit (S4)", C_NODE_S4, fontsize=9)

end_ok  = box(6, 43.5, 20, 4.5, "END → SupportResponse", C_GRAPH, fc="#8b5cf6", fontsize=9)

# ── Tools / data layer ───────────────────────────────────────────────────────
t_inv  = box(5,  29, 20, 5, "invoice_fetcher_tool\n(REAL)", C_TOOL, fontsize=9)
t_mock = box(28, 29, 24, 5, "mock_data_tool\norder · shipping · history", C_TOOL, fontsize=9)
t_repo = box(55, 29, 20, 5, "m3_repository\nreusable queries", C_TOOL, fontsize=9)
svc    = box(78, 29, 18, 5, "human_review_service\naudit_service", C_AUDIT, fc="#ec4899", fontsize=8.5)

# ── Persistence ──────────────────────────────────────────────────────────────
db = box(8, 5, 56, 9,
         "PostgreSQL / Supabase  (SELECT-only for fetchers)\n"
         "invoices · customers · orders · shipments · customer_interactions",
         C_DB, fontsize=10)
audit_db = box(70, 5, 26, 9,
               "audit_log\napproved / rejected / escalated",
               C_AUDIT, fc="#be185d", fontsize=9.5)

# ── Arrows: client/API ──────────────────────────────────────────────────────
arrow(customer, (28, 90.2))
arrow((58, 90.2), (64, 90.2))
arrow((43, 87.5), (45, 84), label="build_initial_state()", label_dy=0.3)
arrow((50, 80), (50, 77.2))  # graph hdr → (down into nodes region)
arrow((16, 80), n_input, rad=-0.1)

# ── Arrows: linear pipeline ─────────────────────────────────────────────────
arrow(n_input, n_fetch)
arrow(n_fetch, n_comp)
arrow(n_comp, (37.5, 56.5), rad=0.0)            # → router 1

# router 1 branches
arrow((44, 56.5), (50, 72.5), label="classify", label_color="#92400e", rad=0.1)
arrow((37.5, 53.5), (60, 57.2), label="escalate", label_color="#92400e", rad=-0.25)

arrow(n_class, n_ctx)
arrow(n_ctx, n_resp)
arrow(n_resp, n_gate)
arrow(n_gate, (80.5, 45.5))                     # → router 2

# router 2 branches
arrow((80.5, 42.5), (60, 38.5), label="escalate", label_color="#92400e", rad=0.2)
arrow((80.5, 42.5), (80.5, 12), label="end →", label_color="#92400e", rad=0.0, label_dy=0)
arrow(n_esc, (16, 38), label="final_response", rad=0.1, label_dy=0.4)
arrow((50, 43), end_ok, rad=0.0)                # gate end path → END (review_required)
arrow(end_ok, (43, 85.5), color="#8b5cf6", style="--", rad=-0.3, label="JSON")

# ── Arrows: nodes → tools/data ──────────────────────────────────────────────
arrow((16, 63), t_inv, color="#15803d", rad=0.0)
arrow((16, 63), (34, 34), color="#15803d", rad=-0.15)
arrow(n_esc, svc, color="#be185d", style="--", rad=-0.1, label="log_decision()", label_dy=0.5)
arrow(reviews, svc, color="#be185d", style="--", rad=-0.2)

# ── Arrows: tools → DB ───────────────────────────────────────────────────────
arrow(t_inv, (24, 14), color="#475569")
arrow(t_mock, (38, 14), color="#475569")
arrow(t_repo, (52, 14), color="#475569")
arrow(svc, audit_db, color="#be185d")

# ── Legend ───────────────────────────────────────────────────────────────────
legend_items = [
    ("Sprint 1 node", C_NODE),
    ("Sprint 2 node", C_NODE_S2),
    ("Sprint 3 node", C_NODE_S3),
    ("Sprint 4 node", C_NODE_S4),
    ("Decision router", C_ROUTER),
    ("Tools / Data", C_TOOL),
    ("Audit", C_AUDIT),
]
lx = 2.0
for i, (label, color) in enumerate(legend_items):
    yy = 18.5 - i * 0.0  # single row
    ax.add_patch(plt.Rectangle((lx, 0.3), 1.4, 1.0, facecolor=color, edgecolor="none"))
    ax.text(lx + 1.8, 0.8, label, ha="left", va="center", fontsize=8, color=C_TEXT)
    lx += 1.8 + len(label) * 0.75 + 2

out = os.path.join(os.path.dirname(__file__), "..", "docs", "architecture",
                   "m3_system_architecture.png")
out = os.path.abspath(out)
plt.tight_layout()
plt.savefig(out, dpi=150, bbox_inches="tight", facecolor="white")
print(f"Saved: {out}")
