"""Business overview page — company description and sector context."""

from __future__ import annotations
import streamlit as st

from src.ui.components import section_header


def render(company: dict, sector_config: dict) -> None:
    section_header("Business Overview", "Company profile and sector context")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Company Information")
        fields = [
            ("Company Name", company.get("company_name")),
            ("Ticker", company.get("ticker")),
            ("NSE Symbol", company.get("nse_symbol")),
            ("BSE Code", company.get("bse_code")),
            ("ISIN", company.get("isin")),
            ("Sector", company.get("sector")),
            ("Industry", company.get("industry")),
            ("Last Updated", str(company.get("last_updated", ""))[:19]),
        ]
        for label, value in fields:
            if value:
                st.markdown(f"**{label}:** {value}")

    with col2:
        st.markdown("#### Sector Context")
        if sector_config:
            display_name = sector_config.get("display_name", company.get("sector", ""))
            desc = sector_config.get("description", "")
            st.markdown(f"**Sector:** {display_name}")
            if desc:
                st.markdown(f"*{desc}*")

            primary = sector_config.get("primary_metrics", [])
            if primary:
                st.markdown("**Primary metrics for this sector:**")
                st.markdown(", ".join(m.replace("_", " ").title() for m in primary[:8]))

            notes = sector_config.get("sector_notes", [])
            if notes:
                st.markdown("**Sector notes:**")
                for note in notes:
                    st.caption(f"• {note}")
        else:
            st.info("No sector configuration loaded.")
