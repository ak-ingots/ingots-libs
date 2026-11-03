# ingot-grpcio: the errors of the calls as a part of the API

Status: ideas, written on 2026-10-25 while the branch `grpc-errors` waits.
The "Decided" sections are what the branch does.

## Where we are (the branch)

- The handlers raise the exceptions of the business logic and see no
  protobuf.
- A codec in `grpc.errors` encodes an exception into a
  `google.rpc.Status`: a code, a message, an `ErrorInfo` of its domain,
  reason and metadata, and the details it gives. A client decodes it back
  by `(domain, reason)`.
- `InternalGrpcErrorCodec` takes every other exception.
  `GrpcErrorsInterceptor` encodes the errors on the server.
- A server takes its interceptors, the middleware of gRPC, from
  `_iter_interceptors()`.

## The idea: the errors of a service in its .proto

The error protos, and only they, are the business API of the errors,
next to the services. Each service declares the errors it may return.
Its reasons are a nested enum, so proto3 needs no prefixes: a nested enum
is scoped by its message, and only top-level enum values clash in a
package. Its contexts are nested messages:

```proto
service Echo {
  rpc Say (EchoMessage) returns (EchoMessage);
}

message EchoError {                 // found by name: <Service>Error
  enum Reason {
    UNSPECIFIED = 0;
    TOO_LOUD = 1;
    NOT_FOUND = 2;
  }

  message TooLoud {                 // the context of TOO_LOUD, by name
    int32 max_volume = 1;
  }
}
```

- On the wire: `ErrorInfo.domain = "demo.Echo"` (the full name of the
  service) and `reason = "TOO_LOUD"`. The pair is unambiguous.
- `GrpcService` finds `<Service>Error` in the file of the service, as it
  finds `<Service>Servicer` and `<Service>Stub`: its `Reason` enum and its
  contexts, by the CamelCase name of a reason.
- The context is typed and packed into the details, in place of the
  `map<string, string>` of `ErrorInfo.metadata`: numbers, nested
  messages, versioning by the rules of protobuf.
- SDKs in any language get the reasons and the contexts from the same
  `.proto`. The export of the services (a FileDescriptorSet) carries them
  with no more work: they are in the files of the services.
- The interceptor knows the method, so the service: a reason outside its
  `<Service>Error` breaks the contract. It is logged as an error and sent
  as `INTERNAL`, as an exception with no codec is.
- Errors common to many services (unauthenticated, account locked) go in a
  package-level message of the same shape, `ShopError`, whose domain is
  the package.
- `buf lint`: `ENUM_VALUE_PREFIX` (STANDARD) asks for `REASON_` on nested
  enums too. It can be switched off: nested values do not clash.

## Decided for now (2026-10-25)

Start with the standard of `google/rpc/error_details.proto`:
`ErrorInfo.reason` within its `domain` is the code of the error,
`ErrorInfo.metadata` its context, and the standard details carry the rest
(`ResourceInfo`, `QuotaFailure`, `PreconditionFailure`, `BadRequest`,
`RetryInfo`, `Help`, `LocalizedMessage` for a user). This is what the
branch does. No contexts of our own: the user said "не будем выдумывать
контекстов". The idea of `<Service>Error` below stays an idea.

`Status.message` is for a developer and `LocalizedMessage` for a user, so
the default `_get_message()`, `str(error)`, serves developers only.

## Decided on the branch (2026-10-25)

- The codecs became **policies**, a strategy ("Strategy, also known as
  Policy"): `BaseGrpcErrorPolicy` is the interface (`EXCEPTION`,
  `LOG_LEVEL`, `LOG_EXC_INFO`, final `encode()` over the hook
  `_encode()`); `BaseStaticGrpcErrorPolicy` declares the status in
  constants (`CODE`, `DOMAIN`, `REASON`, `_get_message`, `_get_metadata`,
  `_iter_details`). A policy with ifs (MySQL's `IntegrityError` by errno)
  is a policy of its own on the interface: no `_get_code` hook.
- The logging of an error is declared per policy, `LOG_LEVEL` (a constant
  of `logging`) and `LOG_EXC_INFO`: one error wants `WARNING` with its
  traceback, another `ERROR` without.
- `GrpcErrors` only groups: `handler = Slot(GrpcErrorHandler)` and the
  policies, with the index by exception and the checks at import time.
  The handler's `handle(error, method, *, is_debug_info)` finds the policy
  once, encodes, logs (`_log`, overridable) and adds the `DebugInfo`: a
  policy cannot send a traceback.
- A client stops at `GrpcError`: server classes stay on the server. No
  index by reason, no decoding by the policies; a static policy still may
  not share its domain and reason with another. `decode_rpc_error()`
  stays on the handler until the clients: then it moves to a client
  handler called by a client interceptor (`ServerGrpcErrorHandler` and
  its client pair).
- The errors interceptor stays in `_iter_interceptors()` of the default
  server, not hidden in a final flow: a subclass dropping it gets grpcio's
  `UNKNOWN "Unexpected <class ...>: <text>"`, which the docstring of the
  hook says.

## Open

Items 3 and 4 are decided above; 1 and 2 belong to the idea of
`<Service>Error`.

1. **One exception, two services.** If both `Users` and `Signup` raise
   `EmailTaken`, these are two reasons in two enums. Then a codec maps
   "service + exception", not an exception alone, and the registry of the
   codecs moves into the services, or takes the service into account.
2. **The codec.** `REASON = demo_pb2.EchoError.Reason.TOO_LOUD`, with
   `DOMAIN` from the service, and `CONTEXT` found by name or declared. The
   hooks become `_build_context(error)` and `_decode(message, context)`.
3. **The status code** may depend on the exception, as for MySQL's
   `IntegrityError` (1062 is `ALREADY_EXISTS`, 1452 is
   `FAILED_PRECONDITION`): a hook `_get_code(error)` defaulting to `CODE`.
4. **System interceptors.** Make `GrpcErrorsInterceptor` non-optional, the
   outermost in the final flow of `BaseGrpcServer`, with
   `_iter_interceptors()` for the user's own only. A subclass forgetting
   `super()` would otherwise lose it silently, and grpcio would then send
   `UNKNOWN "Unexpected <class 'RuntimeError'>: <the text>"`, checked on
   grpcio 1.84.
