import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { Campaign, Creative } from "../types";
import { CreativesModal } from "./CreativesModal";

vi.mock("../lib/api", () => ({
    api: {
        listCreativesForCampaign: vi.fn(),
        createCreative: vi.fn(),
        updateCreative: vi.fn(),
        reviewCreative: vi.fn(),
        deleteCreative: vi.fn(),
    },
}));

const mocked = vi.mocked(api);
const campaign = { id: 1, name: "Autumn sale" } as Campaign;

const creative = (o: Partial<Creative> = {}): Creative => ({
    id: 10,
    campaign_id: 1,
    name: "Banner A",
    asset_url: "https://cdn.example.com/a.png",
    click_url: "https://example.com/landing",
    impression_tracker_url: null,
    format: "image",
    width: 300,
    height: 250,
    is_active: true,
    review_status: "pending",
    rejection_reason: null,
    created_at: "2026-09-25T00:00:00Z",
    ...o,
});

beforeEach(() => {
    vi.resetAllMocks();
});

describe("CreativesModal gaps", () => {
    it("shows an inactive creative as Off and toggles it back on", async () => {
        mocked.listCreativesForCampaign.mockResolvedValue([creative({ is_active: false })]);
        render(<CreativesModal campaign={campaign} isAdmin={false} onClose={vi.fn()} />);

        const toggle = await screen.findByTitle("Toggle active");
        expect(toggle).toHaveTextContent("Off");
        expect(toggle).toHaveClass("badge-ghost");

        fireEvent.click(toggle);

        await waitFor(() => expect(mocked.updateCreative).toHaveBeenCalledWith(10, { is_active: true }));
    });

    it("uses a generic message when an action rejects with a non-Error", async () => {
        mocked.listCreativesForCampaign.mockResolvedValue([creative()]);
        mocked.updateCreative.mockRejectedValue("boom");
        render(<CreativesModal campaign={campaign} isAdmin={false} onClose={vi.fn()} />);

        fireEvent.click(await screen.findByTitle("Toggle active"));

        expect(await screen.findByRole("alert")).toHaveTextContent("Action failed");
    });
});
