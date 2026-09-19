# Week 24 standard review form

Submit one record for each blinded case. Use only the blinded case ID in the
review data; do not store names, emails, or other unnecessary personal data.

## Case record

```json
{
  "reviewerId": "REVIEWER-A",
  "blindedCaseId": "BLIND-001",
  "classification": "usable | not_usable | uncertain",
  "confidence": 0.0,
  "scores": {
    "accessCorrectness": "pass | concern | critical",
    "roomAdjacencyQuality": "pass | concern | critical",
    "dimensionalCredibility": "pass | concern | critical",
    "stairAndExitQuality": "pass | concern | critical",
    "drawingClarity": "pass | concern | critical",
    "furnitureAndCirculationQuality": "pass | concern | critical",
    "missingAssumptions": "none | concern | critical"
  },
  "criticalFindings": [
    {
      "ruleId": "RULE.ID.OR.NONE",
      "affectedObjects": [],
      "evidence": {},
      "suggestedCorrection": "",
      "softwareFindingReproduced": true
    }
  ],
  "notes": ""
}
```

## Disagreement record

```json
{
  "blindedCaseId": "BLIND-001",
  "reviewerA": "usable",
  "reviewerB": "not_usable",
  "critical": true,
  "resolution": "document the evidence, discussion, and final disposition"
}
```

The aggregate result must include reviewer count, plans reviewed, usable/not-
usable agreement, critical defects accepted as usable, reproducibility, and
all critical disagreements. A professional reviewer may mark a case
`uncertain`; uncertainty is not a passing approval.