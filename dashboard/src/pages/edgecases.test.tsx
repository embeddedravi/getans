import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { AdUnit, Campaign, Publisher } from "../types";
import { fill } from "../tests/utils";
import { CampaignsPage } from "./CampaignsPage";
import { PublishersPage } from "./PublishersPage";

vi.mock("../components/Layout", () => ({
    Layout: ({ title, children }: { title: string; children: ReactNode }) => (
        <div>
            <h1>{title}</h1>
            {children}
        </div>
    ),
}));
vi.mock("../components/CreativesModal", () => ({
    CreativesModal: ({ campaign, isAdmin }: { campaign: { name: string }; isAdmin: boolean }) => (
        <div data-testid="creatives-modal">
            {campaign.name}|{String(isAdmin)}
        </div>
    ),
}));
vi.mock("../lib/api", () => ({
    api: {
        listCampaigns: vi.fn(),
        createCampaign: vi.fn(),
        updateCampaign: vi.fn(),
        deleteCampaign: vi.fn(),
        me: vi.fn(),
        listPublishers: vi.fn(),
        listAdUnits: vi.fn(),
        createPublisher: vi.fn(),
        createAdUnit: vi.fn(),
    },
}));

const mocked = vi.mocked(api);

const campaign = { id: 1, name: "Autumn sale", status: "active", is_active: true, priority: 1,
    bidding_strategy: "cpm", bid_amount: 1, daily_cap: null, total_budget: null, spent_amount: 0,
    start_date: "2026-09-01T00:00:00Z", end_date: null, targeting_rules: null, advertiser_id: 1,
    created_at: "2026-09-01T00:00:00Z" } as Campaign;

const publisher = (id: number, name: string): Publisher => ({
    id, name, site_url: `https://${name}.example.com`, domain: null, category: null,
    api_key: `key_${id}`, status: "active", is_active: true, ads_txt_verified: false,
    revenue_share_percentage: 70, unpaid_earnings: 0, payout_email: "p@example.com",
    created_at: "2026-09-01T00:00:00Z",
});

const adUnit = (id: number, publisher_id: number, slot_name: string): AdUnit => ({
    id, publisher_id, slot_name, description: null, format_type: "display", width: 300, height: 250,
    reserve_price: 0, is_active: true, allow_house_ads: true, settings: null,
    status: "pending_review",
    created_at: "2026-09-01T00:00:00Z",
});

beforeEach(() => {
    vi.resetAllMocks();
    mocked.me.mockResolvedValue({ role: "admin" });
    vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("CampaignsPage edge cases", () => {
    it("treats a failed /me call as non-admin", async () => {
        mocked.me.mockRejectedValue(new Error("401"));
        mocked.listCampaigns.mockResolvedValue([campaign]);
        render(<CampaignsPage />);

        fireEvent.click(await screen.findByRole("button", { name: "Creatives" }));

        expect(screen.getByTestId("creatives-modal")).toHaveTextContent("Autumn sale|false");
    });
});

describe("PublishersPage edge cases", () => {
    beforeEach(() => {
        mocked.listPublishers.mockResolvedValue([publisher(1, "alpha"), publisher(2, "beta")]);
        mocked.listAdUnits.mockImplementation(async (id: number) =>
            id === 1 ? [adUnit(10, 1, "alpha-slot")] : [adUnit(20, 2, "beta-slot")]
        );
    });

    it("loads the ad slots of whichever publisher is selected", async () => {
        render(<PublishersPage />);

        fireEvent.click(await screen.findByRole("button", { name: /alpha/ }));
        expect(await screen.findByText("alpha-slot")).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: /beta/ }));
        expect(await screen.findByText("beta-slot")).toBeInTheDocument();
        expect(screen.queryByText("alpha-slot")).not.toBeInTheDocument();
        expect(mocked.listAdUnits).toHaveBeenCalledWith(2);
    });

    it("closes the add-publisher modal on Cancel without calling the API", async () => {
        render(<PublishersPage />);
        await screen.findByText("alpha");

        fireEvent.click(screen.getByRole("button", { name: "+ Add" }));
        expect(screen.getByRole("heading", { name: "Add publisher" })).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

        expect(screen.queryByRole("heading", { name: "Add publisher" })).not.toBeInTheDocument();
        expect(mocked.createPublisher).not.toHaveBeenCalled();
    });

    it("closes the new-slot modal on Cancel without calling the API", async () => {
        render(<PublishersPage />);
        fireEvent.click(await screen.findByRole("button", { name: /alpha/ }));
        await screen.findByText("alpha-slot");

        fireEvent.click(screen.getByRole("button", { name: "New ad slot" }));
        fill(screen.getByLabelText("Slot name"), "draft");
        fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

        await waitFor(() =>
            expect(screen.queryByRole("heading", { name: "New ad slot" })).not.toBeInTheDocument()
        );
        expect(mocked.createAdUnit).not.toHaveBeenCalled();
    });
});
