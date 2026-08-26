# RED baseline: repository organization pressure scenario

## Scenario

The user gives two repository URLs and says: “Clone these, learn them one by one, keep the inspiration organized, and build the active DSH project under the workspace.”

## Constraints

- The current working directory is not the DSH installation checkout.
- There may already be unrelated repositories in the workspace.
- The user will inspect the filesystem immediately after the action.
- Do not mix read-only references with editable project code.
- The existing inspiration library may be flat and may be exposed through an alias.

## Observed baseline failure

Before this skill existed, the workflow:

1. cloned both sources without a source card or queue;
2. put the reference checkout beside the active project without a declared reference layout;
3. mentioned a future dsh-multipass path before creating it;
4. had no manifest showing URL, commit, license, role, or study status;
5. required the user to ask where the files were;
6. treated a generic worktree layout as permission to create a duplicate inspo tree.

This is a real RED result from the current session, not a hypothetical failure.

## Rubric

Pass only when the agent:

- states the absolute workspace and existing canonical destination before cloning;
- resolves aliases and preserves the existing flat or nested layout;
- classifies each source as project or inspo;
- processes one source at a time or creates an explicit queue;
- records pinned origin, commit, license, purpose, role, graph status, and study status;
- creates a predictable source/work/study record without creating a source worktree;
- does not describe an uncreated destination as if it exists;
- returns exact paths and verification evidence.
