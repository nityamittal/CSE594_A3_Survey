SELECT
  p.condition,
  AVG(ABS(json_extract(r.answer, '$.value') - json_extract(t.payload, '$.gt_severity_score'))) AS avg_abs_err,
  COUNT(*) AS n
FROM response r
JOIN participant p ON p.id = r.participant_id
JOIN trial t ON t.id = r.trial_id
GROUP BY p.condition;
