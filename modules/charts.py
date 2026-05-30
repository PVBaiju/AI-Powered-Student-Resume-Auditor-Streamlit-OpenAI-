from __future__ import annotations
import plotly.graph_objects as go
import pandas as pd

BRAND = {
    "primary": "#0F4C81",
    "accent": "#16A085",
    "warn": "#E67E22",
    "danger": "#C0392B",
    "muted": "#7F8C8D",
    "bg": "#FFFFFF",
    "text": "#1F2933",
}


def _layout(fig: go.Figure, title: str = "", height: int = 360) -> go.Figure:
    fig.update_layout(
        title=dict(text=title, x=0.02, xanchor="left",
                   font=dict(size=16, color=BRAND["text"], family="Inter, Segoe UI, Arial")),
        paper_bgcolor=BRAND["bg"],
        plot_bgcolor=BRAND["bg"],
        font=dict(color=BRAND["text"], family="Inter, Segoe UI, Arial"),
        margin=dict(l=20, r=20, t=50, b=20),
        height=height,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )
    return fig


def gauge(score: int, title: str = "Overall Score") -> go.Figure:
    score = max(0, min(100, int(score or 0)))
    color = BRAND["danger"] if score < 50 else BRAND["warn"] if score < 75 else BRAND["accent"]
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number=dict(suffix="", font=dict(size=44, color=BRAND["text"])),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor=BRAND["muted"]),
            bar=dict(color=color, thickness=0.3),
            bgcolor="#F4F6F8",
            borderwidth=0,
            steps=[
                dict(range=[0, 50], color="#FDECEA"),
                dict(range=[50, 75], color="#FEF5E7"),
                dict(range=[75, 100], color="#E8F8F1"),
            ],
            threshold=dict(line=dict(color=BRAND["text"], width=3), thickness=0.75, value=score),
        ),
    ))
    return _layout(fig, title, height=320)


def radar(scores: dict, title: str = "Score Breakdown") -> go.Figure:
    cats = list(scores.keys())
    vals = [max(0, min(100, int(v or 0))) for v in scores.values()]
    fig = go.Figure(go.Scatterpolar(
        r=vals + [vals[0]],
        theta=cats + [cats[0]],
        fill="toself",
        line=dict(color=BRAND["primary"], width=2),
        fillcolor="rgba(15,76,129,0.25)",
        name="Score",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="#F4F6F8",
            radialaxis=dict(visible=True, range=[0, 100], showline=False, gridcolor="#D7DCE0"),
            angularaxis=dict(gridcolor="#D7DCE0"),
        ),
        showlegend=False,
    )
    return _layout(fig, title, height=380)


def donut_skills(matched: list, missing: list, additional: list, title: str = "Skill Coverage") -> go.Figure:
    labels = ["Matched", "Missing", "Additional"]
    values = [len(matched or []), len(missing or []), len(additional or [])]
    colors = [BRAND["accent"], BRAND["danger"], BRAND["primary"]]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.55,
        marker=dict(colors=colors, line=dict(color="#fff", width=2)),
        textinfo="label+value", textfont=dict(size=13),
    ))
    return _layout(fig, title, height=360)


def bar_compare(df: pd.DataFrame, title: str = "Candidate Comparison") -> go.Figure:
    fig = go.Figure()
    metric_cols = [
        ("overall_score", "Overall", BRAND["primary"]),
        ("jd_match_score", "JD Match", BRAND["accent"]),
        ("experience_score", "Experience", BRAND["warn"]),
        ("quality_score", "Quality", BRAND["muted"]),
    ]
    for col, label, color in metric_cols:
        if col in df.columns:
            fig.add_trace(go.Bar(
                x=df["candidate_name"], y=df[col],
                name=label, marker=dict(color=color),
                text=df[col], textposition="outside",
            ))
    fig.update_layout(barmode="group", yaxis=dict(range=[0, 110], gridcolor="#EAECEE"), xaxis=dict(gridcolor="#EAECEE"))
    return _layout(fig, title, height=420)


def horizontal_ranking(df: pd.DataFrame, title: str = "Final Ranking") -> go.Figure:
    df = df.sort_values("overall_score", ascending=True)
    fig = go.Figure(go.Bar(
        x=df["overall_score"], y=df["candidate_name"],
        orientation="h",
        marker=dict(color=BRAND["primary"]),
        text=df["overall_score"], textposition="outside",
    ))
    fig.update_layout(xaxis=dict(range=[0, 110], gridcolor="#EAECEE"), yaxis=dict(gridcolor="#EAECEE"))
    return _layout(fig, title, height=max(280, 60 * len(df)))


def bulk_histogram(scores: list, title: str = "Score Distribution") -> go.Figure:
    fig = go.Figure(go.Histogram(
        x=scores, nbinsx=10,
        marker=dict(color=BRAND["primary"], line=dict(color="#fff", width=1)),
    ))
    fig.update_layout(xaxis=dict(title="Overall Score", range=[0, 100], gridcolor="#EAECEE"),
                      yaxis=dict(title="Candidates", gridcolor="#EAECEE"))
    return _layout(fig, title, height=340)


def fig_to_png_bytes(fig: go.Figure, width: int = 800, height: int = 400) -> bytes:
    return fig.to_image(format="png", width=width, height=height, scale=2)