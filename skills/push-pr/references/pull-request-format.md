# PR body format and push rules

The PR body uses this section order:

1. Title
2. Summary
3. Changed files
4. Screenshots
5. Verification
6. CI state
7. Codebase observation
8. GitHub metadata
9. Notes for the reviewer

Fill each section with a fact. Use `No visual result.` in the Screenshots section for text-only changes. Keep the headings and order.

## Screenshots

- Capture the changed UI before and after when both states exist.
- Save images under `docs/screenshots/` with the PR slug in the file name.
- Use relative image paths.
- Use one row per changed visual area.
- State `No visual result.` when the change has no visual output.

## Verification

List each command and its exit status. Include the project gate, the behavior test, the duplication check, and `git diff --check` when they apply.

## CI state

Write the workflow name, run URL, head commit, and final state. Use `pending` only while the run is active. Update the PR body after the pull request run finishes.

## Codebase observation

Write the Codebase Memory project, coverage for touched paths, caveats, and one blast-radius observation. Write a skip reason when the server is unavailable.

## GitHub metadata

Write the label, assignees, milestone, reviewers, project, draft state, and base from the project `AGENTS.md` or the task page. Use the literal `None` for a field that has no value.

Set the metadata when you create the PR. The `gh pr create` flags are repeatable `--label` and `--reviewer`, then `--milestone`, `--assignee`, `--project`, and always `--base`. Pass `--draft` while the run is still open.

Confirm the result with `gh pr view <number>` after creation. Add a missing value with `gh pr edit --add-label <name> --milestone <name>`.

## Push order

Add only owned files. Use the commit convention from the project `AGENTS.md`. Push the branch. Watch the push run. Create the PR after a passing push run, or create one with `--draft` while the CI run is open. Set the labels, milestone, assignees, reviewers, and project during creation, then confirm with `gh pr view`. Watch the pull request run and update the body and the CI state.
