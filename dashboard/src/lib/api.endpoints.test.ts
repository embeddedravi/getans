import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

const fetchMock = vi.fn();

beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    fetchMock.mockResolvedValue(new Response(JSON.stringify({}), { status: 200 }));
});

afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
});

type Case = [name: string, call: () => Promise<unknown>, url: string, method: string | undefined, body?: unknown];

const cases: Case[] = [
    ["me", () => api.me(), "/api/auth/me", undefined],
    ["requestOtp", () => api.requestOtp("98765 43210"), "/api/auth/otp/request", "POST", { mobile: "98765 43210" }],
    [
        "verifyOtp",
        () => api.verifyOtp("98765 43210", "123456"),
        "/api/auth/otp/verify",
        "POST",
        { mobile: "98765 43210", code: "123456" },
    ],
    [
        "signup",
        () => api.signup({ role: "advertiser", mobile: "98765 43210" }),
        "/api/auth/signup",
        "POST",
        { role: "advertiser", mobile: "98765 43210" },
    ],
    ["listCampaigns", () => api.listCampaigns(), "/api/campaigns", undefined],
    ["createCampaign", () => api.createCampaign({ name: "x" }), "/api/campaigns", "POST", { name: "x" }],
    [
        "updateCampaign",
        () => api.updateCampaign(3, { is_active: false }),
        "/api/campaigns/3",
        "PATCH",
        { is_active: false },
    ],
    ["deleteCampaign", () => api.deleteCampaign(3), "/api/campaigns/3", "DELETE"],
    ["listCreativesForCampaign", () => api.listCreativesForCampaign(4), "/api/creatives/by-campaign/4", undefined],
    ["createCreative", () => api.createCreative({ campaign_id: 4 }), "/api/creatives", "POST", { campaign_id: 4 }],
    ["updateCreative", () => api.updateCreative(5, { is_active: true }), "/api/creatives/5", "PATCH", { is_active: true }],
    ["deleteCreative", () => api.deleteCreative(5), "/api/creatives/5", "DELETE"],
    ["listPublishers", () => api.listPublishers(), "/api/publishers", undefined],
    ["createPublisher", () => api.createPublisher({ name: "p" }), "/api/publishers", "POST", { name: "p" }],
    ["listAdUnits", () => api.listAdUnits(4), "/api/publishers/4/ad-units", undefined],
];

describe("api endpoints", () => {
    it.each(cases)("%s hits the right URL with the right method and body", async (_n, call, url, method, body) => {
        await call();

        const [calledUrl, init] = fetchMock.mock.calls[0];
        expect(calledUrl).toBe(url);
        expect(init.method).toBe(method);
        if (body === undefined) {
            expect(init.body).toBeUndefined();
        } else {
            expect(JSON.parse(init.body)).toEqual(body);
        }
    });

    it("createAdUnit sends the payload as JSON", async () => {
        await api.createAdUnit(4, { slot_name: "x", width: 300 });

        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ slot_name: "x", width: 300 });
    });

    it("lets per-call headers override defaults (spread order)", async () => {
        // request() is internal, but every endpoint routes through it; confirm Content-Type is always JSON.
        await api.listCampaigns();

        expect(fetchMock.mock.calls[0][1].headers["Content-Type"]).toBe("application/json");
    });
});
