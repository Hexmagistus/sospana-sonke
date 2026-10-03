/** Test-only. The CI step compiles tests into /tmp, where node cannot see
frontend/node_modules. This points node at the project's node_modules (the
step runs from frontend/) so the render test can load react. Not imported by the app. */
import path from "node:path";
import Module from "node:module";

const modules = path.join(process.cwd(), "node_modules");
process.env.NODE_PATH = [modules, process.env.NODE_PATH].filter(Boolean).join(path.delimiter);
(Module as unknown as { _initPaths(): void })._initPaths();
