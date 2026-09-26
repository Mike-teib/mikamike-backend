// node-env.d.ts — Déclarations minimales des modules Node utilisés par les tests, pour que
// `tsc --noEmit` passe sans @types/node (seule devDependency : typescript).

declare module "node:test" {
  interface TestContext {
    skip(message?: string): void;
    diagnostic(message: string): void;
  }
  interface TestOptions {
    readonly skip?: boolean | string;
    readonly timeout?: number;
    readonly concurrency?: number | boolean;
  }
  type TestFn = (t: TestContext) => void | Promise<void>;
  type SuiteFn = () => void | Promise<void>;
  export function test(name: string, fn: TestFn): Promise<void>;
  export function test(name: string, options: TestOptions, fn: TestFn): Promise<void>;
  export function describe(name: string, fn: SuiteFn): Promise<void>;
  export function describe(name: string, options: TestOptions, fn: SuiteFn): Promise<void>;
  export function it(name: string, fn: TestFn): Promise<void>;
  export function it(name: string, options: TestOptions, fn: TestFn): Promise<void>;
  export function before(fn: () => void | Promise<void>): void;
  export function after(fn: () => void | Promise<void>): void;
  export default test;
}

declare module "node:assert/strict" {
  interface Assert {
    (value: unknown, message?: string): asserts value;
    ok(value: unknown, message?: string): asserts value;
    equal<T>(actual: unknown, expected: T, message?: string): asserts actual is T;
    notEqual(actual: unknown, expected: unknown, message?: string): void;
    deepEqual<T>(actual: unknown, expected: T, message?: string): asserts actual is T;
    notDeepEqual(actual: unknown, expected: unknown, message?: string): void;
    match(value: string, regexp: RegExp, message?: string): void;
    doesNotMatch(value: string, regexp: RegExp, message?: string): void;
    throws(fn: () => unknown, error?: unknown, message?: string): void;
    doesNotThrow(fn: () => unknown, message?: string): void;
    rejects(promise: Promise<unknown> | (() => Promise<unknown>), error?: unknown, message?: string): Promise<void>;
    fail(message?: string): never;
  }
  const assert: Assert;
  export default assert;
}

declare module "node:fs" {
  export function readFileSync(path: string | URL, encoding: "utf8"): string;
  export function existsSync(path: string | URL): boolean;
}

declare module "node:child_process" {
  export function execFileSync(
    file: string,
    args: readonly string[],
    options: { readonly encoding: "utf8"; readonly timeout?: number; readonly env?: Record<string, string | undefined> },
  ): string;
}

declare const process: {
  readonly env: Record<string, string | undefined>;
};
