# Balancer (hakobalancer)

`hakobalancer` is a stateless L7 balancer over `hakobackend` upstreams. It accepts TCP and unix-socket upstreams.

```toml
[dependencies]
hakobalancer = "0.1"
```

## Status

The crate currently provides configuration loading, the upstream pool, and health checks. The proxy loop is not implemented yet, so it is not ready to serve production traffic.

## Scope

- Health-aware upstream selection for `hakobackend`.
- TCP and unix-socket upstreams.
- No persistent state; any instance can be replaced.
