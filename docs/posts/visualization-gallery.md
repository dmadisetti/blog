---
date: 2024-12-22
tags:
  - data-viz
  - mathematics
  - interactive
---

# Interactive Visualization Gallery

Explore mathematical beauty through interactive visualizations. Every parameter can be adjusted in real-time, and all plots update reactively.

<!-- more -->

## Parametric Curves

Parametric equations create fascinating curves. Let's explore them interactively:

```python {marimo}
import marimo as mo
import numpy as np
import matplotlib.pyplot as plt
```

```python {marimo}
# Controls for parametric curve
frequency_x = mo.ui.slider(1, 10, value=3, label="X Frequency:")
frequency_y = mo.ui.slider(1, 10, value=2, label="Y Frequency:")
amplitude = mo.ui.slider(1, 5, value=2, label="Amplitude:")
phase = mo.ui.slider(0, 2*np.pi, value=0, step=0.1, label="Phase shift:")

mo.hstack([
    mo.vstack([frequency_x, frequency_y]),
    mo.vstack([amplitude, phase])
])
```

```python {marimo}
# Generate parametric curve
t = np.linspace(0, 2*np.pi, 1000)
x = np.cos(frequency_x.value * t + phase.value)
y = amplitude.value * np.sin(frequency_y.value * t)

fig, ax = plt.subplots(figsize=(8, 8))
ax.plot(x, y, linewidth=2, color='#00bcd4')
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_title(f'Lissajous Curve (freq_x={frequency_x.value}, freq_y={frequency_y.value})')
ax.grid(True, alpha=0.3)
ax.set_aspect('equal')
ax.set_xlim(-1.2, 1.2)
ax.set_ylim(-amplitude.value * 1.2, amplitude.value * 1.2)
plt.tight_layout()
fig
```

```python {marimo}
mo.md(f"""
### Current Parameters

- **X Frequency:** {frequency_x.value} oscillations
- **Y Frequency:** {frequency_y.value} oscillations
- **Amplitude:** {amplitude.value}
- **Phase:** {phase.value:.2f} radians

**Try these combinations:**
- (3, 2) - Classic Lissajous figure
- (5, 4) - Complex interwoven pattern
- (1, 1) - Simple diagonal line
- (3, 3) with phase=π/2 - Perfect circle
""")
```

## Function Plotter

Plot any function with adjustable parameters:

```python {marimo}
# Function type selector and parameters
func_type = mo.ui.dropdown(
    options={
        "sin": "Sine Wave",
        "cos": "Cosine Wave",
        "tan": "Tangent",
        "exp": "Exponential",
        "log": "Logarithm"
    },
    value="sin",
    label="Function:"
)

coeff_a = mo.ui.slider(-5, 5, value=1, step=0.1, label="Coefficient A:")
coeff_b = mo.ui.slider(-5, 5, value=1, step=0.1, label="Coefficient B:")
offset = mo.ui.slider(-10, 10, value=0, step=0.5, label="Vertical offset:")

mo.vstack([func_type, coeff_a, coeff_b, offset])
```

```python {marimo}
# Generate function plot
x_vals = np.linspace(-10, 10, 1000)

# Calculate y values based on selected function
if func_type.value == "sin":
    y_vals = coeff_a.value * np.sin(coeff_b.value * x_vals) + offset.value
    formula = f"y = {coeff_a.value:.1f} sin({coeff_b.value:.1f}x) + {offset.value:.1f}"
elif func_type.value == "cos":
    y_vals = coeff_a.value * np.cos(coeff_b.value * x_vals) + offset.value
    formula = f"y = {coeff_a.value:.1f} cos({coeff_b.value:.1f}x) + {offset.value:.1f}"
elif func_type.value == "tan":
    y_vals = coeff_a.value * np.tan(coeff_b.value * x_vals) + offset.value
    y_vals = np.clip(y_vals, -20, 20)  # Clip for display
    formula = f"y = {coeff_a.value:.1f} tan({coeff_b.value:.1f}x) + {offset.value:.1f}"
elif func_type.value == "exp":
    y_vals = coeff_a.value * np.exp(coeff_b.value * x_vals) + offset.value
    y_vals = np.clip(y_vals, -20, 20)  # Clip for display
    formula = f"y = {coeff_a.value:.1f} exp({coeff_b.value:.1f}x) + {offset.value:.1f}"
else:  # log
    y_vals = coeff_a.value * np.log(np.abs(coeff_b.value * x_vals) + 0.1) + offset.value
    formula = f"y = {coeff_a.value:.1f} log(|{coeff_b.value:.1f}x|) + {offset.value:.1f}"

fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.plot(x_vals, y_vals, linewidth=2, color='#00ffff')
ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.3)
ax2.axvline(x=0, color='gray', linestyle='--', alpha=0.3)
ax2.set_xlabel('x')
ax2.set_ylabel('y')
ax2.set_title(f'Function Plot: {formula}')
ax2.grid(True, alpha=0.3)
ax2.set_ylim(-15, 15)
plt.tight_layout()
fig2
```

## Polar Plots

Explore patterns in polar coordinates:

```python {marimo}
# Polar plot controls
n_petals = mo.ui.slider(1, 12, value=5, label="Number of petals:")
petal_size = mo.ui.slider(0.5, 3, value=1, step=0.1, label="Petal size:")
rotation = mo.ui.slider(0, 360, value=0, label="Rotation (degrees):")

mo.hstack([n_petals, petal_size, rotation])
```

```python {marimo}
# Generate polar plot
theta = np.linspace(0, 2*np.pi, 1000)
r = petal_size.value * np.abs(np.cos(n_petals.value * theta + np.radians(rotation.value)))

fig3 = plt.figure(figsize=(8, 8))
ax3 = fig3.add_subplot(111, projection='polar')
ax3.plot(theta, r, linewidth=2, color='#ff00ff')
ax3.fill(theta, r, alpha=0.3, color='#ff00ff')
ax3.set_title(f'Rose Curve (n={n_petals.value})', pad=20)
ax3.grid(True, alpha=0.3)
plt.tight_layout()
fig3
```

```python {marimo}
mo.md(f"""
### Rose Curve Properties

The polar equation is: **r = {petal_size.value:.1f} |cos({n_petals.value}θ)|**

- **Petals:** {n_petals.value * 2 if n_petals.value % 2 == 0 else n_petals.value}
  ({'Even number → 2n petals' if n_petals.value % 2 == 0 else 'Odd number → n petals'})
- **Rotation:** {rotation.value}°

**Try these values:**
- n=3: Three-petaled flower
- n=4: Eight-petaled rose
- n=5: Five-pointed star
- n=6: Twelve-petaled rose
""")
```

## Heatmap Visualization

Explore 2D functions as heatmaps:

```python {marimo}
# Heatmap controls
grid_size = mo.ui.slider(20, 100, value=50, step=10, label="Grid resolution:")
func_choice = mo.ui.dropdown(
    options={
        "ripple": "Ripple Pattern",
        "saddle": "Saddle Surface",
        "peaks": "Peaks and Valleys"
    },
    value="ripple",
    label="Pattern:"
)

mo.hstack([grid_size, func_choice])
```

```python {marimo}
# Generate heatmap
x_heat = np.linspace(-3, 3, grid_size.value)
y_heat = np.linspace(-3, 3, grid_size.value)
X, Y = np.meshgrid(x_heat, y_heat)

if func_choice.value == "ripple":
    Z = np.sin(np.sqrt(X**2 + Y**2)) * np.exp(-0.1 * (X**2 + Y**2))
    title = "Ripple: sin(√(x²+y²)) × exp(-0.1(x²+y²))"
elif func_choice.value == "saddle":
    Z = X**2 - Y**2
    title = "Saddle: x² - y²"
else:  # peaks
    Z = 3 * (1 - X)**2 * np.exp(-(X**2) - (Y+1)**2) \
        - 10*(X/5 - X**3 - Y**5) * np.exp(-X**2 - Y**2) \
        - 1/3 * np.exp(-(X+1)**2 - Y**2)
    title = "Peaks: Complex surface"

fig4, ax4 = plt.subplots(figsize=(10, 8))
im = ax4.imshow(Z, extent=[-3, 3, -3, 3], origin='lower',
                cmap='viridis', aspect='auto')
ax4.set_xlabel('x')
ax4.set_ylabel('y')
ax4.set_title(title)
plt.colorbar(im, ax=ax4, label='z value')
plt.tight_layout()
fig4
```

## Navigation Challenge!

Try navigating this entire page using only vim keys:

1. Press `g` to jump to the top
2. Use `ctrl+j` to jump through sections
3. Try `3j` to move down 3 paragraphs
4. Use `w` and `b` to navigate words in text
5. Press `G` to jump to the bottom (here!)

Watch for the cyan highlight and cursor trails as you navigate!

---

*All visualizations update in real-time as you adjust the parameters. This is the power of marimo's reactive execution.*
