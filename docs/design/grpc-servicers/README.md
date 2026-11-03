# ingot-grpcio: the servicers, the services and their binding to servers

Status: a comparison for a decision, written on 2026-10-25 over the branch
`grpc-server` (staged, not committed); not an ADR.

## The question

What does `grpc.api` register: the implementations (servicers) or the
services, with the implementation as a part of a service? And then: how
does a server pick what it serves?

## (a) The servicer holds the service info (as now)

```python
ECHO = GrpcServiceInfo("tst.Echo", tst_pb2_grpc)   # GrpcService today


class Echo(GrpcServicer, tst_pb2_grpc.EchoServicer):   # an Entity
    SERVICE = ECHO

    async def Unary(self, request, context): ...


class AppGrpcApi(GrpcApi):
    echo = Slot(Echo)
```

## (b) The service holds its servicer, and the API registers the service

```python
class EchoService(GrpcService):                     # a Unit
    INFO = GrpcServiceInfo("tst.Echo", tst_pb2_grpc)
    servicer = Slot(Echo)                           # Echo has no SERVICE


class AppGrpcApi(GrpcApi):
    echo = Slot(EchoService)
```

The service is a unit, not the info object with the servicer as a
constructor parameter: a slot takes a class, and only a class can be
overridden by a subclass. The info object stays as it is, plain, under
the name the TODO asks for: `GrpcServiceInfo`.

## The comparison

| | (a) servicer holds the info | (b) service holds the servicer |
|---|---|---|
| Classes per service | 1: the servicer | 2: the service unit and the servicer |
| What `grpc.api` is | a registry of implementations | a registry of services (the contract), each with its implementation |
| Replacing an implementation | `echo = Slot(AppEcho)` in the API | `servicer = Slot(AppEcho)` in a subclass of the service, then `echo = Slot(AppEchoService)` in the API: one level more |
| Path to the implementation | `grpc.api.echo` | `grpc.api.echo.servicer` |
| Checks | the servicer extends the generated base (at class creation); one servicer per service in the API | the servicer slot extends the base of `INFO` (at class creation of the service); one service per name in the API |
| mypy over the RPC methods | the servicer extends the generated base | the same |
| A service without an implementation (client side only) | not in the API: the info constant alone | a service unit without a servicer; a server must refuse it |
| Per-service settings (interceptors, auth, tags for a binding, version) | on the servicer, mixed with the RPCs | on the service unit, apart from the RPCs |
| What a binding strategy selects | servicers | services |
| The export of the API (FileDescriptorSet) | from `SERVICE` of every servicer | from `INFO` of every service |
| The link "proto + servicer base + stub" you asked for | split: the info constant and the servicer | in one place: the service unit |
| Cost of a change later | (a) → (b) breaks every servicer and API | (b) → (a) breaks every service and API |

**Pros of (a):** less to write; the shortest path to the code that runs;
what is on the branch, tested.

**Cons of (a):** the API mixes "what we offer" with "how it is done";
anything per service has nowhere to live but the servicer.

**Pros of (b):** the API is the contract, which the export, the clients
and the binding strategies all work on; a per-service home; a service can
be declared before (or without) an implementation.

**Cons of (b):** one more class per service and one more level to override
an implementation; the server has to handle a service without a servicer.

My leaning: (b), mildly. The binding strategies tip it: a server
naturally picks *services* to expose, and tags or names for a strategy
belong to the service, not to its RPCs. If per-service settings never
appear, (a) is enough and cheaper.

## The binding: strategies

The TODO in `DefaultGrpcServer._iter_servicers` turns the open question
(1:N or many-to-many) into strategies: each policy is a class, and an
application picks one per server. The question stops being a choice of
the design.

- `AllOfApiGrpcBinding`: everything in `grpc.api` (today's logic, the
  default).
- `ByNameGrpcBinding`: the services listed by full name (`SERVICES = (...)`)
  on the server or the binding.
- Later, if asked: by tag of the service, which needs (b).

**Your two options:**

- (a) `for servicer in self._iter_servicers()`: the hook stays the only
  contract of `BaseGrpcServer`.
- (b) `for servicer in self.services_binding.iter()`: the server depends
  on a binding object.

My leaning: both at once. The hook stays the contract of the base, and
`DefaultGrpcServer._iter_servicers()` delegates to its strategy. A server
with a policy of its own still overrides the hook, and the others take a
strategy without writing code.

**Where the strategy lives:**

| | How | Note |
|---|---|---|
| A class attribute | `BINDING: ClassVar[type[GrpcBinding]] = AllOfApiGrpcBinding`, instantiated with the server | works today; overridden by a subclass of the server |
| A slot of the server | `binding = Slot(AllOfApiGrpcBinding)` | the PUER way, but a component holds no slots today: `Unit = SlotsOwner + Entity`, `Component = Entity`; needs a component owning slots in `ingots` |
| A unit next to the servers | `grpc.bindings.default`, matched to the server by name | an implicit link by name; not recommended |

Start with the class attribute. Move to a slot if components owning slots
appear in `ingots` for another reason.

## Your suggestions on the branch

- **`GrpcService` → `GrpcServiceInfo`.** Yes. It describes a service and
  does not serve one, and under (b) it frees `GrpcService` for the unit.
- **Named variables in place of `names[0..2]`.** Yes, it reads better.
- **`add_to_server` → registrator.** The stored callable may be a noun,
  `_registrar` (the English word; "registrator" is rare), but the public
  method stays a verb (ADR 0007). Keep `add_to_server`, the name grpcio
  gives it, or `register(servicer, server)`.
- **The binding strategies.** Agreed, as above.

## Update: the bindings unit (the user's draft)

```python
grpc.api        # what is implemented
grpc.bindings   # the policy: which services each server exposes
grpc.servers    # the connections: where they are served
grpc.clients    # later: the stubs of a server's services, from its binding
```

Every server has a binding of its own, an entity in `grpc.bindings`
under the same name (`servers.default` with `bindings.default`). The
binding is defined outside the server. The same map gives the client
SDKs: the services each server exposes, by server.

This replaces the table above on where the strategy lives. Each server
names its binding explicitly, as it names its configs, so nothing is
matched by name implicitly:

```python
class DefaultGrpcServer(BaseGrpcServer):
    @t.override
    def _iter_servicers(self):
        return self.project.grpc.bindings.default.iter_servicers()
```

It also sidesteps the limitation that a component holds no slots: a
binding is an entity in a unit, which is how ingots works anyway.

## Decided (2026-10-25): (b) without the extra level

The service is an entity in a slot of the API that names its
implementation by a class attribute, not a slot. The path stays
`grpc.api.echo`:

```python
class EchoService(GrpcService):        # an Entity in a slot of GrpcApi
    INFO = GrpcServiceInfo("tst.Echo", tst_pb2_grpc)
    SERVICER = Echo                    # Echo(GrpcServicer, tst_pb2_grpc.EchoServicer)
```

The servicer extends the generated base directly, for mypy. The service
creates it once, with the project. Each server serves the binding of its
name. A binding replacing `bindings.default` extends `AutoGrpcBinding`,
because the slots of ingots require a class that extends the classes of
all bases, as for the servers.

## Then (2026-10-25): no info object at all

`GrpcServiceInfo` was ceremony: a constant declared once, then given to
the service as `INFO = ...`. The service class does its job itself. The
name and the module are arguments of the class, because mypy reads
`MODULE = module` in a class body as a module alias, not as a value:

```python
class EchoService(GrpcService, full_name="tst.Echo", module=tst_pb2_grpc):
    SERVICER = Echo
```

The class finds `DESCRIPTOR`, `SERVICER_BASE` and `STUB` when it is
created. `SERVICER` is optional: a contract alone serves the clients of a
server written in Go or Rust.

mypy narrows `SERVICER` to the class first assigned. So a refined
implementation subclasses the service (`AppEcho(Echo)`), and another
implementation altogether subclasses the contract.

## Proposed order

1. Decide (a) or (b).
2. Change the branch `grpc-server`: the rename to `GrpcServiceInfo`, the
   named variables, (b) if chosen, and `GrpcBinding` with
   `AllOfApiGrpcBinding` as the default of `DefaultGrpcServer`.
   `ByNameGrpcBinding` comes in its own PR, or in this one if small.
3. The PR.

## Decided (2026-10-25, the clients): bindings are mixins of descriptors

The binding as a policy at run time made a client guess: it checked a
stub against the local binding, while the server it calls may be
another version with another binding. The user's sketch replaced it: a
binding is a plain class of `GrpcService` descriptors, and a server and
its client both extend it.

```python
class AppGrpcBinding:
    echo = GrpcService(demo_pb2_grpc.EchoStub, Echo)

class AppGrpcServer(AppGrpcBinding, DefaultGrpcServer): ...
class AppGrpcClient(AppGrpcBinding, DefaultGrpcClient): ...

reply = await (await clients.default).echo.Say(request)
```

- The descriptor gives each side its own, typed by overloads of
  `__get__`: `server.echo` the servicer, one per server, created with
  the project; `client.echo` the stub, one per client, created on its
  channel when it is configured (`RuntimeError` before); on the class,
  the service itself.
- The stub type is a `Callable[[aio.Channel], Stub]`: the runtime class
  `EchoStub`, which mypy resolves to `EchoAsyncStub` through the
  overloads of `__new__` of mypy-protobuf (the async class exists for
  the type checker only).
- From the stub the service finds the `_pb2_grpc` module, the servicer
  base, the registrar and the descriptor (through the `_pb2` module the
  generated code imports): no `full_name` argument.
- A servicer is optional: a contract alone serves a client; a server
  refuses it when the class is created.
- `GrpcServicesOwner` indexes the services in MRO order; a replacement
  keeps the contract and refines the servicer, as a slot does. mypy
  sees a non-refining replacement too. A contract replaced by an
  implementation needs a `type: ignore` (its servicer type is `Never`).
- `grpc.api` and `grpc.bindings` are gone; a component holds no slots,
  and the descriptors are no slots, so ingots needs nothing new. The
  export will walk the descriptors of the servers.
