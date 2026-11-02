# Architecture Decision Log

Ecosystem-wide architecture decisions of Ingots. Process and format are
described in [0001](0001-record-architecture-decisions.md); new records start
from [template.md](template.md).

The domains tell what a record is about, and whom it concerns, one or several:
`process` how the ecosystem works, `tooling` platforms, layout and builds,
`design` the code of every package; a topic such as `grpc` concerns only the
packages dealing with it, and appears when the first record needs it. They are
metadata, like the status: they may change in a record already accepted.

| # | Decision | Domains | Status |
|---|---|---|---|
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | process | Accepted |
| [0002](0002-target-linux-macos-as-by-product.md) | Target Linux; macOS as a by-product | tooling | Accepted |
| [0003](0003-flat-layout-and-mandatory-library-build.md) | Flat layout; libraries are tested as built wheels | tooling | Accepted |
| [0004](0004-static-composition-with-typed-slots.md) | Static composition of extensions with typed slots | design | Accepted |
| [0005](0005-addons-ship-contract-tests.md) | Addons ship contract tests; consumers run them | design, tooling | Accepted |
| [0006](0006-design-principles.md) | Design principles: SOLID, DRY, KISS, YAGNI, the Zen of Python | design | Accepted |
| [0007](0007-code-layout-and-naming.md) | Code layout and naming | design | Accepted |
| [0008](0008-move-dependents-along-the-tree.md) | Move the dependents of a package along the tree | process, tooling | Accepted |
| [0009](0009-name-grpc-contracts-apart-from-the-layout.md) | Name the gRPC contracts of addons apart from their layout | grpc, tooling | Accepted |
| [0010](0010-keep-contracts-under-testing.md) | Keep the contracts of a package under testing | design | Accepted |
| [0011](0011-mirror-the-packages-of-grpc-contracts.md) | Mirror the packages of the gRPC contracts in their paths | grpc, tooling | Proposed |
