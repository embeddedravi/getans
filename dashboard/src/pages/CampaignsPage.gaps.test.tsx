import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { Campaign } from "../types";
import { fill, submitForm } from "../tests/utils";
import { CampaignsPage } from "./CampaignsPage";

vi.mock("../components/Layout", () => ({
    Layout: ({ title, children }: { title: string; children: ReactNode }) => (
        <div>
            <h1>{title}</h1>
            {children}
        </div>
    ),
}));
// Unlike the main test's mock, this one exposes onClose so we can exercise it.
vi.mock("../components/CreativesModal", () => ({
    CreativesModal: ({ campaign, onClose }: { campaign: { name: string }; onClose: () => void }) => (
        <div data-testid="creatives-modal">
            {campaign.name}
            <button onClick={onClose}>close-creatives</button>
        </div>
    ),
}));
vi.mock("../lib/api", () => ({
    api: {
        me: vi.fn(),
        listCampaigns: vi.fn(),
        createCampaign: vi.fn(),
        updateCampaign: vi.fn(),
        deleteCampaign: vi.fn(),
    },
}));

const mocked = vi.mocked(api);

const campaign = (o: Partial<Campaign> = {}): Campaign => ({
    id: 1,
    advertiser_id: 7,
    name: "Autumn sale",
    status: "active",
    is_active: true,
    priority: 5,
    bidding_strategy: "cpm",
    bid_amount: 1.5,
    daily_cap: null,
    total_budget: null,
    spent_amount: 0,
    start_date: "2026-09-01T00:00:00Z",
    end_date: null,
    targeting_rules: null,
    created_at: "2026-09-01T00:00:00Z",
    ...o,
});

beforeEach(() => {
    vi.resetAllMocks();
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mocked.me.mockResolvedValue({ role: "admin" });
    mocked.listCampaigns.mockResolvedValue([campaign()]);
});

afterEach(() => vi.restoreAllMocks());

describe("CampaignsPage gaps", () => {
    it("closes the creatives modal via its onClose", async () => {
        render(<CampaignsPage />);
        fireEvent.click(await screen.findByRole("button", { name: "Creatives" }));
        expect(screen.getByTestId("creatives-modal")).toBeInTheDocument();

        fireEvent.click(screen.getByRole("button", { name: "close-creatives" }));

        expect(screen.queryByTestId("creatives-modal")).not.toBeInTheDocument();
    });

    it("shows an inactive campaign as Off", async () => {
        mocked.listCampaigns.mockResolvedValue([campaign({ is_active: false })]);
        render(<CampaignsPage />);

        expect(await screen.findByText("Off")).toHaveClass("badge-ghost");
    });

    it("shows the formatted end date instead of 'Ongoing' when one is set", async () => {
        const end = "2026-12-31T12:00:00Z";
        mocked.listCampaigns.mockResolvedValue([campaign({ end_date: end })]);
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");

        const expected = new Date(end).toLocaleDateString();
        expect(screen.getByText((content) => content.includes(expected))).toBeInTheDocument();
        expect(screen.queryByText(/Ongoing/)).not.toBeInTheDocument();
    });

    it("uses a generic message when creation rejects with a non-Error", async () => {
        mocked.createCampaign.mockRejectedValue("boom");
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");
        fireEvent.click(screen.getByRole("button", { name: "New campaign" }));
        fill(screen.getByLabelText(/campaign name/i), "Winter push");
        fill(screen.getByLabelText(/advertiser id/i), "7");
        fill(screen.getByLabelText(/start date/i), "2026-10-01");

        submitForm(screen.getByRole("button", { name: "Create campaign" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not create campaign");
    });
});
