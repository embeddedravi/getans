import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";

vi.mock("./Sidebar", () => ({ Sidebar: () => <nav data-testid="sidebar" /> }));
vi.mock("./TopBar", () => ({
    TopBar: ({ title }: { title: string }) => <header data-testid="topbar">{title}</header>,
}));

describe("Layout", () => {
    it("renders the sidebar and a top bar with the given title", () => {
        render(
            <Layout title="Campaigns">
                <p>content</p>
            </Layout>
        );

        expect(screen.getByTestId("sidebar")).toBeInTheDocument();
        expect(screen.getByTestId("topbar")).toHaveTextContent("Campaigns");
    });

    it("renders children inside the main region", () => {
        render(
            <Layout title="Analytics">
                <p>page body</p>
            </Layout>
        );

        expect(within(screen.getByRole("main")).getByText("page body")).toBeInTheDocument();
    });

    it("keeps the top bar outside the scrollable main region", () => {
        render(
            <Layout title="Analytics">
                <p>page body</p>
            </Layout>
        );

        expect(screen.getByRole("main")).not.toContainElement(screen.getByTestId("topbar"));
    });
});
