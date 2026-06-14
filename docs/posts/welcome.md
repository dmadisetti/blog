---
date: 2024-12-22
tags:
  - introduction
  - interactive
---

# Welcome to Dylan's Interactive Blog!

This isn't your typical blog—every post here is a live, interactive experience powered by [marimo](https://marimo.io/), a reactive Python notebook that runs right in your browser.

<!-- more -->

## What Makes This Special?

### 1. Reactive Notebooks

Unlike traditional notebooks, marimo automatically re-runs dependent cells when you interact with UI elements. No need to manually execute cells or worry about stale state.

Try this slider below—watch how the text updates automatically:

```python {marimo}
import marimo as mo
```

```python {marimo}
slider = mo.ui.slider(1, 100, value=50, label="Adjust me:")
slider
```

```python {marimo}
mo.md(f"""
### Current Value: **{slider.value}**

Notice how this updates instantly? That's marimo's reactivity in action! The value automatically flows from the slider to this text.
""")
```

### 2. Vim Navigation

This blog also features always-on vim-style keyboard navigation:

- **`j`/`k`** - Navigate up/down through content blocks
- **`w`/`b`/`e`** - Jump between words
- **`g`/`G`** - Jump to top/bottom of page
- **`ctrl+j`/`ctrl+k`** - Jump 5 lines (paragraph-aware)
- **`f{char}`** - Find character on current line
- **`3j`, `5w`** - Count prefixes work!

Try it now! Press `j` a few times to navigate down. You'll see a subtle highlight on your current block and smooth WebGL cursor trails.

### 3. Multiple Interactive Elements

Let's combine several UI elements to show coordination:

```python {marimo}
# Create multiple controls
name = mo.ui.text(placeholder="Enter your name", label="Name:")
favorite_color = mo.ui.dropdown(
    options=["red", "blue", "green", "purple", "cyan"],
    value="cyan",
    label="Favorite color:"
)
show_message = mo.ui.checkbox(value=True, label="Show greeting")

mo.vstack([name, favorite_color, show_message])
```

```python {marimo}
mo.md(
    f"""
    <div style="padding: 1rem; background-color: {favorite_color.value if show_message.value else '#gray'}20; border-left: 4px solid {favorite_color.value if show_message.value else 'gray'}; border-radius: 4px;">

    {"### Hello, " + (name.value or "friend") + "! 👋" if show_message.value else "### (greeting hidden)"}

    {f"Your favorite color is **{favorite_color.value}**!" if show_message.value and name.value else ""}

    </div>
    """
)
```

All three controls are connected—change any of them and see the greeting update instantly!

## What's Next?

Explore more posts to see:

- Interactive data visualizations
- SQL queries on dataframes
- Mathematical explorations
- Real-time simulations

Every code block you see is live and editable. This is the future of technical blogging!

---

**Pro tip:** Use vim navigation (`ctrl+j`) to quickly jump between sections. Try pressing `5j` to jump 5 lines down, or `w` to navigate word by word through this text.
