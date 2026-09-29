import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { Campaign, Creative } from "../types";
import { fill, submitForm } from "../tests/utils";
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
const onClose = vi.fn();

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

function renderModal(isAdmin = false) {
    return render(<CreativesModal campaign={campaign} isAdmin={isAdmin} onClose={onClose} />);
}

beforeEach(() => {
    vi.resetAllMocks();
    mocked.listCreativesForCampaign.mockResolvedValue([creative()]);
});

afterEach(() => {
    vi.restoreAllMocks();
});

describe("listing", () => {
    it("loads creatives for the campaign and renders their details", async () => {
        renderModal();
        expect(screen.getByText("Loading...")).toBeInTheDocument();

        expect(await screen.findByText("Banner A")).toBeInTheDocument();
        expect(mocked.listCreativesForCampaign).toHaveBeenCalledWith(1);
        expect(screen.getByText("300×250")).toBeInTheDocument();
        expect(screen.getByText("pending")).toBeInTheDocument();
        expect(screen.getByRole("link", { name: "https://example.com/landing" })).toHaveAttribute(
            "href",
            "https://example.com/landing"
        );
    });

    it("shows why a campaign can't serve when it has no creatives", async () => {
        mocked.listCreativesForCampaign.mockResolvedValue([]);
        renderModal();

        expect(await screen.findByText(/can't serve until it has an approved one/i)).toBeInTheDocument();
    });

    it("falls back to 'Creative #id' for unnamed creatives and shows rejection reasons", async () => {
        mocked.listCreativesForCampaign.mockResolvedValue([
            creative({ name: null, review_status: "rejected", rejection_reason: "Blurry" }),
        ]);
        renderModal();

        expect(await screen.findByText("Creative #10")).toBeInTheDocument();
        expect(screen.getByText("Blurry")).toBeInTheDocument();
    });

    it("shows the error when loading fails", async () => {
        mocked.listCreativesForCampaign.mockRejectedValue(new Error("Access denied to campaign creatives"));
        renderModal();

        expect(await screen.findByRole("alert")).toHaveTextContent("Access denied");
    });

    it("calls onClose", async () => {
        renderModal();
        await screen.findByText("Banner A");

        fireEvent.click(screen.getByRole("button", { name: "Close" }));

        expect(onClose).toHaveBeenCalled();
    });
});

describe("review controls", () => {
    it.each([
        ["pending", true, true],
        ["approved", false, true],
        ["rejected", true, false],
    ] as const)("admin on a %s creative: approve=%s reject=%s", async (status, approve, reject) => {
        mocked.listCreativesForCampaign.mockResolvedValue([creative({ review_status: status })]);
        renderModal(true);
        await screen.findByText("Banner A");

        expect(!!screen.queryByRole("button", { name: "Approve" })).toBe(approve);
        expect(!!screen.queryByRole("button", { name: "Reject" })).toBe(reject);
    });

    it("hides review buttons from non-admins", async () => {
        renderModal(false);
        await screen.findByText("Banner A");

        expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
        expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
    });

    it("approves and reloads", async () => {
        renderModal(true);
        fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

        await waitFor(() => expect(mocked.reviewCreative).toHaveBeenCalledWith(10, "approved"));
        await waitFor(() => expect(mocked.listCreativesForCampaign).toHaveBeenCalledTimes(2));
    });

    it("rejects with the reason from the prompt", async () => {
        vi.spyOn(window, "prompt").mockReturnValue("Blurry");
        renderModal(true);

        fireEvent.click(await screen.findByRole("button", { name: "Reject" }));

        await waitFor(() => expect(mocked.reviewCreative).toHaveBeenCalledWith(10, "rejected", "Blurry"));
    });

    it("does nothing when the rejection prompt is cancelled", async () => {
        vi.spyOn(window, "prompt").mockReturnValue(null);
        renderModal(true);

        fireEvent.click(await screen.findByRole("button", { name: "Reject" }));

        expect(mocked.reviewCreative).not.toHaveBeenCalled();
    });

    it("surfaces a failed action", async () => {
        mocked.reviewCreative.mockRejectedValue(new Error("Not authorized for this action"));
        renderModal(true);

        fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Not authorized");
    });
});

describe("other row actions", () => {
    it("toggles active", async () => {
        renderModal();
        fireEvent.click(await screen.findByTitle("Toggle active"));

        await waitFor(() => expect(mocked.updateCreative).toHaveBeenCalledWith(10, { is_active: false }));
    });

    it("deletes only after confirmation", async () => {
        const confirm = vi.spyOn(window, "confirm");
        renderModal();
        const del = await screen.findByRole("button", { name: "Delete" });

        confirm.mockReturnValueOnce(false);
        fireEvent.click(del);
        expect(mocked.deleteCreative).not.toHaveBeenCalled();

        confirm.mockReturnValueOnce(true);
        fireEvent.click(del);
        await waitFor(() => expect(mocked.deleteCreative).toHaveBeenCalledWith(10));
    });
});

describe("add creative form", () => {
    it("posts an image creative, clears the form and reloads", async () => {
        renderModal();
        await screen.findByText("Banner A");

        fill(screen.getByPlaceholderText("Image URL"), "https://cdn.example.com/new.png");
        fill(screen.getByPlaceholderText("Click-through URL"), "https://example.com/new");
        submitForm(screen.getByRole("button", { name: "Add creative" }));

        await waitFor(() =>
            expect(mocked.createCreative).toHaveBeenCalledWith({
                campaign_id: 1,
                name: null,
                asset_url: "https://cdn.example.com/new.png",
                click_url: "https://example.com/new",
                width: 300,
                height: 250,
                format: "image",
            })
        );
        await waitFor(() => expect(mocked.listCreativesForCampaign).toHaveBeenCalledTimes(2));
        expect(screen.getByPlaceholderText("Image URL")).toHaveValue("");
    });

    it("sends the name and custom dimensions when given", async () => {
        renderModal();
        await screen.findByText("Banner A");

        fill(screen.getByPlaceholderText("Name (optional)"), "Leaderboard");
        fill(screen.getByPlaceholderText("Image URL"), "https://cdn.example.com/lb.png");
        fill(screen.getByPlaceholderText("Click-through URL"), "https://example.com/lb");
        fill(screen.getByPlaceholderText("Width"), "728");
        fill(screen.getByPlaceholderText("Height"), "90");
        submitForm(screen.getByRole("button", { name: "Add creative" }));

        await waitFor(() =>
            expect(mocked.createCreative).toHaveBeenCalledWith(
                expect.objectContaining({ name: "Leaderboard", width: 728, height: 90 })
            )
        );
    });

    it("shows the API error and keeps the entered values", async () => {
        mocked.createCreative.mockRejectedValue(new Error("Parent campaign not found"));
        renderModal();
        await screen.findByText("Banner A");
        fill(screen.getByPlaceholderText("Image URL"), "https://cdn.example.com/new.png");
        fill(screen.getByPlaceholderText("Click-through URL"), "https://example.com/new");

        submitForm(screen.getByRole("button", { name: "Add creative" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Parent campaign not found");
        expect(screen.getByPlaceholderText("Image URL")).toHaveValue("https://cdn.example.com/new.png");
    });
});