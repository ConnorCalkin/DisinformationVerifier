import streamlit as st
import pandas as pd
import plotly.express as px
from db_logic import get_source_ratings

# --- 1. Data Logic ---


def load_and_process_data():
    """Fetches raw data and converts to a formatted DataFrame."""
    raw_data = get_source_ratings()
    return pd.DataFrame(raw_data)

# --- 2. Visualization Logic ---


def create_unreliability_chart(df):
    """Generates a polished, professional Plotly horizontal bar chart."""
    # Sort for a clean descending visual flow
    chart_df = df.sort_values(by="unreliability_pct", ascending=True)

    fig = px.bar(
        chart_df,
        x="unreliability_pct",
        y="source_type_name",
        orientation='h',
        title="<b>Relative Unreliability by Source</b>",  # Bold title for hierarchy
        labels={
            "unreliability_pct": "Unreliability (%)",
            "source_type_name": "Source Type"
        },
        hover_data={
            "total_inputs": True,
            "total_contradicted": True,
            "total_misleading": True,
            "unreliability_pct": ":.1f"
        },
        color="unreliability_pct",
        # Use a more sophisticated color scale (Sunset or Plasma looks more modern than just Reds)
        color_continuous_scale=["#FFC1C1", "#531F78"]
    )

    fig.update_traces(
        width=0.5,  # Slightly thicker bars for a "heftier" feel
        marker_line_color='rgba(0,0,0,0)',  # No harsh borders
        marker_pattern_shape="",  # Ensure clean fill
        # This creates the "Rounded" look in modern Plotly
        marker=dict(
            line=dict(width=0),
            # ROUNDED CORNERS (Only available in recent Plotly versions)
            cornerradius=10
        )
    )

    fig.update_layout(
        # 1. CLEAN BACKGROUND
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',

        # 2. TYPOGRAPHY
        font=dict(family="Inter, sans-serif", size=13, color="#444"),
        title_font=dict(size=20, color="#531F78"),

        # 3. AXIS CLEANUP
        xaxis=dict(
            range=[0, 105],  # Extra 5% breathing room for labels
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.2)',  # Very faint grid
            zeroline=False,
            ticksuffix="%"
        ),
        yaxis=dict(
            categoryorder='total ascending',
            showgrid=False,
            zeroline=False
        ),

        # 4. DIMENSIONS & MARGINS
        height=500,
        margin=dict(l=20, r=40, t=80, b=40),
        coloraxis_showscale=False,
        showlegend=False
    )

    return fig

# --- 3. UI Components ---


def display_source_details(df):
    """Renders the expandable detail sections for each news source."""
    with st.expander("Detailed Rankings and Insights"):
        for index, row in df.iterrows():
            with st.expander(f"#{index+1} {row['source_type_name']} — {row['unreliability_pct']}% Unreliable"):
                col1, col2 = st.columns([2, 1])

                with col1:
                    st.write(
                        f"**Overall Insight:** This source has had **{row['total_inputs']}** claims analyzed.")
                    if row['unreliability_pct'] >= 60:
                        st.error(
                            "⚠️ **High Risk:** The vast majority of shared content is factually incorrect.")
                    elif row['unreliability_pct'] >= 30:
                        st.warning(
                            "⚡ **Caution:** This source frequently mixes factual data with misleading context.")
                    else:
                        st.success(
                            "✅ **Relatively Reliable:** A smaller portion of content is flagged as misleading or contradicted.")

                with col2:
                    st.progress(float(row['unreliability_pct']) / 100)
                    st.metric("Failure Rate", f"{row['unreliability_pct']}%")


def display_summary_stats(df):
    """Renders the final summary footer."""
    st.divider()
    st.subheader("Global Database Insights")
    avg_fail = df['unreliability_pct'].mean()
    st.write(
        f"Across the top {len(df)} flagged sources, the average rate of misinformation is **{avg_fail:.1f}%**.")

# --- Main App Execution ---


def main():
    st.set_page_config(page_title="News Rankings", layout="wide")
    st.title("News Source Unreliability Rankings")
    st.info("Ranking is based on the percentage of claims marked as **Contradicted** or **Misleading**.")

    # Data Pipeline
    df = load_and_process_data()

    # Visuals
    fig = create_unreliability_chart(df)
    st.plotly_chart(fig, use_container_width=True)

    # Details & Summary
    display_source_details(df)
    display_summary_stats(df)


if __name__ == "__main__":
    main()
