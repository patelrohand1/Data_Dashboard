import streamlit as st
import plotly.express as px
import pandas as pd
from data_engine import fetch_sector_data, fetch_yield_curve,fetch_key_economic_prints
# 1. Page Configuration
st.set_page_config(page_title="Global Macro Terminal", layout="wide")
st.title("🌍 Global Macro & Market Outlook Terminal")

# Styling function for Tear Sheets
def color_momentum(val):
    if pd.isna(val):
        return ''
    color = 'rgba(255, 75, 75, 0.2)' if val < 0 else 'rgba(75, 255, 75, 0.2)'
    return f'background-color: {color}'

# 2. Workspace Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Equities", "🏛️ Rates & Bonds", "💱 FX Markets", "🛢️ Commodities", "📊 Macro Fundamentals"])

# --- TAB 1: EQUITIES ---
with tab1:
    st.header("Global Equities Tear Sheet")
    with st.spinner("Loading Equities..."):
        eq_matrix = fetch_sector_data("Equities")
        st.dataframe(
            eq_matrix.style.map(color_momentum, subset=['1D %', '1W %', '1M %']).format("{:.2f}"),
            use_container_width=True
        )

# --- TAB 2: RATES & YIELD CURVE ---
with tab2:
    st.header("Global Rates & Yield Curve")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Yield Curve Matrix")
        with st.spinner("Loading Rates..."):
            curve_df = fetch_yield_curve()
            st.dataframe(curve_df[['Tenor', 'Yield (%)']].set_index('Tenor').style.format("{:.2f}%"), use_container_width=True)
            
            # Quick Spread Calc
            spread_10y2y = curve_df.loc[curve_df['Tenor']=='10Y', 'Yield (%)'].values[0] - curve_df.loc[curve_df['Tenor']=='2Y', 'Yield (%)'].values[0]
            st.metric("10Y-2Y Spread", f"{spread_10y2y*100:.1f} bps", help="Negative indicates an inverted yield curve (recession warning).")

    with col2:
        st.subheader("US Sovereign Yield Curve Trajectory")
        fig_curve = px.line(
            curve_df, x="Years", y="Yield (%)", text="Tenor", markers=True,
            title="Real-Time US Treasury Term Structure"
        )
        fig_curve.update_traces(textposition="top center", line=dict(width=3, color='royalblue'))
        fig_curve.update_layout(xaxis_title="Maturity (Years)", yaxis_title="Yield (%)", height=450)
        st.plotly_chart(fig_curve, use_container_width=True)

# --- TAB 3: FX MARKETS ---
with tab3:
    st.header("Foreign Exchange Tear Sheet")
    with st.spinner("Loading FX..."):
        fx_matrix = fetch_sector_data("FX")
        st.dataframe(
            fx_matrix.style.map(color_momentum, subset=['1D %', '1W %', '1M %']).format("{:.4f}", subset=['Last Price']).format("{:.2f}", subset=['1D %', '1W %', '1M %']),
            use_container_width=True
        )

# --- TAB 4: COMMODITIES ---
with tab4:
    st.header("Commodities Tear Sheet")
    with st.spinner("Loading Commodities..."):
        cmd_matrix = fetch_sector_data("Commodities")
        st.dataframe(
            cmd_matrix.style.map(color_momentum, subset=['1D %', '1W %', '1M %']).format("{:.2f}"),
            use_container_width=True
        )
# --- TAB 5: MACRO FUNDAMENTALS ---
with tab5:
    st.header("Key Economic Prints (US Macro Engine)")
    st.markdown("Autonomously tracking the latest releases from the Bureau of Economic Analysis and Bureau of Labor Statistics.")
    
    col_macro1, col_macro2 = st.columns([2, 1])
    
    with col_macro1:
        with st.spinner("Compiling Macroeconomic Releases..."):
            macro_df = fetch_key_economic_prints()
            
            if not macro_df.empty:
                # Custom styling to highlight acceleration vs deceleration
                def color_macro_shift(val):
                    if pd.isna(val) or val == 0:
                        return ''
                    # Green for accelerating metrics, Red for decelerating metrics
                    color = 'rgba(75, 255, 75, 0.2)' if val > 0 else 'rgba(255, 75, 75, 0.2)'
                    return f'background-color: {color}'

                st.dataframe(
                    macro_df.style.map(color_macro_shift, subset=['Change (Net)'])
                    .format("{:.2f}", subset=['Latest Print', 'Previous Print', 'Change (Net)']),
                    use_container_width=True,
                    height=300
                )
            else:
                st.write("Awaiting Macro Data...")

    with col_macro2:
        st.markdown("### 💡 Desk Translation")
        st.info("""
        **Reading the Matrix:**
        * **Green Change:** The metric is *accelerating* relative to the previous period (e.g., inflation is running hotter, or job growth is expanding).
        * **Red Change:** The metric is *decelerating* (e.g., GDP is slowing down, or unemployment is dropping).
        """)
        
        if not macro_df.empty:
            # Dynamic highlight based on the latest Core CPI trend
            cpi_change = macro_df.loc["Core CPI (MoM %)", "Change (Net)"]
            if cpi_change > 0:
                st.error(f"🚨 **Inflation Alert:** Core CPI MoM is accelerating by +{cpi_change:.2f}%. Watch for hawkish Fed repricing across the short-end of the yield curve.")
            elif cpi_change < 0:
                st.success(f"📉 **Disinflation Trend:** Core CPI MoM is decelerating by {cpi_change:.2f}%. Supports risk-on equity environments and curve steepening.")
