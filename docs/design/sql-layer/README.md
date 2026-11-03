# A light SQL layer for ingot-sql

Status: an idea, talked through on 2026-10-23; not an ADR, nothing built.
Next step: a prototype here, checked by `make check-prototypes`.

## What we want

- Typical queries in one line: `db.select(...)`, `db.insert(...)`,
  `db.update(...)`, `db.delete(...)`, from typed parameter objects.
- Control over the result: the SQL a call runs is always visible and
  predictable, one parameter object is one statement.
- A direct way out for the niche and the fast: raw SQL, and the driver's own
  connection.
- Not an ORM, and not SQLAlchemy: nothing to look up in documentation for a
  plain query, nothing happening behind the code's back.

## Why not a portable abstraction over every database

The first path we weighed: `ingot-sql` as generic solutions over every SQL
database, backends plugging their implementations in, the backend swapped
"with a snap", SQLite natural in tests. What speaks against it as a promise:

- There is no async standard: DB-API 2.0 (PEP 249) is synchronous only, and
  the async drivers differ: asyncpg is not DB-API and binds `$1`, aiosqlite
  binds `?`, aiomysql and psycopg 3 bind `%s`.
- SQL itself differs: upserts (`ON CONFLICT` / `ON DUPLICATE KEY`),
  `RETURNING`, types, JSON, locking. Code written against one database stays
  tied to it whatever the API.
- The data does not move with the code: swapping a database is a migration.
- SQLite in tests instead of the production database is a known trap: green
  tests, then constraints, types and concurrency break on PostgreSQL.

So the layer generalizes what is common and cheap, and does not promise
portability.

## What is common to every database

The plumbing of a driver, today copied in every backend's `connections`:

- the pool's life cycle, opened at start and closed at shutdown: a
  `Component` with its `SHUTDOWN_ORDER`;
- configs: DSN, pool size, timeouts;
- the scope of a transaction, `async with` around a unit of work;
- logging, a health check;
- contract tests (ADR 0005).

The base of `ingot-sql` holds these; a backend implements a few hooks
(`_connect`, `_close`, `_acquire`) and its dialect.

## Three levels

```python
# 1. Typical queries: parameters are data, one object is one statement
users = await db.select(
    Select(Users, where=Users.name.eq("bee"), order_by=[Users.id.desc()], limit=10)
)
await db.insert(Insert(Users, rows=[Users(id=1, name="bee", email=None)]))
await db.update(Update(Users, set=[Users.email.to("b@x")], where=Users.id.eq(1)))

# what goes to the database, without one: a pure function
db.compile(Select(Users, where=Users.name.eq("bee")))
# Statement('SELECT "id", "name", "email" FROM "users" WHERE "name" = $1', ("bee",))

# 2. A fragment of SQL where equality is not enough, or a whole raw query
Select(Users, where=Sql("age > {} AND name LIKE {}", 18, "b%"))
report = await db.fetch(Sql("WITH ... SELECT ...", since), into=Report)

# 3. The driver itself
async with db.connection() as conn:  # an asyncpg.Connection as it is
    await conn.copy_records_to_table("users", records=...)
```

Principles:

- No hidden queries: no session, no identity map, no lazy relations. Joins
  and aggregates are explicit, `Sql(..., into=...)`.
- `compile()` is pure: the SQL is always visible, and tests can compare it
  without a database.
- Values are always bound, never put into the text; table and column names
  come from the classes and are quoted. No injection even through `Select`.
- A neutral placeholder `{}`: the compiler turns it into the driver's style
  (`$1`, `?`, `%s`) and numbers it across fragments, so a fragment reads the
  same for every database.
- The dialect is a few hooks of a backend: the placeholder, identifier
  quoting, `RETURNING`, upserts. Execution and the pool are a component.

Prior art to look at: PyPika (a query builder, no execution), aiosql (raw
queries in `.sql` files turned into functions).

## The table is its record too

`Table` as a structure is a set of columns, a record is one row of it; only
the column names were shared, which is what blocked a dataclass approach
before. A column is a descriptor, as `BaseConfig` and `Slot` in `ingots`
are: on the class it is the column, on an instance its value.

```python
class Column[V]:
    def __set_name__(self, owner: type, name: str) -> None: ...
    @t.overload
    def __get__(self, obj: None, owner: type) -> t.Self: ...   # the structure
    @t.overload
    def __get__(self, obj: "Table", owner: type) -> V: ...     # a record's value
    def __set__(self, obj: "Table", value: t.Never) -> t.NoReturn: ...  # frozen

class Users(Table):
    NAME = "users"
    id = Column[int]()
    name = Column[str]()
    email = Column[str | None]()

Users.name   # Column[str]: builds queries
user.name    # str: a value of a fetched row
```

What it gives:

- A typed `where` without overloading `__eq__`: `Column[V].eq(value: V)`, so
  mypy rejects `Users.id.eq("x")`; likewise `.to(value: V)` for `SET`,
  `.desc()` for ordering. No dict of strings, no expression language.
- Columns inherit as slots do: a mixin table `Timestamps` with `created_at`
  and `updated_at` joins any table (composition by inheritance, ADR 0004).
- Names come from `__set_name__`, as the configs' do.

## Not an ORM: where the line is

A record is data only, and every I/O goes explicitly through `db`.
`user = await Users.create(name="john"); user.name = "Bob"; await
user.save()` is Active Record, the mark of an ORM, and stays out.

| An ORM has | We have |
|---|---|
| a record holding a connection or a session (`user.save()`) | a record unaware of the database: a frozen value |
| change tracking, an implicit flush | none: a change is an explicit statement |
| an identity map | none: every fetch gives new records |
| lazy relations, hidden N+1 queries | none: an explicit `Select` or `Sql(..., into=...)` |
| opaque query building | `db.compile(...)` |

Mapping a row to a typed object is a row mapper, not an ORM: we keep it.

```python
[user] = await db.select(Select(Users, where=Users.id.eq(1)))
bob = dataclasses.replace(user, name="Bob")   # a new record, no database
await db.update(Update.record(bob))           # all columns by the primary key
```

`Update.record()` is the limit of the sugar: one predictable statement from
what it is given. Computing which fields changed would be change tracking.

## Open questions

1. The record's constructor: `Users(id=1, name="bee", email=None)` checked
   by mypy, through `@t.dataclass_transform(field_specifiers=(Column,))` on
   `Table`. Descriptor-typed fields are a fine point for mypy: the
   `__init__` parameter must take the type of the column's `__set__`, which
   conflicts with a frozen `__set__(value: t.Never)`. The first thing for
   the prototype to settle.
2. A partial select (`columns=[Users.id, Users.name]`) gives a record
   without `email`, and `user.email` stops being an honest `str | None`:
   forbid it for records and return tuples, or declare a view table with the
   columns wanted.
3. Values the database makes: autoincrement, `DEFAULT`, `now()`. Before the
   insert there is no `id`: an `Insert` without those columns plus
   `RETURNING`, or a mark on the column.
4. Joins: a view class, or a tuple `(Users, Orders)`; likely the level of
   `Sql(..., into=...)`.
5. Transactions: `async with db.transaction() as tx: await tx.select(...)`,
   the same API as `db`.
6. Naming: typical queries are written against `ingot-sql`, so by the
   naming rule a backend takes the database's name (`ingot-postgresql`);
   level 3 exposes the driver, which its description says.

## The prototype

`Column`, `Table` (structure and record), `Select` / `Insert` / `Update` /
`Delete`, `Update.record`, `Sql`, `compile()` with two dialects (`$1` and
`?`), checked by `make check-prototypes`; `# error:` marks what mypy must
reject, such as `Users.id.eq("x")` and `user.name = "Bob"`. Question 1
first.
