from app import app, db
from app.models import Participant, Trial, Assignment, Response, AIEvent

@app.shell_context_processor
def make_shell_context():
    return dict(db=db, Participant=Participant, Trial=Trial,
                Assignment=Assignment, Response=Response, AIEvent=AIEvent)



# --- A3 utility: seed trials from JSON file ---
import click, json
from app.models import Trial

@app.cli.command('seed-trials')
@click.argument('json_path')
def seed_trials(json_path):
    """Load trials from a JSON file.
    Expect a list of objects; each will be stored in Trial.payload.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        items = json.load(f)
    n=0
    for obj in items:
        t = Trial(payload=obj, split=obj.get('split','all'))
        db.session.add(t)
        n+=1
    db.session.commit()
    print(f"Inserted {n} trials from {json_path}")

@app.cli.command('seed-trials-csv')
@click.argument('csv_path')
def seed_trials_csv(csv_path):
    """CSV columns: dilemma_text, gt_severity_score, gt_justification, ai_severity_score, ai_justification"""
    import pandas as _pd
    from app.models import Trial, db
    df = _pd.read_csv(csv_path)
    n = 0
    for _, row in df.iterrows():
        payload = {
            "dilemma_text": str(row["dilemma_text"]),
            "gt_severity_score": int(row["gt_severity_score"]),
            "gt_justification": str(row.get("gt_justification", "")),
            "ai_severity_score": (None if _pd.isna(row.get("ai_severity_score")) else int(row.get("ai_severity_score"))),
            "ai_justification": str(row.get("ai_justification", "")),
        }
        db.session.add(Trial(payload=payload, split="all"))
        n += 1
    db.session.commit()
    print(f"Inserted {n} trials from {csv_path}")
