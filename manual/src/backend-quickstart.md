# Backend quickstart

```sh
# 1. Fetch the static binary (runs on EL7/EL8/ubuntu/Alpine alike)
curl -LO https://github.com/hakodb/hakobackend/releases/download/v0.9.0/hakobackend-v0.9.0-linux-x86_64.tar.gz
tar xzf hakobackend-v0.9.0-linux-x86_64.tar.gz

# 2. Minimal config (dev only: no policy file = OPEN + WARN)
printf 'port = 3000\ndriver = "hako"\ndata = "./data"\n' > hakobackend.toml
./hakobackend --config hakobackend.toml &

# 3. Smoke + first document
curl localhost:3000/api/ready                                    # {"ready":true}
curl -X POST localhost:3000/api/collections/users \
  -H 'Content-Type: application/json' -d '{"name":"alice"}'
curl localhost:3000/api/collections/users
```

Path rule (legacy parity): **even segments = document, odd = collection** — `/api/collections/users` lists, `/api/collections/users/1` reads one. `POST` creates, `PUT` replaces, `PATCH` merges (404 when absent — use PUT to create), `DELETE` removes.

TypeScript clients use `@hakodb/backend` (see [HTTP backend SDK](sdk-backend.md)); every other language speaks the same HTTP + WebSocket wire.

Next: [configuration](backend-config.md), then [policy](backend-policy.md) before exposing anything beyond localhost.
