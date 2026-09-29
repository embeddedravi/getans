import { act, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TopBar } from "./TopBar";

const { fake, handlers } = vi.hoisted(() => {
    const handlers: Record<string, () => void> = {};
    const fake = {
        connected: false,
        on: vi.fn((event: string, cb: () => void) => {
            handlers[event] = cb;
        }),
        off: vi.fn(),
    };
    return { fake, handlers };
});

vi.mock("../lib/socket", () => ({ getDashboardSocket: () => fake }));

beforeEach(() => {
    fake.connected = false;
    fake.on.mockClear();
    fake.off.mockClear();
});

describe("TopBar", () => {
    it("shows the page title", () => {
        render(<TopBar title="Analytics" />);
        expect(screen.getByRole("heading", { name: "Analytics" })).toBeInTheDocument();
    });

    it("starts disconnected and follows connect/disconnect events", () => {
        render(<TopBar title="Analytics" />);
        expect(screen.getByText("Disconnected")).toBeInTheDocument();

        act(() => handlers.connect());
        expect(screen.getByText("Live")).toBeInTheDocument();

        act(() => handlers.disconnect());
        expect(screen.getByText("Disconnected")).toBeInTheDocument();
    });

    it("shows Live immediately if the socket is already connected", () => {
        fake.connected = true;
        render(<TopBar title="Analytics" />);
        expect(screen.getByText("Live")).toBeInTheDocument();
    });

    it("removes its listeners on unmount", () => {
        const { unmount } = render(<TopBar title="Analytics" />);
        unmount();

        expect(fake.off).toHaveBeenCalledWith("connect", handlers.connect);
        expect(fake.off).toHaveBeenCalledWith("disconnect", handlers.disconnect);
    });
});