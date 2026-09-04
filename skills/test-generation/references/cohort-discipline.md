# Cohesive test changes

Source: Sewer56 and scarywood75, 2026-08-03; distilled from the original
discussion transcript and qualified against repository policy.

## Cohorts

Group broad test work into coherent themes when that makes review, diagnosis,
and rollback easier. A cohort is an organizational aid, not a mandatory PR size
or file-length threshold. Keep naturally cohesive code together.

## Scratch-tool promotion

A scratch script can become a maintained helper when repeated use establishes a
stable interface and its deterministic result is worth the ownership cost.
Promote the smallest reusable mechanism and test its exact contract. Do not
create a CLI merely to make an agent follow a preferred process.

## Adoption boundary

Select outside test patterns for the failure class they catch, not repository
popularity. Adapt only the relevant pattern, verify that it fails against the
unfixed behavior when practical, and avoid importing a parallel suite that
competes with the project's existing test owner.
