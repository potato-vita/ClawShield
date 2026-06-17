export type HookRegistrar = (
  api: unknown,
  name: string,
  handler: (event: unknown, ctx: Record<string, unknown>) => unknown,
  opts?: Record<string, unknown>,
) => void;

export const on: HookRegistrar = (api, name, handler, opts) => {
  const typedApi = api as {
    on?: (
      name: string,
      handler: (event: unknown, ctx: Record<string, unknown>) => unknown,
      opts?: Record<string, unknown>,
    ) => void;
    registerHook?: (
      name: string,
      handler: (event: unknown) => unknown,
      opts?: Record<string, unknown>,
    ) => void;
  };

  if (typedApi.on) {
    typedApi.on(name, handler, opts);
    return;
  }

  typedApi.registerHook?.(name, (event) => handler(event, {}), opts);
};
