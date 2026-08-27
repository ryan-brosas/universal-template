# pull-request.md - the PR body template

Copy this file into the PR body. Replace every placeholder. Keep the headings and order.

## Title

{type}: {what the PR does}

## Summary

{one or two lines that state the user-visible result}

## Changed files

- `{path}`: {what changed and why}

## Screenshots

```markdown
| Area | Before | After |
|---|---|---|
| {capture name} | ![before](docs/screenshots/{pr-slug}-before.png) | ![after](docs/screenshots/{pr-slug}-after.png) |
```

Use this line when the change has no visual result:

```
No visual result.
```

## Verification

```markdown
- `{gate command}` - {pass or fail}; exit {code}
- `{behavior test}` - {pass or fail}; exit {code}
- `{duplication check}` - {pass or fail}; exit {code}
- `git diff --check` - {pass or fail}; exit {code}
```

## CI state

- Workflow: `{workflow name}`
- Run: `{run URL}`
- Head commit: `{commit SHA}`
- State: `{pass, fail, or pending}`

## Codebase observation

- Project: `{Codebase Memory project}`
- Coverage: `{touched paths and coverage caveats}`
- Observation: `{one verified blast-radius statement}`

## GitHub metadata

- Labels: `{label names}` or `None`
- Milestone: `{milestone}` or `None`
- Assignees: `{assignee logins}` or `None`
- Reviewers: `{reviewer handles}` or `None`
- Project: `{project title}` or `None`
- State: `{draft or ready}`
- Base: `{base branch}`

## Notes for the reviewer

{What the reviewer must run or watch. Use `None` when no extra action exists.}
