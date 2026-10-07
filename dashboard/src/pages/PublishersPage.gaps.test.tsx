import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { Publisher } from "../types";
import { fill, submitForm } from "../tests/utils";
import { PublishersPage } from "./PublishersPage";

vi.mock("../components/Layout", () => ({
    Layout: ({ title, children }: { title: string; children: ReactNode }) => (
        <div>
            <h1>{title}</h1>
            {children}
        </div>
    ),
}));
vi.mock("../lib/api", () => ({
    api: {
        me: vi.fn(),
        listPublishers: vi.fn(),
        listAdUnits: vi.fn(),
        createPublisher: vi.fn(),
        createAdUnit: vi.fn(),
    },
}));

const mocked = vi.mocked(api);

const publisher: Publisher = {
    id: 1,
    name: "Global Tech Media",
    site_url: "https://example.com",
    domain: null,
    category: null,
    api_key: "pub_live_abc123",
    status: "active",
    is_active: true,
    ads_txt_verified: false,
    revenue_share_percentage: 70,
    unpaid_earnings: 0,
    payout_email: "pay@example.com",
    created_at: "2026-09-01T00:00:00Z",
};

beforeEach(() => {
    vi.resetAllMocks();
    mocked.me.mockResolvedValue({ role: "admin" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mocked.listPublishers.mockResolvedValue([publisher]);
    mocked.listAdUnits.mockResolvedValue([]);
});

afterEach(() => vi.restoreAllMocks());

describe("PublishersPage gaps", () => {
    it("uses a generic message when creating a publisher rejects with a non-Error", async () => {
        mocked.createPublisher.mockRejectedValue("boom");
        render(<PublishersPage />);
        await screen.findByText("Global Tech Media");
        fireEvent.click(screen.getByRole("button", { name: "+ Add" }));
        fill(screen.getByLabelText("Name"), "New Site");
        fill(screen.getByLabelText("Site URL"), "https://new.example.com");
        fill(screen.getByLabelText("Payout email"), "money@new.example.com");

        submitForm(screen.getByRole("button", { name: "Add publisher" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not create publisher");
    });

    it("uses a generic message when creating an ad slot rejects with a non-Error", async () => {
        mocked.createAdUnit.mockRejectedValue("boom");
        render(<PublishersPage />);
        fireEvent.click(await screen.findByRole("button", { name: /Global Tech Media/ }));
        await screen.findByRole("heading", { name: "Global Tech Media" });
        fireEvent.click(screen.getByRole("button", { name: "New ad slot" }));
        fill(screen.getByLabelText("Slot name"), "x");

        submitForm(screen.getByRole("button", { name: "Create slot" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not create ad slot");
    });
});
