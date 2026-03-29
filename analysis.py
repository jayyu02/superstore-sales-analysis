"""
Superstore Sales Analysis
=========================
Author : Jaya Mundre
Tools  : Python, pandas, matplotlib, seaborn, SQLite
Dataset: data/superstore.csv (2,000 orders, 2021-2023)

Run:
    python analysis.py
Outputs are saved to outputs/
"""

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import warnings
import os

warnings.filterwarnings('ignore')
os.makedirs('outputs', exist_ok=True)

# ── style ────────────────────────────────────────────────────────────────────
BLUE    = '#2E75B6'
GREEN   = '#70AD47'
ORANGE  = '#ED7D31'
RED     = '#FF0000'
PURPLE  = '#7030A0'
PALETTE = [BLUE, GREEN, ORANGE, '#FFC000', PURPLE]

plt.rcParams.update({
    'figure.facecolor': 'white',
    'axes.facecolor':   'white',
    'axes.spines.top':  False,
    'axes.spines.right':False,
    'axes.grid':        True,
    'grid.alpha':       0.3,
    'grid.linestyle':   '--',
    'font.family':      'DejaVu Sans',
    'axes.titlesize':   13,
    'axes.titleweight': 'bold',
    'axes.labelsize':   11,
})

# ─────────────────────────────────────────────────────────────────────────────
# 1. LOAD DATA  →  SQLITE
# ─────────────────────────────────────────────────────────────────────────────
print("Loading data...")
df = pd.read_csv('data/superstore.csv', parse_dates=['order_date', 'ship_date'])

conn = sqlite3.connect(':memory:')
df.to_sql('superstore', conn, index=False, if_exists='replace')
print(f"  {len(df):,} rows loaded into SQLite")

def q(sql):
    return pd.read_sql_query(sql, conn)


# ─────────────────────────────────────────────────────────────────────────────
# 2. SQL QUERIES  (same as analysis_queries.sql)
# ─────────────────────────────────────────────────────────────────────────────

# Q1 — overall KPIs
kpi = q("""
    SELECT
        COUNT(DISTINCT order_id)              AS total_orders,
        ROUND(SUM(sales),  2)                 AS total_sales,
        ROUND(SUM(profit), 2)                 AS total_profit,
        ROUND(SUM(profit)/SUM(sales)*100, 2)  AS profit_margin_pct
    FROM superstore
""").iloc[0]

print("\n── KEY PERFORMANCE INDICATORS ──────────────────────────")
print(f"  Total orders  : {int(kpi.total_orders):,}")
print(f"  Total sales   : ${kpi.total_sales:,.2f}")
print(f"  Total profit  : ${kpi.total_profit:,.2f}")
print(f"  Profit margin : {kpi.profit_margin_pct}%")

# Q2 — by region
region = q("""
    SELECT region,
           ROUND(SUM(sales),2)  AS total_sales,
           ROUND(SUM(profit),2) AS total_profit,
           ROUND(SUM(profit)/SUM(sales)*100,2) AS margin_pct
    FROM superstore GROUP BY region ORDER BY total_sales DESC
""")

# Q3 — by category
category = q("""
    SELECT category,
           ROUND(SUM(sales),2)            AS total_sales,
           ROUND(SUM(profit),2)           AS total_profit,
           ROUND(AVG(discount)*100, 1)    AS avg_discount_pct
    FROM superstore GROUP BY category ORDER BY total_sales DESC
""")

# Q4 — top sub-categories
subcat = q("""
    SELECT sub_category,
           ROUND(SUM(profit),2) AS total_profit
    FROM superstore GROUP BY sub_category ORDER BY total_profit DESC LIMIT 8
""")

# Q5 — monthly trend
monthly = q("""
    SELECT STRFTIME('%Y-%m', order_date) AS month,
           ROUND(SUM(sales),2)  AS monthly_sales,
           ROUND(SUM(profit),2) AS monthly_profit
    FROM superstore GROUP BY month ORDER BY month
""")

# Q6 — segment
segment = q("""
    SELECT segment,
           ROUND(SUM(sales),2)   AS total_sales,
           ROUND(AVG(sales),2)   AS avg_order_value
    FROM superstore GROUP BY segment ORDER BY total_sales DESC
""")

# Q7 — shipping mode
shipping = q("""
    SELECT ship_mode,
           COUNT(*) AS count,
           ROUND(AVG(JULIANDAY(ship_date)-JULIANDAY(order_date)),1) AS avg_days
    FROM superstore GROUP BY ship_mode ORDER BY avg_days
""")

# Q9 — discount impact
discount = q("""
    SELECT
        CASE WHEN discount=0     THEN 'No discount'
             WHEN discount<=0.10 THEN '1-10%'
             WHEN discount<=0.20 THEN '11-20%'
             ELSE '21%+' END AS band,
        ROUND(AVG(profit),2) AS avg_profit,
        COUNT(*) AS orders
    FROM superstore
    GROUP BY band ORDER BY avg_profit DESC
""")

# Q10 — YoY growth
yoy = q("""
    WITH y AS (
        SELECT STRFTIME('%Y', order_date) AS year,
               ROUND(SUM(sales),2) AS total_sales
        FROM superstore GROUP BY year
    )
    SELECT year, total_sales,
           LAG(total_sales) OVER (ORDER BY year) AS prev,
           ROUND((total_sales - LAG(total_sales) OVER (ORDER BY year))
                 / LAG(total_sales) OVER (ORDER BY year)*100, 1) AS yoy_pct
    FROM y ORDER BY year
""")


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHARTS
# ─────────────────────────────────────────────────────────────────────────────

# ── Chart 1: Sales by Region (horizontal bar) ────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4))
bars = ax.barh(region['region'], region['total_sales'], color=PALETTE[:4], height=0.5)
ax.bar_label(bars, labels=[f"${v/1e3:.0f}K" for v in region['total_sales']], padding=5, fontsize=10)
ax.set_xlabel('Total Sales ($)')
ax.set_title('Sales by Region')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f'${x/1e3:.0f}K'))
plt.tight_layout()
plt.savefig('outputs/01_sales_by_region.png', dpi=150, bbox_inches='tight')
plt.close()
print("\nSaved: outputs/01_sales_by_region.png")

# ── Chart 2: Sales & Profit by Category (grouped bar) ───────────────────────
fig, ax = plt.subplots(figsize=(8, 4))
x = range(len(category))
w = 0.35
b1 = ax.bar([i-w/2 for i in x], category['total_sales'],  width=w, label='Sales',  color=BLUE)
b2 = ax.bar([i+w/2 for i in x], category['total_profit'], width=w, label='Profit', color=GREEN)
ax.set_xticks(list(x)); ax.set_xticklabels(category['category'])
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'${v/1e3:.0f}K'))
ax.set_title('Sales & Profit by Category')
ax.legend()
plt.tight_layout()
plt.savefig('outputs/02_category_performance.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/02_category_performance.png")

# ── Chart 3: Monthly Sales Trend (line) ──────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(monthly['month'], monthly['monthly_sales'],  color=BLUE,  linewidth=2, marker='o', markersize=3, label='Sales')
ax.plot(monthly['month'], monthly['monthly_profit'], color=GREEN, linewidth=2, marker='s', markersize=3, label='Profit')
ax.set_title('Monthly Sales & Profit Trend (2021–2023)')
ax.set_xlabel('Month')
tick_step = max(1, len(monthly)//12)
ax.set_xticks(range(0, len(monthly), tick_step))
ax.set_xticklabels(monthly['month'].iloc[::tick_step], rotation=45, ha='right')
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'${v/1e3:.0f}K'))
ax.legend()
plt.tight_layout()
plt.savefig('outputs/03_monthly_trend.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/03_monthly_trend.png")

# ── Chart 4: Top Sub-categories by Profit (bar) ──────────────────────────────
fig, ax = plt.subplots(figsize=(8, 4))
colors = [GREEN if v > 0 else RED for v in subcat['total_profit']]
bars = ax.barh(subcat['sub_category'], subcat['total_profit'], color=colors, height=0.55)
ax.bar_label(bars, labels=[f"${v/1e3:.1f}K" for v in subcat['total_profit']], padding=4, fontsize=9)
ax.set_title('Top 8 Sub-Categories by Profit')
ax.set_xlabel('Total Profit ($)')
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'${v/1e3:.0f}K'))
plt.tight_layout()
plt.savefig('outputs/04_subcat_profit.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/04_subcat_profit.png")

# ── Chart 5: Segment Sales (pie) ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(6, 5))
wedges, texts, autotexts = ax.pie(
    segment['total_sales'],
    labels=segment['segment'],
    autopct='%1.1f%%',
    colors=PALETTE[:3],
    startangle=140,
    wedgeprops={'linewidth':1,'edgecolor':'white'}
)
for t in autotexts: t.set_fontsize(10)
ax.set_title('Sales by Customer Segment')
plt.tight_layout()
plt.savefig('outputs/05_segment_pie.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/05_segment_pie.png")

# ── Chart 6: Discount Impact on Profit (bar) ─────────────────────────────────
fig, ax = plt.subplots(figsize=(7, 4))
bar_colors = [GREEN if v > 0 else RED for v in discount['avg_profit']]
bars = ax.bar(discount['band'], discount['avg_profit'], color=bar_colors, width=0.5)
ax.bar_label(bars, labels=[f"${v:.0f}" for v in discount['avg_profit']], padding=4, fontsize=10)
ax.axhline(0, color='black', linewidth=0.8, linestyle='--')
ax.set_title('Avg Profit by Discount Band')
ax.set_xlabel('Discount Range')
ax.set_ylabel('Average Profit ($)')
plt.tight_layout()
plt.savefig('outputs/06_discount_impact.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/06_discount_impact.png")

# ── Chart 7: YoY Sales Growth (bar + line) ───────────────────────────────────
fig, ax1 = plt.subplots(figsize=(7, 4))
bars = ax1.bar(yoy['year'], yoy['total_sales'], color=BLUE, width=0.4, label='Sales')
ax1.set_ylabel('Total Sales ($)')
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v,_: f'${v/1e3:.0f}K'))
ax2 = ax1.twinx()
valid = yoy.dropna(subset=['yoy_pct'])
ax2.plot(valid['year'], valid['yoy_pct'], color=ORANGE, marker='o', linewidth=2, label='YoY Growth %')
ax2.set_ylabel('YoY Growth (%)', color=ORANGE)
ax2.tick_params(axis='y', labelcolor=ORANGE)
ax1.set_title('Year-over-Year Sales Growth')
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1+lines2, labels1+labels2, loc='upper left')
plt.tight_layout()
plt.savefig('outputs/07_yoy_growth.png', dpi=150, bbox_inches='tight')
plt.close()
print("Saved: outputs/07_yoy_growth.png")


# ─────────────────────────────────────────────────────────────────────────────
# 4. PRINT SUMMARY TABLE
# ─────────────────────────────────────────────────────────────────────────────
print("\n── REGION SUMMARY ──────────────────────────────────────")
print(region.to_string(index=False))

print("\n── CATEGORY SUMMARY ────────────────────────────────────")
print(category.to_string(index=False))

print("\n── DISCOUNT IMPACT ─────────────────────────────────────")
print(discount.to_string(index=False))

print("\n── YoY GROWTH ──────────────────────────────────────────")
print(yoy.to_string(index=False))

print("\n All charts saved to outputs/")
conn.close()
