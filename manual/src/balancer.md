# Balancer (hakobalancer)

`hakobalancer` is a stateless L7 balancer over `hakobackend` upstreams (TCP and unix socket).

Status: scaffold (config, pool, and health checks). The proxy loop is next. Design lives in issue #1; lease and fencing follow issue #2 and require balancer HA first, which is not part of phase 1.

```toml
[dependencies]
hakobalancer = "0.1"
```
