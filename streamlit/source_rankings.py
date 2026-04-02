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
    """Generates a polished chart with value-based conditional coloring."""

    # 1. Define your thresholds and colors
    def get_color(val):
        if val < 30:
            return "#2ecc71"  # Soft Green
        elif val < 50:
            return "#f1c40f"  # Soft Yellow/Gold
        else:
            return "#e74c3c"  # Soft Red

    # Apply color logic to the dataframe
    chart_df = df.sort_values(by="unreliability_pct", ascending=True).copy()
    chart_df["bar_color"] = chart_df["unreliability_pct"].apply(get_color)

    fig = px.bar(
        chart_df,
        x="unreliability_pct",
        y="source_type_name",
        orientation='h',
        title="<b>Relative Unreliability by Source</b>",
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
        # USE THE NEW COLOR COLUMN
        color="bar_color",
        color_discrete_map="identity"  # This tells Plotly to use the hex codes directly
    )

    fig.update_traces(
        width=0.6,
        marker=dict(
            line=dict(width=0),
            cornerradius=10  # Note: Ensure Plotly version >= 5.20.0
        )
    )

    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter, sans-serif", size=13, color="#444"),
        # Darker gray for professionalism
        title_font=dict(size=20, color="#2c3e50"),
        xaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor='rgba(200, 200, 200, 0.2)',
            zeroline=False,
            ticksuffix="%"
        ),
        yaxis=dict(showgrid=False, zeroline=False),
        height=500,
        margin=dict(l=20, r=40, t=80, b=40),
        showlegend=False  # Hide legend since colors are self-explanatory
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
                    if row['unreliability_pct'] >= 50:
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
    st.header("News Source Unreliability Rankings")
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
