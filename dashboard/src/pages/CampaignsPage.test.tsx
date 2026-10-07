import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
vi.mock("../components/CreativesModal", () => ({
    CreativesModal: ({ campaign, isAdmin }: { campaign: { name: string }; isAdmin: boolean }) => (
        <div data-testid="creatives-modal">
            {campaign.name}|{String(isAdmin)}
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

afterEach(() => {
    vi.restoreAllMocks();
});

describe("campaign list", () => {
    it("shows a loading row, then the campaigns", async () => {
        render(<CampaignsPage />);
        expect(screen.getByText("Loading...")).toBeInTheDocument();

        expect(await screen.findByText("Autumn sale")).toBeInTheDocument();
        expect(screen.getByText("active")).toBeInTheDocument();
        expect(screen.getByText("CPM · ₹1.5000")).toBeInTheDocument();
        expect(screen.getByText("No daily cap")).toBeInTheDocument();
        expect(screen.getByText("₹0.00 spent")).toBeInTheDocument();
        expect(screen.getByText(/Ongoing/)).toBeInTheDocument();
        expect(screen.getByText("1 campaign")).toBeInTheDocument();
    });

    it("formats caps and total budget", async () => {
        mocked.listCampaigns.mockResolvedValue([
            campaign({ daily_cap: 25, total_budget: 100, spent_amount: 12.5 }),
        ]);
        render(<CampaignsPage />);

        expect(await screen.findByText("₹25.00/day")).toBeInTheDocument();
        expect(screen.getByText("₹12.50 / ₹100.00 total")).toBeInTheDocument();
    });

    it("shows an empty state", async () => {
        mocked.listCampaigns.mockResolvedValue([]);
        render(<CampaignsPage />);

        expect(await screen.findByText(/no campaigns yet/i)).toBeInTheDocument();
        expect(screen.getByText("0 campaigns")).toBeInTheDocument();
    });
});

describe("row actions", () => {
    it("toggles active/paused and reloads", async () => {
        render(<CampaignsPage />);
        fireEvent.click(await screen.findByRole("button", { name: "Pause" }));

        await waitFor(() => expect(mocked.updateCampaign).toHaveBeenCalledWith(1, { is_active: false }));
        await waitFor(() => expect(mocked.listCampaigns).toHaveBeenCalledTimes(2));
    });

    it("deletes only after confirmation", async () => {
        const confirm = vi.spyOn(window, "confirm");
        render(<CampaignsPage />);
        const del = await screen.findByRole("button", { name: "Delete" });

        confirm.mockReturnValueOnce(false);
        fireEvent.click(del);
        expect(mocked.deleteCampaign).not.toHaveBeenCalled();

        confirm.mockReturnValueOnce(true);
        fireEvent.click(del);
        await waitFor(() => expect(mocked.deleteCampaign).toHaveBeenCalledWith(1));
    });

    it("opens the creatives modal with the admin flag from /me", async () => {
        render(<CampaignsPage />);

        fireEvent.click(await screen.findByRole("button", { name: "Creatives" }));

        await waitFor(() =>
            expect(screen.getByTestId("creatives-modal")).toHaveTextContent("Autumn sale|true")
        );
    });

    it("passes isAdmin=false for non-admin users", async () => {
        mocked.me.mockResolvedValue({ role: "advertiser" });
        render(<CampaignsPage />);

        fireEvent.click(await screen.findByRole("button", { name: "Creatives" }));

        expect(screen.getByTestId("creatives-modal")).toHaveTextContent("Autumn sale|false");
    });
});

describe("create campaign modal", () => {
    function openModal() {
        fireEvent.click(screen.getByRole("button", { name: "New campaign" }));
    }

    function fillRequired() {
        fill(screen.getByLabelText(/campaign name/i), "Winter push");
        fill(screen.getByLabelText(/advertiser id/i), "7");
        fill(screen.getByLabelText(/start date/i), "2026-10-01");
    }

    it("submits the minimal payload and omits end_date when blank", async () => {
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");
        openModal();
        fillRequired();

        submitForm(screen.getByRole("button", { name: "Create campaign" }));

        await waitFor(() =>
            expect(mocked.createCampaign).toHaveBeenCalledWith({
                advertiser_id: 7,
                name: "Winter push",
                priority: 1,
                bidding_strategy: "cpm",
                bid_amount: 1,
                daily_cap: null,
                total_budget: null,
                start_date: "2026-10-01T00:00:00.000Z",
            })
        );
        // closes the modal and refreshes the list
        await waitFor(() => expect(mocked.listCampaigns).toHaveBeenCalledTimes(2));
        expect(screen.queryByRole("heading", { name: "New campaign" })).not.toBeInTheDocument();
    });

    it("converts every optional field when provided", async () => {
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");
        openModal();
        fillRequired();
        fill(screen.getByLabelText(/priority/i), "10");
        fill(screen.getByLabelText(/bidding strategy/i), "cpc");
        fill(screen.getByLabelText(/bid amount/i), "0.25");
        fill(screen.getByLabelText(/daily cap/i), "50");
        fill(screen.getByLabelText(/total budget/i), "1000");
        fill(screen.getByLabelText(/end date/i), "2026-10-31");

        submitForm(screen.getByRole("button", { name: "Create campaign" }));

        await waitFor(() =>
            expect(mocked.createCampaign).toHaveBeenCalledWith({
                advertiser_id: 7,
                name: "Winter push",
                priority: 10,
                bidding_strategy: "cpc",
                bid_amount: 0.25,
                daily_cap: 50,
                total_budget: 1000,
                start_date: "2026-10-01T00:00:00.000Z",
                end_date: "2026-10-31T00:00:00.000Z",
            })
        );
    });

    it("keeps the modal open and shows the error when creation fails", async () => {
        mocked.createCampaign.mockRejectedValue(new Error("end_date must be set after start_date"));
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");
        openModal();
        fillRequired();

        submitForm(screen.getByRole("button", { name: "Create campaign" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("end_date must be set after");
        expect(screen.getByRole("button", { name: "Create campaign" })).toBeEnabled();
    });

    it("closes on Cancel without calling the API", async () => {
        render(<CampaignsPage />);
        await screen.findByText("Autumn sale");
        openModal();

        fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

        expect(screen.queryByRole("heading", { name: "New campaign" })).not.toBeInTheDocument();
        expect(mocked.createCampaign).not.toHaveBeenCalled();
    });
});
