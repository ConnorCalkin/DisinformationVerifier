import streamlit as st
import pandas as pd
from db_logic import get_source_ratings
import plotly.express as px

st.title("News Source Unreliability Rankings")

# --- Sample Data (Replace with your DB connection) ---
# data = run_query(sql_above)
raw_data = get_source_ratings()
df = pd.DataFrame(raw_data)

st.info("Ranking is based on the percentage of claims marked as **Contradicted** or **Misleading**.")


chart_df = df.sort_values(by="unreliability_pct", ascending=True)

# 2. Create the Horizontal Bar Chart
fig = px.bar(
    chart_df,
    x="unreliability_pct",
    y="source_type_name",
    orientation='h',
    title="Relative Unreliability by Source",
    labels={
        "unreliability_pct": "Unreliability (%)",
        "source_type_name": "News Source"
    },
    # Add custom hover data for extra insight
    hover_data={
        "total_inputs": True,
        "total_contradicted": True,
        "total_misleading": True,
        "unreliability_pct": ":.2f"
    },
    color="unreliability_pct",
    color_continuous_scale="Reds"
)

# 3. Clean up the layout
fig.update_layout(
    yaxis={'categoryorder': 'total ascending'},
    xaxis_range=[0, 100],
    height=500,
    margin=dict(l=20, r=20, t=40, b=20),
    coloraxis_showscale=False,
    showlegend=False
)

fig.update_traces(width=0.3)

# 4. Display in Streamlit
st.plotly_chart(fig, width='stretch')

with st.expander("Detailed Rankings and Insights"):
    for index, row in df.iterrows():
        color = "red" if row['unreliability_pct'] > 70 else "orange"

        with st.expander(f"#{index+1} {row['source_type_name']} — {row['unreliability_pct']}% Unreliable"):
            col1, col2 = st.columns([2, 1])

            with col1:
                st.write(
                    f"**Overall Insight:** This source has had **{row['total_inputs']}** claims analyzed.")
                if row['unreliability_pct'] > 80:
                    st.error(
                        "⚠️ **High Risk:** The vast majority of shared content from this source is factually incorrect.")
                else:
                    st.warning(
                        "⚡ **Caution:** This source frequently mixes factual data with misleading context.")

            with col2:
                st.progress(float(row['unreliability_pct']) / 100)
                st.metric("Failure Rate", f"{row['unreliability_pct']}%")

# --- Overall Summary Statistics ---
st.divider()
st.subheader("Global Database Insights")
avg_fail = df['unreliability_pct'].mean()
st.write(
    f"Across the top 10 flagged sources, the average rate of misinformation is **{avg_fail:.1f}%**.")
