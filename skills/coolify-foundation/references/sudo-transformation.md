<!-- capsule-v2 -->
# Sudo transformation — how do commands get sudo-prefixed for non-root servers without breaking pipelines?

**Source:** Coolify Apache-2.0 `main@379abb252621f34b318190bd49b614aed9818716`; Codebase Memory `ext-coolify`. **Question:** Prefixing every line with `sudo` breaks `cd`, pipes, and command substitutions — what is the actual transformation algorithm and its known regression?

## parseCommandsByLineForSudo / parseLineForSudo / shouldChangeOwnership
**Path/Symbol:** `bootstrap/helpers/sudo.php:parseCommandsByLineForSudo` (lines 23–130), `parseLineForSudo` (131–153), `shouldChangeOwnership` (7–22).
**Signature:** `function parseCommandsByLineForSudo(Collection $commands, Server $server): array`, `function parseLineForSudo(string $command, Server $server): string`.
**Data Shape:** Input: array/Collection of command lines; output: transformed lines. Ownership rule applies only under `/data/coolify` or `/tmp/coolify`.

### Decisive source
```php
foreach ($bashKeywords as $keyword) {           // cd, echo, export, if, fi, for, while, do...
    if (preg_match('/^'.preg_quote($keyword, '/').'(\s|;|$)/', $trimmedLine)) {
        if ($keyword === 'if') return preg_replace('/^(\s*)if\s+/', '$1if sudo ', $line);
        return $line;                            // keyword lines get NO sudo prefix
    }
}
return "sudo $line";
...
$isComplexPipeCommand = ($line->contains(' | sh') || $line->contains(' | bash') ||
    $line->contains(' sh -c ') || ($line->contains(' | ') && ($line->contains('||') || $line->contains('&&'))));
if ($isComplexPipeCommand && $line->startsWith('sudo ')) {
    ... return "sudo bash -c '$escapedCommand'";
}
```

**Flow:** line-level pass 1: comments untouched; bash-keyword lines skipped (word-boundary regex avoids the classic `do`/`docker` collision); everything else gets `sudo `. Pass 2: `sudo mkdir -p <coolify-path>` gains `&& sudo chown -R user:user path && sudo chmod -R o-rwx path`. Pass 3: complex pipe commands are rewrapped as a single `sudo bash -c '...'` (sudo must wrap the WHOLE pipeline, not per-segment); simple commands get sudo injected after `$(`, `||`, `&&`, and around `| `. The single-line variant parseLineForSudo (used by ExecuteRemoteCommand) is simpler but currently BROKEN — see invariant.
**Invariant:** The whole point: `a | b > c` with naive per-segment sudo elevates the wrong segments or loses shell syntax; wrapping in `sudo bash -c` preserves semantics. REGRESSION at pin: `parseLineForSudo` calls `str($command)->startSwith(...)` — misspelled method introduced upstream in commit `0d23b297` (2026-08-18 "honor GitHub default branches...") which replaced the old logic; no definition of startSwith exists in this tree's Laravel Stringable surface, so on a non-root server any non-`docker exec` command now throws Error (call_as_macro not found) when ExecuteRemoteCommand hits that branch. Porters must implement the keyword/pipe algorithm, NOT copy this function verbatim.
**Probe:** `tests/Unit/ParseCommandsByLineForSudoTest.php::wraps_complex_Docker_install_command_with_pipes_in_bash_c` pins `"sudo bash -c 'curl ... | sh || curl ... | sh'"`; second test forbids `$(sudo if` inside wrapped backups scripts. Regression probe: `grep -c "startSwith" bootstrap/helpers/sudo.php` → 1 line (line 133 carries both occurrences).
**Retrieve:** search_graph project ext-coolify query "parseLineForSudo parseCommandsByLineForSudo sudo" resolves all three functions in bootstrap/helpers/sudo.php.

## Verdict
Adopt the three-pass transformation + ownership policy as portable behavior; treat parseLineForSudo's typo as an upstream bug to fix on port (use startsWith semantics); omit server-model coupling.
