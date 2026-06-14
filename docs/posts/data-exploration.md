---
date: 2024-12-22
tags:
  - data-science
  - interactive
  - sql
---

# Interactive Data Exploration with Marimo

One of marimo's superpowers is making data exploration interactive and reactive. Let's explore a dataset with sliders, filters, and SQL queries that update in real-time.

<!-- more -->

## Generate Sample Data

First, let's create a synthetic dataset to work with:

```python {marimo}
import marimo as mo
import pandas as pd
import numpy as np
```

```python {marimo}
# Set seed for reproducibility
np.random.seed(42)

# Generate sample data
n_samples = 200
data = pd.DataFrame({
    'date': pd.date_range('2024-01-01', periods=n_samples, freq='D'),
    'value': np.cumsum(np.random.randn(n_samples)) + 100,
    'category': np.random.choice(['A', 'B', 'C', 'D'], n_samples),
    'quantity': np.random.randint(1, 100, n_samples),
    'price': np.random.uniform(10, 100, n_samples)
})

# Calculate revenue
data['revenue'] = data['quantity'] * data['price']

mo.md(f"Generated **{len(data)}** rows of sample data")
```

## Interactive Data Table

Marimo provides an interactive dataframe viewer. You can sort, filter, and search through the data:

```python {marimo}
mo.ui.table(data, selection=None, page_size=10)
```

## Filter with UI Controls

Let's add interactive filters to explore subsets of the data:

```python {marimo}
# Create filter controls
category_filter = mo.ui.multiselect(
    options=['A', 'B', 'C', 'D'],
    value=['A', 'B', 'C', 'D'],
    label="Categories:"
)

value_range = mo.ui.range_slider(
    start=float(data['value'].min()),
    stop=float(data['value'].max()),
    value=[float(data['value'].min()), float(data['value'].max())],
    label="Value range:"
)

min_revenue = mo.ui.slider(
    start=0,
    stop=float(data['revenue'].max()),
    value=0,
    label="Minimum revenue:"
)

mo.vstack([category_filter, value_range, min_revenue])
```

```python {marimo}
# Filter the data based on controls
filtered_data = data[
    (data['category'].isin(category_filter.value)) &
    (data['value'] >= value_range.value[0]) &
    (data['value'] <= value_range.value[1]) &
    (data['revenue'] >= min_revenue.value)
]

mo.md(f"""
### Filtered Results

Showing **{len(filtered_data)}** of **{len(data)}** rows

**Summary Statistics:**
- Mean Value: **${filtered_data['value'].mean():.2f}**
- Total Revenue: **${filtered_data['revenue'].sum():.2f}**
- Average Price: **${filtered_data['price'].mean():.2f}**
""")
```

```python {marimo}
# Show filtered table
mo.ui.table(filtered_data, page_size=10)
```

## SQL Queries with DuckDB

Marimo has built-in SQL support powered by DuckDB. You can query pandas dataframes directly:

```python {marimo}
# SQL query on filtered data
import duckdb

sql_result = duckdb.query(f"""
    SELECT
        category,
        COUNT(*) as count,
        AVG(revenue) as avg_revenue,
        SUM(revenue) as total_revenue,
        AVG(quantity) as avg_quantity
    FROM filtered_data
    GROUP BY category
    ORDER BY total_revenue DESC
""").df()

mo.ui.table(sql_result)
```

```python {marimo}
mo.md(f"""
### Category Analysis

The SQL query above shows revenue by category in the filtered dataset.

**Top Category:** {sql_result.iloc[0]['category']} with ${sql_result.iloc[0]['total_revenue']:.2f} total revenue
""")
```

## Visualization

Let's visualize the filtered data:

```python {marimo}
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

# Time series plot
ax1.plot(filtered_data['date'], filtered_data['value'], alpha=0.7)
ax1.set_xlabel('Date')
ax1.set_ylabel('Value')
ax1.set_title(f'Time Series ({len(filtered_data)} points)')
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', rotation=45)

# Revenue by category
category_revenue = filtered_data.groupby('category')['revenue'].sum().sort_values(ascending=False)
ax2.bar(category_revenue.index, category_revenue.values, color='#00bcd4')
ax2.set_xlabel('Category')
ax2.set_ylabel('Total Revenue ($)')
ax2.set_title('Revenue by Category')
ax2.grid(True, axis='y', alpha=0.3)

plt.tight_layout()
fig
```

## Try It Yourself!

Change the filters above and watch everything update automatically:

1. **Toggle categories** - Select/deselect categories to filter
2. **Adjust value range** - Drag the range slider
3. **Set minimum revenue** - Filter out low-revenue items

The table, SQL results, statistics, and plots all update reactively. No need to re-run cells manually!

---

**Vim Navigation Tip:** Use `ctrl+w j` and `ctrl+w k` to quickly jump between the different visualization blocks. Try `G` to jump to the bottom or `g` to return to the top!
