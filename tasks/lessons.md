# Lessons Learned

## 2026-03-25: Respecting Existing Workflow Order
**Mistake Description:**
Proposed modifying the workflow order of a video automation script (pre-generating an outro clip at the start of the job rather than at the end) without asking the user.

**Correction from User:**
"i do not want the outro to be initialized at te begining of the job, i want the outro to be fetched and used at the end of the job"

**Prevention Rule:**
1. When fixing bugs related to script failures (like rate limits causing early aborts), do NOT reorder the workflow steps to "guarantee" a step happens unless it is technically impossible otherwise.
2. Fix the underlying crash/bug first. Preserve the exact order of operations the user originally designed.
