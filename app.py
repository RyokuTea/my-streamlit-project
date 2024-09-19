import streamlit as st
import pandas as pd
import altair as alt
import datetime

data_path = r'/Users/itaka/python/Data/Output/Total/total_summary.csv'

# Load your data
df = pd.read_csv(data_path,
                 dtype={'発注番号': str, '発行区分': int, '数量': int},
                 parse_dates=['発注日', '納入期日'])

# Sidebar selection for granularity (daily or monthly)
view_option = st.sidebar.selectbox('View by', ('日次', '月次'))

# Get the min and max dates from the data
start_date = df['発注日'].min().date()
end_date = df['発注日'].max().date()

# Date range slider
date_range = st.sidebar.slider('表示する期間を入力', min_value=start_date, max_value=end_date,
                               value=(start_date, end_date))

# Convert the date from slider to pandas.Timestamp
start_timestamp = pd.to_datetime(date_range[0])
end_timestamp = pd.to_datetime(date_range[1])

# Filter data by the selected date range
df_filtered = df[(df['発注日'] >= start_timestamp) & (df['発注日'] <= end_timestamp)]

# Group data accordingly
if view_option == '月次':
    df_filtered['month'] = df_filtered['発注日'].dt.to_period('M')
    df_grouped = df_filtered.groupby('month').agg({
        '売上金額JPY': 'sum',
        '仕入金額JPY': 'sum'
    }).reset_index()
    df_grouped['period'] = df_grouped['month'].astype(str)
else:
    df_grouped = df_filtered.groupby('発注日').agg({
        '売上金額JPY': 'sum',
        '仕入金額JPY': 'sum'
    }).reset_index()
    df_grouped['period'] = df_grouped['発注日'].dt.strftime('%Y-%m-%d')

# Calculate gross profit and margin
df_grouped['粗利'] = df_grouped['売上金額JPY'] - df_grouped['仕入金額JPY']
df_grouped['粗利率'] = (df_grouped['粗利'] / df_grouped['売上金額JPY']) * 100

# --- Streamlit dashboard ---

# 1. Display the sum of 売上金額JPY
st.title("売上ダッシュボード")
total_sales = df_grouped['売上金額JPY'].sum()
st.metric(label="総売上金額 (JPY)", value=f"¥{total_sales:,.0f}")

# 2. Altair chart for 売上金額JPY and 粗利率
st.subheader(f"{view_option}の売上金額と粗利率の推移")

# Create the bar chart for 売上金額JPY
bars = alt.Chart(df_grouped).mark_bar(color='cornflowerblue').encode(
    x='period:O',
    y='売上金額JPY:Q',
    tooltip=['period', '売上金額JPY']
).properties(
    width=700,
    height=400
)

# Create the line chart for 粗利率
line = alt.Chart(df_grouped).mark_line(color='lightcoral', point=True).encode(
    x='period:O',
    y='粗利率:Q',
    tooltip=['period', '粗利率']
)

# Combine the two charts
combined_chart = alt.layer(bars, line).resolve_scale(
    y='independent'  # Separate y-axes for each chart
)

# Display the combined Altair chart
st.altair_chart(combined_chart, use_container_width=True)

# 3. Heatmap for 生産工場 vs 納入先 (Count of Orders)
st.subheader('Count of Orders: 生産工場 vs 納入先')

# Prepare the filtered data for heatmap (cross-tabulation)
factory_delivery = pd.crosstab(df_filtered['納入先'], df_filtered['生産工場']).reset_index()

# Convert crosstab result into Altair format (melted DataFrame)
heatmap_data = factory_delivery.melt(id_vars='納入先', var_name='生産工場', value_name='count')

# Create the heatmap with Altair
heatmap = alt.Chart(heatmap_data).mark_rect().encode(
    x='生産工場:O',
    y='納入先:O',
    color=alt.Color('count:Q', scale=alt.Scale(scheme='blues'), title='Count'),
    tooltip=['納入先', '生産工場', 'count']
).properties(
    width=600,
    height=500,
)

# Display the heatmap in Streamlit
st.altair_chart(heatmap, use_container_width=True)

# --- Pareto chart for 商品 (merchandise) ---

st.subheader('Pareto Chart: 売上高と累計構成比 (商品別)')

# Group by '品名' (merchandise) and sum up '売上金額JPY'
df_pareto = df_filtered.groupby('品名')['売上金額JPY'].sum().reset_index()

# Sort by '売上金額JPY' in descending order
df_pareto = df_pareto.sort_values(by='売上金額JPY', ascending=False)

# Calculate cumulative percentage for the Pareto chart
df_pareto['累計構成比'] = df_pareto['売上金額JPY'].cumsum() / df_pareto['売上金額JPY'].sum() * 100

# Create the bar chart for '売上金額JPY'
bars_pareto = alt.Chart(df_pareto).mark_bar(color='gray', opacity=0.7).encode(
    x=alt.X('品名:O', sort=alt.EncodingSortField(field="売上金額JPY", op="sum", order='descending'), title='商品'),
    y=alt.Y('売上金額JPY:Q', title='売上金額JPY'),
    tooltip=['品名', '売上金額JPY']
)

# Create the line chart for cumulative percentage '累計構成比'
line_pareto = alt.Chart(df_pareto).mark_line(color='blue', point=True).encode(
    x=alt.X('品名:O', sort=alt.EncodingSortField(field="売上金額JPY", op="sum", order='descending'), title='商品'),
    y=alt.Y('累計構成比:Q', title='累計構成比 (%)', scale=alt.Scale(domain=[0, 100])),  # Set y-axis scale for cumulative percentage
    tooltip=['品名', '累計構成比']
)

# Combine the two charts
pareto_chart = alt.layer(bars_pareto, line_pareto).resolve_scale(
    y='independent'  # Separate y-axes for each chart
).properties(
    width=700,
    height=400
)

# Add a horizontal line at 80% cumulative percentage (aligned to secondary y-axis)
line_80 = alt.Chart(pd.DataFrame({'y': [80]})).mark_rule(color='red', strokeDash=[5,5]).encode(
    y=alt.Y('y:Q', scale=alt.Scale(domain=[0, 100]))  # Ensure alignment with secondary y-axis (0 to 100%)
)

# Display the Pareto chart with the corrected 80% line
st.altair_chart(pareto_chart + line_80, use_container_width=True)