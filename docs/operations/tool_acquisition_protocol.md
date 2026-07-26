# HomeAura tool acquisition protocol

Version: 1.0

## Rule

Do not install a missing tool merely to satisfy a test. Diagnose the gap and
create a simulated or real `TOOL_REQUEST` for ChatGPT review.

## Procedure

1. State the missing capability and exact job impact.
2. Record how absence was verified and when.
3. Name the candidate tool without downloading it.
4. Provide only an official vendor/project source for ChatGPT to verify.
5. State required rights: standard user, administrator, application restart,
   or system restart.
6. State data/security implications.
7. Provide a rollback approach.
8. Give the user a short, exact action only after ChatGPT approves.
9. Re-run the smallest safe test after installation.
10. Update the capability matrix with factual evidence.

## Required TOOL_REQUEST fields

- request_id
- job_id
- status (`SIMULATED_ONLY`, `PENDING_REVIEW`, `APPROVED`, `REJECTED`)
- missing_capability
- purpose
- verification_method
- candidate_tool
- official_source_for_chatgpt_review
- required_rights
- restart_required
- security_notes
- rollback
- user_instruction

## Stop conditions

Stop without workaround when the acquisition path presents CAPTCHA, 2FA,
account sign-in, device confirmation, UAC, a security/privacy permission
prompt, an unverified download source, or a destructive action.
