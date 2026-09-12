# Skill: studio-deploy

## Purpose
Own deployment, connectivity, configuration, security and operational diagnostics.

## Scope
- Vercel configuration;
- environment variables;
- worker URL/connectivity;
- tunnel or persistent worker exposure;
- CORS;
- timeouts;
- auth between Vercel and worker;
- logs/observability;
- production readiness.

## P0 rules
- never commit temporary tunnel URLs as production source of truth;
- keep `RENDER_WORKER_URL` in deployment environment configuration;
- expose a visible worker health/capabilities diagnostic;
- apply short health-check timeouts and longer job polling separately;
- do not proxy large/long-running renders synchronously through Vercel;
- do not commit secrets;
- fail clearly when worker configuration is missing.

## Security checklist
- validate upload type and size;
- sanitize paths;
- no arbitrary local-path access from public requests;
- worker endpoints that mutate state should support authentication before multiuser/public production;
- CORS limited to intended control plane;
- redact internal exceptions/paths from public responses where appropriate;
- rate/size limits for abuse-prone endpoints.

## Observability checklist
Record or expose:
- app version;
- worker version;
- capabilities;
- request id;
- job id;
- project id;
- scene id;
- stage;
- elapsed time;
- retry count;
- stable error code.

## Deployment verification
After a deploy verify:
1. control-plane health;
2. worker configured;
3. worker online;
4. checkpoint discovery;
5. create-project path;
6. one small scene job can be initiated and observed;
7. no secret appears in page source or public logs.