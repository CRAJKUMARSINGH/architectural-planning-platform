# Week 24 independent professional review instructions

This package is a blinded review aid for the Advocate-Chambers planning
validation system. It is not an architectural approval, permit decision, or
construction certification. Reviewers must use their professional judgment and
the applicable code, fire/life-safety, accessibility, structural, MEP, survey,
and local-authority requirements.

## Pack

The reviewer-facing pack is:

`tests/fixtures/professional-review/week24-review-pack.json`

It contains 25 models:

- 10 valid plans
- 10 intentionally defective plans
- 5 borderline or incomplete-input plans

The case IDs are blinded. Do not open
`bar-association-hall/standard/week24-software-answer-key.json` until all
independent scorecards are complete; it is the software answer key, not
reviewer evidence.

## Procedure

1. Each reviewer works independently from the blinded pack.
2. Record one standard form for every `BLIND-###` case.
3. Classify each case as `usable`, `not_usable`, or `uncertain`.
4. Score access, room adjacency, dimensional credibility, stairs/exits,
   drawing clarity, furniture/circulation, missing assumptions, and confidence.
5. For every critical problem, record the affected object, evidence, rule or
   calculation used, and the suggested correction.
6. Record whether the software finding can be reproduced from the model,
   geometry, rule ID, and calculation.
7. Record every disagreement between reviewers. Critical disagreements require
   a written resolution or an explicit unresolved status.
8. Anonymize reviewer identifiers as `REVIEWER-A`, `REVIEWER-B`, or another
   stable pseudonym before committing results.

## Acceptance thresholds

The professional-review track can pass only when all conditions are true:

- At least two independent reviewers completed the pack.
- At least 90% agreement exists for usable/not-usable classification.
- No critical defect is accepted as usable by both reviewers.
- Every critical disagreement is documented.
- Reviewers can reproduce every critical software finding.

Until those conditions are evidenced, the result must remain
`REVIEW_REQUIRED`. The generated Week 24 artifact intentionally uses that
status and contains two pending reviewer slots rather than fabricated human
results.