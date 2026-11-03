# Moving ingot-pymongo to the new Ingots

Status: a plan, written on 2026-10-25 from the code of the current solution
(`abkarotki/ingot-pymongo`, 0.9.0 on ingots 0.29); not an ADR, nothing built
past the layout. To talk through, then a pull request per step.

## What the current solution does

About 570 lines, the most of them the old framework's ceremony (generic
type variables, extension managers, `register_extensions`).

| Part | What |
|---|---|
| `PyMongoUnit` → `ConnectorsUnit` | `project.pymongo.connectors`, a unit of connectors |
| `BaseConnectorComponent` | a component holding an `AsyncMongoClient` (the async API of PyMongo, not Motor): `configure()` creates it, `shut_down()` closes it; `get_database(name)`, `make_session()` |
| `DefaultConnectorComponent` | the connector of `MONGODB_DEFAULT_*`: properties `config_host`, `config_port`, `config_user`, `config_password`, `config_force_connect` |
| another connector | a subclass reading `MONGODB_<NAME>_*`, added to a subclass of `ConnectorsUnit` (the demo: `cmp_demo_cls`) |
| `ListConnectorsCommand` | `pymongo connectors list`: name, class, host, port, user of every connector |
| configs | `MONGODB_DEFAULT_HOST` (`localhost`), `_PORT` (27017), `_USER`, `_PASSWORD` (secure), `_FORCE_CONNECT` (false); `LOGGING_INGOT_PYMONGO_LEVEL` |
| `py_bootstrap` | templates of an application and an extension for the old bootstrap tool |
| tests | the configs of the connectors and the list command; no database |

Found on the way:

- The URI is concatenated: `mongodb://{user}:{password}@{host}:{port}`,
  without `quote_plus`. A password with `@`, `:` or `/` breaks it.
- The connection parameters are logged at INFO with the URI, password
  included.
- Without a user, the host is passed as the URI and the port separately;
  replica sets, SRV, TLS, `authSource` and the other options are out of
  reach.
- Usage goes through the client's internals (`connector.get_database`); the
  demo SDK looks the connector up by an alias string.

## In the new Ingots

The same shape as ingot-grpcio's servers: a unit of components, a base with
hooks, a default one on `MONGODB_DEFAULT_*`, others side by side.

```python
project.mongodb                      # MongoDbUnit
project.mongodb.clients.default      # MongoDbClients: default = Slot(DefaultMongoDbClient)
```

```python
class BaseMongoDbClient(Component):
    SHUTDOWN_ORDER = 8               # a store client: after the servers

    @property
    def client(self) -> AsyncMongoClient: ...     # PyMongo as it is: the name says so
    def get_database(self, name: str | None = None) -> AsyncDatabase: ...
                                                   # None: the database of the URI

    async def _configure(self) -> None: ...       # AsyncMongoClient(uri, **options), ping
    async def _shut_down(self) -> None: ...       # await client.close()

    def _get_uri(self) -> str: raise NotImplementedError
    def _get_options(self) -> dict[str, t.Any]: raise NotImplementedError


class DefaultMongoDbClient(BaseMongoDbClient):
    ...                                           # MONGODB_DEFAULT_*
```

Usage:

```python
mongodb = await self.project.mongodb.clients.default
await mongodb.get_database("shop").orders.insert_one({...})
```

- The addon is a thin integration (named after PyMongo by the naming rule):
  the component gives the `AsyncMongoClient` and its databases as they are,
  with no wrappers over collections or sessions.
- `MongoDbClients` is to clients what `GrpcServers` is to servers; a second
  client is a subclass of `BaseMongoDbClient` with `MONGODB_<NAME>_*` and a
  slot.
- `components list` prints the clients with their paths; a `mongodb clients
  list` of our own is needed only to show their hosts (without credentials,
  through `pymongo.uri_parser`).
- The extras of PyMongo pass through as ours: `ingot-pymongo[aws]`,
  `[encryption]`, `[snappy]`, `[zstd]`, `[gssapi]`, `[ocsp]` require
  `pymongo[...]`. No units for them: they change no code of the addon.
- Not carried over: `py_bootstrap` (no bootstrap tool in the new Ingots), the
  generic type variables, the extension managers, the demo.

PyMongo 4.19.0 ships wheels for CPython 3.14 and 3.15 (manylinux x86_64),
so the CI matrix stands.

## Steps

1. **Layout** (prepared on the branch `unit-layout`, not committed): the
   prefix `MongoDb` (`MongoDbProject`, `MongoDbSettings`, `MongoDbConfigs`,
   `MongoDbLogging`), ingots 0.31, the canary; 0.11.0.dev0.
   Merged as #2.
2. **Clients** (prepared on the branch `mongodb-clients`): `mongodb/` with `clients/`, `BaseMongoDbClient`,
   `DefaultMongoDbClient`, the configs, PyMongo as a dependency, the tests
   (see question 4).
3. **Release 0.11.0.**

Later: a `mongodb clients list` with hosts if `components list` is not
enough; transactions helpers only if a real application asks.

## Decisions (2026-10-25)

1. **The parts.** `MONGODB_DEFAULT_HOST` (`localhost`), `_PORT` (27017),
   `_USER` and `_PASSWORD` (secure), passed to `AsyncMongoClient` as
   `host=`, `port=`, `username=`, `password=`: no URI is put together, so
   nothing needs quoting. `_get_uri()` gives way to `_get_options()` alone.
2. **A ping on start:** `MONGODB_DEFAULT_IS_PING_ON_START`, on by default;
   the demo commands of the current solution hung for 30 seconds without it.
3. **The clients** as in the current demo: `BaseMongoDbClient` gives the
   connection pool, `DefaultMongoDbClient` binds it to `MONGODB_DEFAULT_*`,
   and others stand next to it with configs of their own. A client is a
   connection wrapper, not an SDK: it gives the `AsyncMongoClient` and
   `get_database(name)` with the name required; MongoDB has no database of
   the connection as MySQL has, and an application's own layer over its
   databases is the application's.
4. **Integration tests** asking the server for its parameters
   (`buildInfo`, `serverStatus`), against a MongoDB of a
   `docker-compose.yml`, by a `make` target of their own; they skip
   without the server. CI runs them in a job of its own.
5. **`mongodb`**, as the project and the configs are named: the addon
   integrates the official driver; an addon on another client names its
   own unit.

## Questions

1. **The configs: one URI or the parts?**
   - (a) `MONGODB_DEFAULT_URI = SecureStrConfig("mongodb://localhost:27017")`:
     replica sets, SRV, TLS and every option in one place, as MongoDB
     documents it; secure, so `settings list` does not print it.
   - (b) the parts of the current solution, `HOST`, `PORT`, `USER`,
     `PASSWORD`, put together with `quote_plus`.
   - (c) the URI without credentials plus `MONGODB_DEFAULT_USER` and
     `MONGODB_DEFAULT_PASSWORD` (secure), passed as `username=` and
     `password=`: the secret apart from the address, as secret stores give
     them.

   The leaning: (c), which is (a) with the secret kept apart.
2. **Fail fast?** `AsyncMongoClient` connects lazily; the first query fails
   when the server is down. A `ping` in `_configure()` fails the start
   instead (`MONGODB_DEFAULT_IS_PING_ON_START`, on by default), which is
   what the old `FORCE_CONNECT` was for.
3. **The default database:** the one in the URI path
   (`mongodb://host/shop`, `get_default_database()`) or a config of its own
   (`MONGODB_DEFAULT_DATABASE`)?
4. **Tests against a real server.** The wiring is testable without one, the
   client is not (mongomock does not cover the async API).
   - CI: a `mongo` service container in the test, coverage and wheel jobs.
   - Locally: the tests needing a server skip without
     `INGOT_PYMONGO_TEST_URI`, and `make check` would then miss coverage;
     either `make check` starts a container (`docker run mongo`), or the
     coverage of those lines counts in CI only.
5. **The name of the unit:** `project.mongodb` (the domain, as the configs
   `MONGODB_*`) or `project.pymongo` (the library, as the addon)? The
   leaning: `mongodb`, as gRPC's is `grpc` and not `grpcio`.
