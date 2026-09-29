import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

const fetchMock = vi.fn();

function respond(status: number, body?: unknown) {
    fetchMock.mockResolvedValueOnce(
        new Response(body === undefined ? null : JSON.stringify(body), { status })
    );
}

beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
});

describe("request plumbing", () => {
    it("sends JSON and the bearer token from localStorage", async () => {
        localStorage.setItem("access_token", "abc");
        respond(200, []);

        await api.listCampaigns();

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe("/api/campaigns");
        expect(init.headers).toEqual({
            "Content-Type": "application/json",
            Authorization: "Bearer abc",
        });
    });

    it("omits Authorization when there is no token", async () => {
        respond(200, []);
        await api.listCampaigns();
        expect(fetchMock.mock.calls[0][1].headers).toEqual({ "Content-Type": "application/json" });
    });

    it("returns undefined for 204 responses", async () => {
        respond(204);
        await expect(api.deleteCampaign(3)).resolves.toBeUndefined();

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe("/api/campaigns/3");
        expect(init.method).toBe("DELETE");
    });
});

describe("error handling", () => {
    it("uses a string `detail` as the message", async () => {
        respond(401, { detail: "Incorrect mobile number or password" });
        await expect(api.login("9876543210", "wrongpass1")).rejects.toThrow(
            "Incorrect mobile number or password"
        );
    });

    it("joins 422 validation messages and strips the pydantic prefix", async () => {
        respond(422, {
            detail: [
                { msg: "Value error, Enter a valid 10-digit Indian mobile number" },
                { msg: "Field required" },
            ],
        });
        await expect(api.login("123", "x")).rejects.toThrow(
            "Enter a valid 10-digit Indian mobile number, Field required"
        );
    });

    it("falls back to 'Invalid input' for a validation item without msg", async () => {
        respond(422, { detail: [{}] });
        await expect(api.listCampaigns()).rejects.toThrow("Invalid input");
    });

    it("falls back to the status code when the body is not JSON", async () => {
        fetchMock.mockResolvedValueOnce(new Response("<html>bad gateway</html>", { status: 502 }));
        await expect(api.listCampaigns()).rejects.toThrow("Request failed: 502");
    });

    it("falls back to the status code when `detail` has an unexpected shape", async () => {
        respond(400, { detail: { foo: 1 } });
        await expect(api.listCampaigns()).rejects.toThrow("Request failed: 400");
    });
});

describe("endpoints", () => {
    it("login posts mobile and password as JSON", async () => {
        respond(200, { access_token: "t" });
        await api.login("98765 43210", "pw123456");

        const [url, init] = fetchMock.mock.calls[0];
        expect(url).toBe("/api/auth/login");
        expect(init.method).toBe("POST");
        expect(JSON.parse(init.body)).toEqual({ mobile: "98765 43210", password: "pw123456" });
    });

    it("campaignStats URL-encodes the date range", async () => {
        respond(200, []);
        await api.campaignStats("2026-09-22T00:00:00.000Z", "2026-09-29T00:00:00.000Z");

        expect(fetchMock.mock.calls[0][0]).toBe(
            "/api/analytics/campaigns?start=2026-09-22T00%3A00%3A00.000Z&end=2026-09-29T00%3A00%3A00.000Z"
        );
    });

    it("reviewCreative sends the reason only when given", async () => {
        respond(200, {});
        await api.reviewCreative(10, "approved");
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ review_status: "approved" });

        respond(200, {});
        await api.reviewCreative(10, "rejected", "Blurry");
        expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
            review_status: "rejected",
            rejection_reason: "Blurry",
        });
        expect(fetchMock.mock.calls[1][0]).toBe("/api/creatives/10/review");
    });

    it("createAdUnit posts to the publisher's ad-units collection", async () => {
        respond(201, {});
        await api.createAdUnit(4, { slot_name: "x" });
        expect(fetchMock.mock.calls[0][0]).toBe("/api/publishers/4/ad-units");
        expect(fetchMock.mock.calls[0][1].method).toBe("POST");
    });
});