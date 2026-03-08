from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import streamlit as st


@dataclass(frozen=True)
class Brand:
    name: str = "Project Colossal"
    tagline: str = "Digital traces → credit → growth"
    motto: str = "Welcome to Project Colossal, \"Financial Identity for the Unseen Economy.\""


def set_page() -> None:
    st.set_page_config(
        page_title="Project Colossal",
        page_icon="🏦",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def load_css() -> None:
    css_path = Path(__file__).resolve().parent.parent / "assets" / "style.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)


def header(brand: Brand = Brand(), right: Optional[str] = None) -> None:
    motto_escaped = brand.motto.replace('"', "&quot;")
    right_html = f"<div class='pc-right'>{right}</div>" if right else ""
    st.markdown(
        f"""
        <div class="pc-header-wrap">
          <div class="pc-header-inner">
            <div class="pc-header">
              <div class="pc-title">{brand.name}</div>
              <div class="pc-motto">{motto_escaped}</div>
            </div>
            {right_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def kpi(label: str, value: str, hint: str = "") -> None:
    st.markdown(
        f"""
        <div class="pc-kpi">
          <div class="pc-kpi-label">{label}</div>
          <div class="pc-kpi-value">{value}</div>
          <div class="pc-kpi-hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "neutral") -> str:
    kind = kind if kind in {"neutral", "good", "warn", "bad"} else "neutral"
    return f"<span class='pc-badge pc-badge-{kind}'>{text}</span>"


def section_header(title: str, icon: str = "", caption: str = "") -> str:
    """HTML for a styled page/section title with optional icon and caption."""
    icon_html = f"<span class='pc-section-icon'>{icon}</span> " if icon else ""
    caption_html = f"<div class='pc-section-caption'>{caption}</div>" if caption else ""
    return f"""
    <div class="pc-section-header">
      <h2 class="pc-section-title">{icon_html}{title}</h2>
      {caption_html}
    </div>
    """


def info_card(title: str, items: list[str], accent: str = "blue") -> str:
    """HTML for a card with a title and bullet list (e.g. next steps, how it works)."""
    li = "".join(f"<li>{item}</li>" for item in items)
    return f"""
    <div class="pc-info-card pc-info-card-{accent}">
      <div class="pc-info-card-title">{title}</div>
      <ul class="pc-info-card-list">{li}</ul>
    </div>
    """


def footer_html() -> str:
    """HTML for app footer."""
    return """
    <div class="pc-footer">
      <span>Project Colossal</span>
      <span class="pc-footer-dot">·</span>
      <span>Digital traces → credit → growth</span>
    </div>
    """

