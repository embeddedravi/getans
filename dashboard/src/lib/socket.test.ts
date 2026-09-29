import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

type Handler = (...args: unknown[]) => void;

const { ioMock, fake, handlers } = vi.hoisted(() => {
    const handlers: Record<string, Handler> = {};
    const fake = {
        connected: false,
        on: vi.fn((event: string, cb: Handler) => {
            handlers[event] = cb;
            return fake;
        }),
        off: vi.fn(),
        disconnect: vi.fn(),
    };
    return { ioMock: vi.fn((_url: string, _opts?: unknown) => fake), fake, handlers };
});

vi.mock("socket.io-client", () => ({ io: ioMock }));

let assign: ReturnType<typeof vi.fn>;

beforeEach(() => {
    vi.resetModules(); // socket.ts keeps a module-level singleton
    ioMock.mockClear();
    fake.on.mockClear();
    fake.off.mockClear();
    fake.disconnect.mockClear();
    Object.keys(handlers).forEach((k) => delete handlers[k]);
    assign = vi.fn();
    vi.stubGlobal("location", { pathname: "/", assign });
});

afterEach(() => {
    vi.unstubAllGlobals();
});

const load = () => import("./socket");

describe("getDashboardSocket", () => {
    it("opens a single websocket connection to /dashboard", async () => {
        const { getDashboardSocket } = await load();

        expect(getDashboardSocket()).toBe(getDashboardSocket());
        expect(ioMock).toHaveBeenCalledTimes(1);
        expect(ioMock).toHaveBeenCalledWith(
            "/dashboard",
            expect.objectContaining({ transports: ["websocket"] })
        );
    });

    it("reads the token on every connection attempt", async () => {
        const { getDashboardSocket } = await load();
        getDashboardSocket();
        const opts = ioMock.mock.calls[0][1] as { auth: (cb: (d: unknown) => void) => void };

        const cb = vi.fn();
        localStorage.setItem("access_token", "t1");
        opts.auth(cb);
        localStorage.setItem("access_token", "t2");
        opts.auth(cb);

        expect(cb.mock.calls).toEqual([[{ token: "t1" }], [{ token: "t2" }]]);
    });
});

describe("session expiry", () => {
    it("clears the token and redirects when the handshake is refused", async () => {
        localStorage.setItem("access_token", "expired");
        const { getDashboardSocket } = await load();
        getDashboardSocket();

        handlers.connect_error(new Error("unauthorized"));

        expect(localStorage.getItem("access_token")).toBeNull();
        expect(fake.disconnect).toHaveBeenCalled();
        expect(assign).toHaveBeenCalledWith("/login");
    });

    it("ignores other connection errors", async () => {
        localStorage.setItem("access_token", "still-good");
        const { getDashboardSocket } = await load();
        getDashboardSocket();

        handlers.connect_error(new Error("xhr poll error"));

        expect(localStorage.getItem("access_token")).toBe("still-good");
        expect(assign).not.toHaveBeenCalled();
    });

    it("redirects when the server closes the connection (token expiry)", async () => {
        const { getDashboardSocket } = await load();
        getDashboardSocket();

        handlers.disconnect("io server disconnect");

        expect(assign).toHaveBeenCalledWith("/login");
    });

    it("does not redirect on network-level disconnects", async () => {
        const { getDashboardSocket } = await load();
        getDashboardSocket();

        handlers.disconnect("transport close");

        expect(assign).not.toHaveBeenCalled();
    });

    it("does not redirect again when already on /login", async () => {
        vi.stubGlobal("location", { pathname: "/login", assign });
        const { getDashboardSocket } = await load();
        getDashboardSocket();

        handlers.connect_error(new Error("unauthorized"));

        expect(assign).not.toHaveBeenCalled();
    });
});

describe("subscribeToMetrics / resetDashboardSocket", () => {
    it("subscribes to metric_update and returns an unsubscribe function", async () => {
        const { subscribeToMetrics } = await load();
        const cb = vi.fn();

        const unsubscribe = subscribeToMetrics(cb);
        expect(fake.on).toHaveBeenCalledWith("metric_update", cb);

        unsubscribe();
        expect(fake.off).toHaveBeenCalledWith("metric_update", cb);
    });

    it("resetDashboardSocket disconnects and the next call reconnects", async () => {
        const { getDashboardSocket, resetDashboardSocket } = await load();
        getDashboardSocket();

        resetDashboardSocket();
        expect(fake.disconnect).toHaveBeenCalledTimes(1);

        getDashboardSocket();
        expect(ioMock).toHaveBeenCalledTimes(2);
    });
});