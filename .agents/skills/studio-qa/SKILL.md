# Skill: studio-qa

## Purpose
Make AI Music Video Studio verifiable and regression-resistant.

## Scope
- unit tests;
- API contract tests;
- worker offline/online tests;
- state machine tests;
- fixture-based media tests;
- smoke tests;
- regression coverage for fixed bugs.

## P0 test matrix

### Control Plane
- `/api/control/health` with no worker configured;
- configured worker online;
- configured worker offline/timeout;
- checkpoint discovery success/failure.

### Project flow
- create project;
- create storyboard;
- approve storyboard;
- generate one scene;
- poll status;
- regenerate scene;
- approve version;
- assemble only when valid.

### Resilience
- duplicate request does not duplicate destructive work;
- restart/reload preserves state;
- malformed upload rejected;
- invalid project/scene returns structured 4xx;
- worker 5xx/timeout becomes recoverable application state.

## Media fixtures
Use very small legal/generated fixtures for CI. Do not require a GPU for the default test suite. GPU/ComfyUI tests should be separately marked integration/e2e.

## Done rule
A bug fix without a regression test is incomplete when the behavior can be tested deterministically.