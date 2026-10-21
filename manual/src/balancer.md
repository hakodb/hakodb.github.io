# Balancer (hakobalancer)

`hakobalancer` is a stateless L7 proxy over `hakobackend` upstreams. It accepts TCP and unix-socket upstreams.

## Status

The project is **under evaluation**: it will either be deprecated or continue development. Do not deploy it as a production balancer yet.

The proxy works, but it does not currently improve throughput. End-to-end RPS through the balancer is lower than sending requests directly to `hakobackend`, and further performance work is not planned at this time. Prefer a direct `hakobackend` upstream unless you are evaluating the routing layer itself.

## Build and run

```sh
cargo build --release
cargo run --release -- --config hakobalancer.toml
```

Without `--config`, the process listens with an empty backend pool and refuses traffic.

## Configuration

```toml
listen = "0.0.0.0:8080"
strategy = "round_robin"        # only supported strategy
health_interval_secs = 10

backends = [
  { addr = "127.0.0.1:3005" },
  { addr = "127.0.0.1:3010" },
  # { sock = "/run/hakobackend/hako.sock" },
]
```

Each backend declares exactly one of `addr` or `sock`. A missing or duplicate field fails config validation.

Optional path routing:

```toml
[[routes]]
prefix = "/api/a"
backend = 1

default_backend = 0
```

Routes are matched by prefix; the first match wins. `default_backend` handles unmatched paths. Route and default indices must name a declared backend.

TLS termination is enabled only when both files are set:

```toml
tls_cert = "/etc/hako/fullchain.pem"
tls_key = "/etc/hako/privkey.pem"
```

A half pair stays plain HTTP rather than starting with partial TLS.

## Scope

- Health-aware, round-robin selection over `hakobackend` upstreams.
- TCP and unix-socket upstreams.
- Transparent HTTP proxying, WebSocket upgrade relay, sticky routing, and optional path routing.
- No persistent state; any instance can be replaced.
