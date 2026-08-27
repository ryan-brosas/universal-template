# readme.md - the repository README template

Copy this file into a new repository as README.md. Replace every placeholder.
Keep the headings and order. Delete a section only when the project has no
equivalent content. The badge URLs match the badges in the CI workflow that
`github-pr-ci.yml` produces.

<div align="center">

# {repo-name}

**{one-line tagline: what the project is}**

_{one sentence that states the user-visible outcome}_

[![CI](https://img.shields.io/github/actions/workflow/status/{owner}/{repo}/{workflow-file}?branch={default-branch}&style=for-the-badge&label=checks)](https://github.com/{owner}/{repo}/actions/workflows/{workflow-name}.yml) [![{registry}](https://img.shields.io/{registry}/v/{package-name}?style=for-the-badge&logo={registry})](https://{registry-domain}/package/{package-name}) [![Node.js](https://img.shields.io/badge/{language}-{version}-339933?style=for-the-badge&logo={language}&logoColor=white)](package.json) [![license](https://img.shields.io/badge/license-{license}-f4c430?style=for-the-badge)](LICENSE)

</div>

## Run

```sh
{one command that starts the project}
```

{Two sentences: what the command does and where the output or UI lands. State
the default address and which flag overrides it.}

## Why {repo-name}?

| | Capability | What it unlocks |
| :-: | --- | --- |
| {emoji} | **{capability}** | {what the user can do because of it} |
| {emoji} | **{capability}** | {what the user can do because of it} |
| {emoji} | **{capability}** | {what the user can do because of it} |

## How it fits

```mermaid
flowchart LR
  {Entry}[{Entry}] --> {Next}[{Next}]
  {Next} --> {Store}[({Store})]
```

{One paragraph: which layer owns what, and where the composition root lives.}

## Install

### Run without installing

```sh
{command without install}
```

### Install the command

```sh
{install command}
{command} {subcommand}
```

### Run from source

```sh
git clone https://github.com/{owner}/{repo-name}.git
cd {repo-name}
{package-manager} install
{package-manager} run build
{start command}
```

## Usage

```sh
{command} --help
{command} {subcommand} {arg}
```

{Where configuration lives, which source wins on conflict, and which commands
read or write it.}

## Documentation

- {guide name}: `docs/user/guide/{name}.md`
- {architecture}: `docs/{name}.md`
- {development}: `docs/{name}.md`
- [Discussions](https://github.com/{owner}/{repo-name}/discussions)

> [!WARNING]
>
> {project state warning: what may change before the first stable release}

## License

{license} {copyright}. Third-party licenses are listed in THIRD_PARTY_NOTICES.md
when they exist.
