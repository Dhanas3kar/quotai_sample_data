"""
HTML report generator for QuotAI cost estimates.

Produces a self-contained HTML report with variant details, feature
extraction results, cost breakdown, pricing adjustments, and summary.
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict


def _fmt(value: Decimal, symbol: str = "₹") -> str:
    """Format a Decimal value as currency."""
    return f"{symbol} {value:,.2f}"


def generate_html_report(result: Dict) -> str:
    """
    Generate a professional HTML report from an estimation result dict.

    Parameters
    ----------
    result : dict
        Output from ``CostEstimator.estimate()``.

    Returns
    -------
    str
        Complete HTML document as a string.
    """
    features = result["features"]
    holes = features.get("holes", [])
    hole_str = ", ".join(
        f'{h["count"]}× ⌀{h["diameter_mm"]} mm' for h in holes
    ) or "None"

    # Operation rows
    op_rows = ""
    for op in result["operation_details"]:
        op_rows += f"""
        <tr>
            <td>{op['operation_name']}</td>
            <td>{op['work_center_name']}</td>
            <td>{op['setup_time_hrs']}</td>
            <td>{op['cycle_time_hrs']}</td>
            <td>{_fmt(op['rate_per_hour'])}/hr</td>
            <td>{_fmt(op['cost_per_unit'])}</td>
        </tr>"""

    # Adjustment rows
    adj_rows = ""
    for adj in result["adjustments"]:
        sign = "+" if adj["category"] == "overhead" else "−"
        desc = f"{adj['value']}% of {adj['apply_on']}" if adj["type"] == "percentage" else "fixed/unit"
        adj_rows += f"""
        <tr>
            <td>{adj['name']}</td>
            <td>{adj['category'].title()}</td>
            <td>{desc}</td>
            <td>{sign} {_fmt(adj['computed_amount'])}</td>
        </tr>"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    estimation_id = result.get("estimation_id", "N/A")
    status = result.get("status", "draft").upper()
    family_name = result.get("family_name", "N/A")
    created_at = result.get("created_at", now)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuotAI — Cost Estimation Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #f5f7fa; color: #333; padding: 40px;
    max-width: 900px; margin: 0 auto;
  }}
  .header {{
    background: linear-gradient(135deg, #1a1d2e, #2a3050);
    color: #fff; padding: 30px 40px; border-radius: 12px;
    margin-bottom: 30px;
  }}
  .header h1 {{ font-size: 24px; margin-bottom: 6px; }}
  .header h1 span {{ color: #6c8cff; }}
  .header .meta {{ font-size: 13px; color: #aaa; }}
  .header .meta .status {{
    display: inline-block; padding: 2px 10px; border-radius: 4px;
    font-weight: 600; font-size: 11px; text-transform: uppercase;
    background: #27ae6044; color: #2ecc71; margin-left: 8px;
  }}
  .section {{
    background: #fff; border-radius: 10px; padding: 24px 30px;
    margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  }}
  .section h2 {{
    font-size: 16px; color: #1a1d2e; margin-bottom: 14px;
    border-bottom: 2px solid #eee; padding-bottom: 8px;
  }}
  table {{
    width: 100%; border-collapse: collapse; font-size: 14px;
  }}
  th, td {{
    text-align: left; padding: 8px 12px;
    border-bottom: 1px solid #f0f0f0;
  }}
  th {{ color: #666; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
  .summary-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
  }}
  .summary-card {{
    background: #f8fafc; border: 1px solid #e8ecf0;
    border-radius: 8px; padding: 16px 20px;
  }}
  .summary-card .label {{ font-size: 12px; color: #888; text-transform: uppercase; }}
  .summary-card .value {{ font-size: 22px; font-weight: 700; color: #1a1d2e; margin-top: 4px; }}
  .summary-card.highlight {{
    background: linear-gradient(135deg, #1a1d2e, #2a3050);
    border-color: transparent;
  }}
  .summary-card.highlight .label {{ color: #8899bb; }}
  .summary-card.highlight .value {{ color: #fff; }}
  .footer {{
    text-align: center; font-size: 12px; color: #aaa;
    padding: 20px 0; border-top: 1px solid #eee; margin-top: 10px;
  }}
  .feat-grid {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }}
  .feat-item {{ padding: 10px; background: #f8fafc; border-radius: 6px; }}
  .feat-item .fl {{ font-size: 11px; color: #888; text-transform: uppercase; }}
  .feat-item .fv {{ font-size: 16px; font-weight: 600; margin-top: 2px; }}
</style>
</head>
<body>

<div class="header">
  <h1>Quot<span>AI</span> — Cost Estimation Report</h1>
  <div class="meta">
    Estimation ID: <strong>{estimation_id[:8]}…</strong>
    <span class="status">{status}</span><br>
    Family: {family_name} &nbsp;|&nbsp; Variant: {result['variant']} &nbsp;|&nbsp;
    Quantity: {result['quantity']} &nbsp;|&nbsp; Created: {created_at}
  </div>
</div>

<div class="section">
  <h2>📐 Extracted Features</h2>
  <div class="feat-grid">
    <div class="feat-item"><div class="fl">Outer Diameter</div><div class="fv">{features['outer_diameter_mm']} mm</div></div>
    <div class="feat-item"><div class="fl">Inner Diameter</div><div class="fv">{features['inner_diameter_mm']} mm</div></div>
    <div class="feat-item"><div class="fl">Length</div><div class="fv">{features['length_mm']} mm</div></div>
    <div class="feat-item"><div class="fl">Holes</div><div class="fv">{hole_str}</div></div>
    <div class="feat-item"><div class="fl">Material</div><div class="fv">{result['material_name']}</div></div>
    <div class="feat-item"><div class="fl">Weight (incl. scrap)</div><div class="fv">{result['weight_kg']} kg</div></div>
  </div>
</div>

<div class="section">
  <h2>🪨 Material Cost</h2>
  <table>
    <tr><th>Material</th><th>Weight / Unit</th><th>Rate / kg</th><th>Cost / Unit</th></tr>
    <tr>
      <td>{result['material_name']}</td>
      <td>{result['weight_kg']} kg</td>
      <td>{_fmt(result['rate_per_kg'])}/kg</td>
      <td><strong>{_fmt(result['material_cost'])}</strong></td>
    </tr>
  </table>
</div>

<div class="section">
  <h2>🔧 Operation Costs</h2>
  <table>
    <tr><th>Operation</th><th>Work Center</th><th>Setup (hr)</th><th>Cycle (hr)</th><th>Rate</th><th>Cost / Unit</th></tr>
    {op_rows}
    <tr style="font-weight:700; border-top:2px solid #ddd;">
      <td colspan="5">Total Operation Cost</td>
      <td>{_fmt(result['operation_cost'])}</td>
    </tr>
  </table>
</div>

<div class="section">
  <h2>📄 Pricing Adjustments ({result['template_name']})</h2>
  <table>
    <tr><th>Item</th><th>Category</th><th>Basis</th><th>Amount / Unit</th></tr>
    {adj_rows}
  </table>
</div>

<div class="section">
  <h2>📊 Cost Summary</h2>
  <div class="summary-grid">
    <div class="summary-card">
      <div class="label">Material Cost / Unit</div>
      <div class="value">{_fmt(result['material_cost'])}</div>
    </div>
    <div class="summary-card">
      <div class="label">Operation Cost / Unit</div>
      <div class="value">{_fmt(result['operation_cost'])}</div>
    </div>
    <div class="summary-card">
      <div class="label">Subtotal / Unit</div>
      <div class="value">{_fmt(result['subtotal'])}</div>
    </div>
    <div class="summary-card">
      <div class="label">Overheads / Unit</div>
      <div class="value">+ {_fmt(result['overheads'])}</div>
    </div>
    <div class="summary-card">
      <div class="label">Discounts / Unit</div>
      <div class="value">− {_fmt(result['discounts'])}</div>
    </div>
    <div class="summary-card">
      <div class="label">Net Cost / Unit</div>
      <div class="value">{_fmt(result['net_cost_per_unit'])}</div>
    </div>
    <div class="summary-card highlight" style="grid-column: span 2;">
      <div class="label">Total Cost ({result['quantity']} units)</div>
      <div class="value">{_fmt(result['total_cost'])}</div>
    </div>
  </div>
</div>

<div class="footer">
  QuotAI Cost Estimator &nbsp;·&nbsp; Estimation {estimation_id[:8]}… ({status}) &nbsp;·&nbsp; Report generated {now} &nbsp;·&nbsp; Currency: {result['currency']}
</div>

</body>
</html>"""
    return html
