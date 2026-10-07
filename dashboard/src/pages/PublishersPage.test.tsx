import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { AdUnit, Publisher } from "../types";
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

const publisher = (o: Partial<Publisher> = {}): Publisher => ({
    id: 1,
    name: "Global Tech Media",
    site_url: "https://example.com",
    domain: "example.com",
    category: "News",
    api_key: "pub_live_abc123",
    status: "pending_approval",
    is_active: true,
    ads_txt_verified: true,
    revenue_share_percentage: 70,
    unpaid_earnings: 12.5,
    payout_email: "pay@example.com",
    created_at: "2026-09-01T00:00:00Z",
    ...o,
});

const adUnit = (o: Partial<AdUnit> = {}): AdUnit => ({
    id: 5,
    publisher_id: 1,
    slot_name: "sidebar-300x250",
    description: null,
    format_type: "display",
    width: 300,
    height: 250,
    reserve_price: 0.5,
    is_active: true,
    allow_house_ads: true,
    status: "pending_review",
    settings: null,
    created_at: "2026-09-01T00:00:00Z",
    ...o,
});

async function selectPublisher() {
    fireEvent.click(await screen.findByRole("button", { name: /Global Tech Media/ }));
    await screen.findByRole("heading", { name: "Global Tech Media" });
}

beforeEach(() => {
    vi.resetAllMocks();
    mocked.me.mockResolvedValue({ role: "admin" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mocked.listPublishers.mockResolvedValue([publisher()]);
    mocked.listAdUnits.mockResolvedValue([adUnit()]);
});

describe("publisher list and detail", () => {
    it("lists publishers with a readable status badge", async () => {
        render(<PublishersPage />);

        expect(await screen.findByText("Global Tech Media")).toBeInTheDocument();
        expect(screen.getByText("pending approval")).toBeInTheDocument();
        expect(screen.getByText("https://example.com")).toBeInTheDocument();
        expect(screen.getByText(/select a publisher/i)).toBeInTheDocument();
    });

    it("shows an empty state", async () => {
        mocked.listPublishers.mockResolvedValue([]);
        render(<PublishersPage />);

        expect(await screen.findByText("No publishers yet.")).toBeInTheDocument();
    });

    it("shows the key, payout details and ad slots for the selected publisher", async () => {
        render(<PublishersPage />);

        await selectPublisher();

        expect(mocked.listAdUnits).toHaveBeenCalledWith(1);
        expect(screen.getByText("pub_live_abc123")).toBeInTheDocument();
        expect(screen.getByText(/Payout: pay@example\.com · 70% share/)).toBeInTheDocument();
        expect(screen.getByText("₹12.50 unpaid")).toBeInTheDocument();
        expect(screen.getByText("ads.txt verified")).toBeInTheDocument();
        expect(screen.getByText("example.com · News")).toBeInTheDocument();
        expect(await screen.findByText("sidebar-300x250")).toBeInTheDocument();
        expect(screen.getByText("300×250")).toBeInTheDocument();
        expect(screen.getByText("₹0.5000")).toBeInTheDocument();
    });

    it("renders a dash for a zero reserve price and an empty slot state", async () => {
        mocked.listAdUnits.mockResolvedValue([adUnit({ reserve_price: 0 })]);
        render(<PublishersPage />);
        await selectPublisher();
        expect(await screen.findByText("—")).toBeInTheDocument();
    });

    it("shows an empty state when the publisher has no ad slots", async () => {
        mocked.listAdUnits.mockResolvedValue([]);
        render(<PublishersPage />);

        await selectPublisher();

        expect(await screen.findByText(/no ad slots yet/i)).toBeInTheDocument();
    });
});

describe("create publisher modal", () => {
    function openModal() {
        fireEvent.click(screen.getByRole("button", { name: "+ Add" }));
    }

    function fillRequired() {
        fill(screen.getByLabelText("Name"), "New Site");
        fill(screen.getByLabelText("Site URL"), "https://new.example.com");
        fill(screen.getByLabelText("Payout email"), "money@new.example.com");
    }

    it("sends null for blank optional fields, then closes and reloads", async () => {
        render(<PublishersPage />);
        await screen.findByText("Global Tech Media");
        openModal();
        fillRequired();

        submitForm(screen.getByRole("button", { name: "Add publisher" }));

        await waitFor(() =>
            expect(mocked.createPublisher).toHaveBeenCalledWith({
                name: "New Site",
                site_url: "https://new.example.com",
                payout_email: "money@new.example.com",
                domain: null,
                category: null,
            })
        );
        await waitFor(() => expect(mocked.listPublishers).toHaveBeenCalledTimes(2));
        expect(screen.queryByRole("heading", { name: "Add publisher" })).not.toBeInTheDocument();
    });

    it("includes domain and category when provided", async () => {
        render(<PublishersPage />);
        await screen.findByText("Global Tech Media");
        openModal();
        fillRequired();
        fill(screen.getByLabelText("Domain (optional)"), "new.example.com");
        fill(screen.getByLabelText("Category (optional)"), "Tech");

        submitForm(screen.getByRole("button", { name: "Add publisher" }));

        await waitFor(() =>
            expect(mocked.createPublisher).toHaveBeenCalledWith(
                expect.objectContaining({ domain: "new.example.com", category: "Tech" })
            )
        );
    });

    it("shows the API error and keeps the modal open", async () => {
        mocked.createPublisher.mockRejectedValue(new Error("value is not a valid email address"));
        render(<PublishersPage />);
        await screen.findByText("Global Tech Media");
        openModal();
        fillRequired();

        submitForm(screen.getByRole("button", { name: "Add publisher" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("not a valid email");
    });
});

describe("create ad slot modal", () => {
    it("submits numbers, not strings, and refreshes the slot list", async () => {
        render(<PublishersPage />);
        await selectPublisher();
        fireEvent.click(screen.getByRole("button", { name: "New ad slot" }));

        fill(screen.getByLabelText("Slot name"), "leaderboard");
        fill(screen.getByLabelText("Format"), "banner");
        fill(screen.getByLabelText("Width"), "728");
        fill(screen.getByLabelText("Height"), "90");
        fill(screen.getByLabelText(/reserve price/i), "0.25");
        submitForm(screen.getByRole("button", { name: "Create slot" }));

        await waitFor(() =>
            expect(mocked.createAdUnit).toHaveBeenCalledWith(1, {
                publisher_id: 1,
                slot_name: "leaderboard",
                format_type: "banner",
                width: 728,
                height: 90,
                reserve_price: 0.25,
            })
        );
        await waitFor(() => expect(mocked.listAdUnits).toHaveBeenCalledTimes(2));
        expect(screen.queryByRole("heading", { name: "New ad slot" })).not.toBeInTheDocument();
    });

    it("uses the 300x250 / display / $0 defaults", async () => {
        render(<PublishersPage />);
        await selectPublisher();
        fireEvent.click(screen.getByRole("button", { name: "New ad slot" }));

        fill(screen.getByLabelText("Slot name"), "sidebar");
        submitForm(screen.getByRole("button", { name: "Create slot" }));

        await waitFor(() =>
            expect(mocked.createAdUnit).toHaveBeenCalledWith(1, {
                publisher_id: 1,
                slot_name: "sidebar",
                format_type: "display",
                width: 300,
                height: 250,
                reserve_price: 0,
            })
        );
    });

    it("shows the API error", async () => {
        mocked.createAdUnit.mockRejectedValue(new Error("Cannot add ad units to another publisher account"));
        render(<PublishersPage />);
        await selectPublisher();
        fireEvent.click(screen.getByRole("button", { name: "New ad slot" }));
        fill(screen.getByLabelText("Slot name"), "x");

        submitForm(screen.getByRole("button", { name: "Create slot" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("another publisher");
    });
});
