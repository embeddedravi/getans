import "@testing-library/jest-dom/vitest";
import { act, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter }  from "react-router-dom";
import { api } from "../lib/api";
import { subscribeToMetrics } from "../lib/socket";
import type { MetricUpdate } from "../types";
import { AnalyticsPage } from "./AnalyticsPage";

vi.mock("../components/Layout", () => ({
    Layout: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("../lib/api", () => ({ api: { me: vi.fn(), campaignStats: vi.fn(), listPendingApprovals: vi.fn() } }));
vi.mock("../lib/socket", () => ({ subscribeToMetrics: vi.fn() }));
// jsdom has no layout, so recharts renders nothing useful; stub it.
vi.mock("recharts", () => ({
    ResponsiveContainer: ({ children }: { children: ReactNode }) => <div>{children}</div>,
    BarChart: ({ data }: { data: unknown[] }) => <div data-testid="bar-chart" data-points={data.length} />,
    Bar: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    XAxis: () => null,
    YAxis: () => null,
}));

const campaignStats = vi.mocked(api.campaignStats);
const currentUser = vi.mocked(api.me);
const pendingApprovals = vi.mocked(api.listPendingApprovals);
const subscribe = vi.mocked(subscribeToMetrics);

const renderPage = () => render(<MemoryRouter ><AnalyticsPage /></MemoryRouter>);

const STATS = [
    { campaign_id: 1, campaign_name: "Autumn sale", impressions: 1000, clicks: 100, ctr: 10 },
    { campaign_id: 2, campaign_name: "Winter push", impressions: 500, clicks: 50, ctr: 10 },
];

let push: (u: MetricUpdate) => void;
const unsubscribe = vi.fn();

const metric = (type: "impression" | "click"): MetricUpdate => ({
    type,
    campaign_id: 1,
    ad_unit_id: 1,
    timestamp: "2026-09-29T00:00:00Z",
});

const valueOf = (label: string) => screen.getByText(label).nextElementSibling;

beforeEach(() => {
    vi.resetAllMocks();
    currentUser.mockResolvedValue({ role: "admin" });
    campaignStats.mockResolvedValue(STATS);
    pendingApprovals.mockResolvedValue({ publishers: [], advertisers: [], ad_units: [] });
    subscribe.mockImplementation((cb) => {
        push = cb;
        return unsubscribe;
    });
});

describe("AnalyticsPage", () => {
    it("requests exactly the last 7 days", async () => {
        renderPage();
        await screen.findByTestId("bar-chart");

        const [start, end] = campaignStats.mock.calls[0];
        expect(new Date(end).getTime() - new Date(start).getTime()).toBe(7 * 24 * 60 * 60 * 1000);
    });

    it("sums 7-day impressions and charts one bar group per campaign", async () => {
        renderPage();

        expect(await screen.findByTestId("bar-chart")).toHaveAttribute("data-points", "2");
        expect(valueOf("7-day impressions")).toHaveTextContent((1500).toLocaleString());
    });

    it("shows the empty state when there is no data", async () => {
        campaignStats.mockResolvedValue([]);
        renderPage();

        expect(await screen.findByText(/no event data yet/i)).toBeInTheDocument();
    });

    it("degrades to the empty state when the request fails", async () => {
        campaignStats.mockRejectedValue(new Error("boom"));
        renderPage();

        expect(await screen.findByText(/no event data yet/i)).toBeInTheDocument();
    });

    it("increments the live counters from metric updates", async () => {
        renderPage();
        await screen.findByTestId("bar-chart");
        expect(valueOf("Impressions this session")).toHaveTextContent("0");

        act(() => {
            push(metric("impression"));
            push(metric("impression"));
            push(metric("click"));
        });

        expect(valueOf("Impressions this session")).toHaveTextContent("2");
        expect(valueOf("Clicks this session")).toHaveTextContent("1");
    });

    it("unsubscribes from metrics on unmount", async () => {
        const { unmount } = renderPage();
        await screen.findByTestId("bar-chart");

        unmount();

        expect(unsubscribe).toHaveBeenCalledTimes(1);
    });
});
