from flask import render_template, request, jsonify
from sqlalchemy import func, text
from app import app, db
from app.models import Participant, Trial, Assignment, Response, AIEvent

# ---------- Study entry / instructions ----------
@app.route('/study', methods=['GET'])
def study_index():
    return render_template('study_instructions.html')

# ---------- Start: create participant + initial block ----------
@app.route('/study/start', methods=['POST'])
def study_start():
    data = request.get_json(force=True)
    condition = (data.get('condition') or 'control').lower()
    p = Participant(
        condition=condition,
        worker_id=data.get('workerId'),
        assignment_id=data.get('assignmentId'),
        hit_id=data.get('hitId'),
    )
    db.session.add(p)
    db.session.flush()  # p.id now available

    # coverage-first: prefer trials with the lowest assignment count
    N = app.config.get('STUDY_TRIALS_PER_PARTICIPANT', 10)
    subq = db.session.query(
        Trial.id.label('tid'),
        func.count(Assignment.id).label('cnt')
    ).outerjoin(
        Assignment, Trial.id == Assignment.trial_id
    ).group_by(Trial.id).subquery()

    rows = db.session.query(subq.c.tid, subq.c.cnt).all()
    if not rows:
        return jsonify({'error': 'No trials loaded in DB. Run: flask seed-trials-csv resources/dilemma_combined.csv'}), 400

    min_cnt = min(r.cnt for r in rows)
    import random
    candidates = [r.tid for r in rows if r.cnt == min_cnt]
    random.shuffle(candidates)
    chosen = candidates[:N] if len(candidates) >= N else list(candidates)
    if len(chosen) < N:
        remaining = N - len(chosen)
        for c in sorted(set(r.cnt for r in rows if r.cnt > min_cnt)):
            pool = [r.tid for r in rows if r.cnt == c and r.tid not in chosen]
            random.shuffle(pool)
            take = min(remaining, len(pool))
            chosen.extend(pool[:take])
            remaining = N - len(chosen)
            if remaining <= 0:
                break

    for idx, tid in enumerate(chosen):
        db.session.add(Assignment(participant_id=p.id, trial_id=tid, order_idx=idx))
    db.session.commit()
    return jsonify({'participant_id': p.id, 'condition': condition, 'n_trials': len(chosen)}), 200

# ---------- Next trial ----------
@app.route('/study/next', methods=['GET'])
def study_next():
    pid = int(request.args['participant_id'])
    # find next assigned trial without a response
    q = text("""
        SELECT a.trial_id
        FROM assignment a
        LEFT JOIN response r ON r.trial_id = a.trial_id AND r.participant_id = a.participant_id
        WHERE a.participant_id = :pid AND r.id IS NULL
        ORDER BY a.order_idx ASC
        LIMIT 1
    """)
    row = db.session.execute(q, {'pid': pid}).first()
    if not row:
        return ('', 204)
    trial = Trial.query.get(row[0])
    return jsonify({'trial_id': trial.id, 'payload': trial.payload})

# ---------- Submit response (LOG ai_confidence here) ----------
@app.route('/study/submit', methods=['POST'])
def study_submit():
    d = request.get_json(force=True)
    # answer is stored as JSON in your model; keep that behavior
    r = Response(
        participant_id=int(d['participant_id']),
        trial_id=int(d['trial_id']),
        answer=d.get('answer'),
        correct=None,
        rt_ms=int(d.get('rt_ms') or 0),
        revealed_ai=bool(d.get('revealed_ai', False)),
        ai_confidence=(float(d.get('ai_confidence')) if d.get('ai_confidence') is not None else None)  # <-- fixed
    )
    db.session.add(r)
    db.session.commit()
    return jsonify({'ok': True})

# ---------- Log AI UI events ----------
@app.route('/study/event', methods=['POST'])
def study_event():
    d = request.get_json(force=True)
    e = AIEvent(
        participant_id=int(d['participant_id']),
        trial_id=int(d['trial_id']),
        event_type=d.get('event_type'),
        payload=d.get('payload')
    )
    db.session.add(e)
    db.session.commit()
    return jsonify({'ok': True})

# ---------- Run + Finish screens ----------
@app.route('/study/run', methods=['GET'])
def study_run():
    return render_template('study_run.html')

@app.route('/study/finish', methods=['GET'])
def study_finish():
    return render_template('study_finish.html')

# ---------- Export ----------
from io import StringIO
import csv
from flask import Response as FlaskResponse, jsonify
from app.models import Response as RespModel, Participant as PartModel, Trial as TrialModel

@app.route('/study/export', methods=['GET'])
def study_export():
    """
    GET /study/export?format=csv|json
    Exports one row per response with GT/AI fields from the trial payload.
    """
    fmt = (request.args.get('format') or 'csv').lower()

    q = (db.session.query(RespModel, PartModel, TrialModel)
         .join(PartModel, PartModel.id == RespModel.participant_id)
         .join(TrialModel, TrialModel.id == RespModel.trial_id)
         .order_by(RespModel.id.asc()))

    rows = []
    for r, p, t in q.all():
        payload = t.payload or {}
        ans_val = (r.answer or {}).get("value") if isinstance(r.answer, dict) else None
        # pick the logged confidence when available; otherwise fall back to trial-level/payload
        ai_conf = r.ai_confidence
        if ai_conf is None:
            ai_conf = payload.get("ai_confidence")
        if ai_conf is None and hasattr(t, "ai_confidence"):
            ai_conf = t.ai_confidence

        rows.append({
            "response_id": r.id,
            "participant_id": r.participant_id,
            "condition": p.condition,
            "trial_id": r.trial_id,
            "answer_value": ans_val,
            "rt_ms": r.rt_ms,
            "revealed_ai": bool(r.revealed_ai),
            "gt_severity_score": payload.get("gt_severity_score"),
            "gt_justification": payload.get("gt_justification"),
            "ai_severity_score": payload.get("ai_severity_score"),
            "ai_justification": payload.get("ai_justification"),
            "ai_confidence": ai_conf,  # <-- now exported
            "dilemma_text": (payload.get("dilemma_text") or "").replace("\n", " ").strip(),
        })

    if fmt == "json":
        return jsonify(rows)

    # include ai_confidence in CSV headers
    headers = [
        "response_id","participant_id","condition","trial_id",
        "answer_value","rt_ms","revealed_ai",
        "gt_severity_score","gt_justification",
        "ai_severity_score","ai_justification","ai_confidence",
        "dilemma_text"
    ]
    sio = StringIO()
    w = csv.DictWriter(sio, fieldnames=headers, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return FlaskResponse(
        sio.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=study_export.csv"}
    )

# ---------- Extend block ----------
@app.route('/study/extend', methods=['POST'])
def study_extend():
    """Assign another block of N trials to an existing participant."""
    data = request.get_json(force=True)
    pid = int(data['participant_id'])

    N = app.config.get('STUDY_TRIALS_PER_PARTICIPANT', 10)

    rows = db.session.execute(text("""
        WITH assigned_to_participant AS (
            SELECT trial_id FROM assignment WHERE participant_id = :pid
        )
        SELECT t.id AS tid, COALESCE(COUNT(a.id), 0) AS cnt
        FROM trial t
        LEFT JOIN assignment a ON a.trial_id = t.id
        WHERE t.id NOT IN (SELECT trial_id FROM assigned_to_participant)
        GROUP BY t.id
    """), {'pid': pid}).fetchall()

    if not rows:
        return jsonify({'ok': False, 'error': 'no-unassigned-trials'}), 400

    import random
    min_cnt = min(r.cnt for r in rows) if rows else 0
    candidates = [r.tid for r in rows if r.cnt == min_cnt]
    random.shuffle(candidates)
    chosen = candidates[:N] if len(candidates) >= N else list(candidates)
    if len(chosen) < N:
        remaining = N - len(chosen)
        for c in sorted({r.cnt for r in rows if r.cnt > min_cnt}):
            pool = [r.tid for r in rows if r.cnt == c and r.tid not in chosen]
            random.shuffle(pool)
            take = min(remaining, len(pool))
            chosen.extend(pool[:take])
            remaining = N - len(chosen)
            if remaining <= 0:
                break

    max_ord = db.session.execute(text("""
        SELECT COALESCE(MAX(order_idx), -1) FROM assignment WHERE participant_id = :pid
    """), {'pid': pid}).scalar()
    start_idx = (max_ord + 1) if max_ord is not None else 0

    for i, tid in enumerate(chosen):
        db.session.add(Assignment(participant_id=pid, trial_id=tid, order_idx=start_idx + i))
    db.session.commit()

    return jsonify({'ok': True, 'added': len(chosen)})

# ---------- AI suggestion payload (includes confidence) ----------
@app.get('/api/trials/<int:trial_id>/ai')
def api_trial_ai(trial_id):
    trial = Trial.query.get_or_404(trial_id)
    payload = {
        "ai_score": int(trial.ai_severity_score),
        "ai_justification": trial.ai_justification or "",
        "ai_confidence": (trial.ai_confidence if hasattr(trial, "ai_confidence") and trial.ai_confidence is not None else 0.75)
    }
    return jsonify(payload)
