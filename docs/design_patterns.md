# Design patterns in MiteCoder

| Problem | Pattern and location | Why this implementation | Alternative considered |
|---|---|---|---|
| Compare local inference engines without coupling the loop | Strategy: `inference/base.py`, scripted and llama.cpp backends | Experiments swap one injected object | Backend branches inside the agent would contaminate measurements and tests |
| Compare cheap workspace intelligence | Strategy: `retrieval/base.py`, Unicode lexical, symbol, hybrid | Ranking remains explicit and independently testable | Embedding RAG adds memory, dependencies, and opaque ranking |
| Restrict model capabilities | Command: `tools/base.py` and six concrete tools | Each action has a schema and one auditable execution boundary | Free-form shell access violates the threat model |
| Construct configured services | Factory: `inference/factory.py`, `retrieval/factory.py`, runtime composition | Backend-specific setup stays outside the agent | A framework would add weight without experimental value |
| Audit available actions | Registry: `tools/registry.py` | Names and schemas are enumerable and unknown actions fail closed | Dynamic imports make capability review harder |
| Make termination and progress testable | State: `agent/state.py`, `agent/loop.py` | Every transition emits an event | An implicit monolithic loop hides failure stages |
| Isolate experiments and tests | Dependency injection: `Agent.__init__` | Fake model, tools, retrieval, clock-facing budget, and metrics can be supplied | Global singletons create cross-run state |
