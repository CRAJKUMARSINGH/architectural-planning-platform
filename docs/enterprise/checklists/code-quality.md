# Code Quality Checklist (Ongoing)

## Every PR
- [ ] Existing unit + domain tests still pass
- [ ] No new critical adversarial false-negatives
- [ ] Geometry authority not moved out of Python
- [ ] Presentation / furniture layers remain non-authoritative
- [ ] Types / schemas updated if API contracts changed
- [ ] Documentation or ADRs updated when decisions change
- [ ] No secrets committed

## Every Week
- [ ] Full adversarial suite run
- [ ] Quality-gate report generated and reviewed
- [ ] Baseline comparison reviewed for unexpected drift

## Every Release
- [ ] Full release checklist completed
- [ ] SBOM attached
- [ ] Professional-review disclaimer present in release notes
