import csv
from pathlib import Path
import click
from flask import current_app
from app import db
from app.models import Trial

def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    # repo-relative: app root -> parent -> resources/...
    return Path(current_app.root_path).parent / p

@click.command("import-ai-confidence")
@click.argument("csv_path")
def import_ai_confidence(csv_path):
    """
    Import ai_confidence for trials.
    CSV columns: trial_id, ai_confidence (0..1) or ai_confidence_pct (70..100).
    """
    p = _resolve(csv_path)
    rows = 0
    updated = 0
    with p.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows += 1
            tid = int(row["trial_id"])
            conf = None
            if "ai_confidence" in row and row["ai_confidence"]:
                conf = float(row["ai_confidence"])
            elif "ai_confidence_pct" in row and row["ai_confidence_pct"]:
                conf = float(row["ai_confidence_pct"]) / 100.0
            if conf is None:
                continue
            trial = Trial.query.get(tid)
            if not trial:
                continue
            trial.ai_confidence = max(0.0, min(1.0, conf))
            updated += 1
    db.session.commit()
    click.echo(f"Processed {rows} rows; updated {updated} trials.")
