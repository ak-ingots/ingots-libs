# 0012. Design a feature before building it

- Status: Proposed
- Domains: process
- Date: 2026-11-02
- Deciders: Aliaksandr Karotki
- Supersedes / Superseded by: —

> In the context of **features of the framework and its addons, used by
> developers more than by end users**, facing **designs reworked in pull
> request after pull request as their consumers turned up**, we decided for
> **a design document per feature, its stories accepted by the code of their
> consumers in a prototype checked by mypy**, and against **designing in the
> code, or in conversation alone**, to achieve **an API that fits its
> consumers before it is built**, accepting **the time the document takes**.

## Context

The policies of ingot-auth went through about ten designs in a day: a value
became a context, names became classes, presets moved from the core to the
methods, a pull request brought code nothing called. Each turn came from a
consumer nobody had written down: the history of a password, a client
checking a form, mypy catching a wrong binding, an application adding one
policy. Two things found those turns quickly: walking a story as code ("I add
a policy: what do I write?") and a prototype run through mypy. Both came after
the code instead of before it.

ADRs record decisions across repositories; a feature inside an addon needs a
lighter document, written before its code.

## Decision drivers

- Find the consumers of an API before the API, while a change costs minutes.
- The users of a framework are developers: a story is accepted by code.
- Keep the rejected options, so they are not proposed again blindly.
- No more process than a feature needs.

## Considered options

1. Design in the code and rework in review, as so far.
2. User stories alone, in the description of an issue.
3. A design document per feature from a template, with a prototype.

## Decision

Option 3. A feature that adds or changes an API, a flow or a domain of a
package gets a design document before its code:

- It lives in `docs/design/<topic>/README.md` of this repository, for a
  feature may touch several, from [the template](../design/template.md),
  its sections optional, its prototypes in
  `docs/design/<topic>/<concept>/`, checked one by `make check-prototype`
  while it is written, all by `make check-prototypes` in CI.
- Its stories are told by actor: the author of an application, of an addon
  or a contrib, of a client, an operator, the end user. A story taken is
  accepted by the code its actor writes, run in the prototype; mypy must
  refuse what is marked `# error:`.
- It finds the domain first, its events and states, and draws a flow of more
  than one step as a sequence; Mermaid, as GitHub renders it.
- A package of the auth or of the data of users adds its threats by STRIDE.
- It is done when the user accepts it, its status `Accepted`; the code is
  then built in slices, a pull request each with its first consumer, a thin
  path through every layer first.
- A design is not an ADR: it may change while built, and its status becomes
  `Built`. A decision in it that spans repositories becomes an ADR.
- A fix, a rename, a move of code or a change of one function needs none.

## Consequences

### Positive

- The consumers of an API are written before it, and a wrong turn costs a
  prototype, not a pull request.
- The stories left for later say what the API must not shut out.
- The reasons of a design stay in one place, whatever repositories it
  touches.
- A small feature fills a few sections, a large one all of them, and shows
  the size of the work by that.

### Negative

- A feature takes a document and a prototype before its first line of code.
- Prototypes kept for `make check-prototypes` age as the packages move on;
  a design built is a snapshot, not maintained. CI checks them all until
  that gets in the way; the problem met then decides what changes.

## Links

- [Template](../design/template.md).
- [ADR 0001](0001-record-architecture-decisions.md): records and their
  lifecycle.
- [Extension composition](../design/extension-composition/README.md): a
  design with prototypes, made for ADR 0004.
- Tom Preston-Werner, "Readme Driven Development" (2010).
- Alberto Brandolini, "Introducing EventStorming" (2013).
- Matt Wynne, "Introducing Example Mapping" (2015).
- Adam Shostack, "Threat Modeling: Designing for Security" (2014).
- Andrew Hunt, David Thomas, "The Pragmatic Programmer": tracer bullets.
