import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

fig, ax = plt.subplots(figsize=(15, 9))
ax.set_xlim(0, 15); ax.set_ylim(0, 9.4); ax.axis("off")

def box(x, y, w, h, text, fc, ec, fs=10, lw=2, ls="-"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05,rounding_size=0.12",
                                fc=fc, ec=ec, lw=lw, ls=ls))
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, color="#1b1b1b")

def arrow(p, q, color="#333", ls="-", lw=1.8, text=None, tpos=None, fs=8.5, both=False):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<|-|>" if both else "-|>", mutation_scale=15,
                                 color=color, lw=lw, ls=ls, shrinkA=0, shrinkB=0))
    if text:
        tx, ty = tpos if tpos else ((p[0]+q[0])/2, (p[1]+q[1])/2 + 0.18)
        ax.text(tx, ty, text, ha="center", va="bottom", fontsize=fs, color=color)

ax.text(7.5, 9.0, "Student Task Scheduler - DA3 scaled architecture", ha="center", fontsize=16, fontweight="bold")

# --- left: user + frontend
box(0.2, 4.3, 1.7, 1.2, "Student\n(web browser)", "#F5F5F5", "#555")
box(2.4, 4.3, 2.4, 1.2, "Streamlit frontend\n(Streamlit Community Cloud;\nlocalhost:8501 in demo)", "#E8F1FB", "#2E5C99", fs=8.5)
arrow((1.9, 4.9), (2.4, 4.9), both=True)

# --- Docker Compose group
ax.add_patch(Rectangle((5.75, 2.55), 4.2, 5.75, fill=False, ec="#2E7D32", lw=1.8, ls="--"))
ax.text(7.85, 8.05, "Docker Compose host", ha="center", fontsize=10.5, color="#2E7D32", fontweight="bold")
box(6.0, 4.3, 1.55, 1.2, "Nginx LB\nnginx_lb\nhost :8080\n-> container :80", "#EAF7EA", "#2E7D32", fs=8.5)
ys = [6.45, 4.35, 2.8]
for i, y in enumerate(ys, start=1):
    box(8.2, y, 1.55, 1.1, f"backend{i}\nFastAPI + Uvicorn\n:8000", "#E3F4F4", "#00796B", fs=8.5)
    arrow((7.55, 4.9), (8.2, y + 0.55), color="#2E7D32", lw=1.5)
ax.text(7.0, 6.45, "round-robin", fontsize=8, color="#2E7D32", ha="center")
arrow((4.8, 4.9), (6.0, 4.9), text="HTTP :8080", tpos=(5.4, 5.0), both=True)

# --- cloud DB + DA1 hosting
box(11.5, 4.3, 2.8, 1.2, "Supabase PostgreSQL\n(cloud database)\npooler :6543", "#FFF4D6", "#B8860B", fs=9.5)
for y in ys:
    arrow((9.75, y + 0.55), (11.5, 4.9), color="#B8860B", lw=1.3)
ax.text(10.6, 7.05, "SQL over TCP", fontsize=8, color="#B8860B", ha="center")
box(11.5, 6.6, 2.8, 1.1, "Render web service\n(Assignment 1 deployment)\nFastAPI, single instance", "#EDE7F6", "#5E35B1", fs=9)
arrow((12.9, 6.6), (12.9, 5.5), color="#5E35B1", both=True)

# --- cloud bursting (different colour)
BURST = "#C2185B"
ax.add_patch(Rectangle((5.75, 0.35), 4.2, 1.6, fc="#FCE4EC", ec=BURST, lw=2.2, ls="--"))
ax.text(7.85, 1.12, "CLOUD BURSTING\nburst-1..N: extra FastAPI containers\non a public cloud, started when load\ncrosses the threshold",
        ha="center", va="center", fontsize=8.5, color=BURST, fontweight="bold")
arrow((6.78, 4.3), (6.78, 1.95), color=BURST, ls="--", lw=2.0, text="overflow traffic", tpos=(7.35, 3.3))
arrow((9.95, 1.15), (11.9, 4.3), color=BURST, ls="--", lw=1.8)
ax.text(11.4, 2.4, "same Supabase DB", fontsize=8, color=BURST, ha="center")

# --- tools
ax.text(0.3, 3.2, "Tools used", fontsize=10.5, fontweight="bold")
tools = ["Docker Compose (3 backend containers + Nginx)", "Nginx 1.27 (round-robin, failover)",
         "Apache Bench (httpd:2.4) - 1,000-request load test", "Trivy - image vulnerability scan",
         "bcrypt (password hashes) + pyotp (TOTP MFA) + JWT", "GitHub - branch: assignment-3"]
for i, t in enumerate(tools):
    ax.text(0.3, 2.8 - i*0.42, "- " + t, fontsize=8.8)

# --- legend
ax.add_patch(Rectangle((11.0, 0.45), 0.35, 0.25, fc="#FCE4EC", ec=BURST, lw=1.8, ls="--"))
ax.text(11.45, 0.5, "= cloud bursting component (added for peak demand)", fontsize=8.5, color=BURST)

plt.savefig("architecture_diagram_da3.png", dpi=170, bbox_inches="tight", facecolor="white")
print("saved")
