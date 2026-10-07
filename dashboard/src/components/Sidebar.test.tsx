import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter }  from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { Sidebar } from "./Sidebar";

vi.mock("../lib/api", () => ({ api: { me: vi.fn() } }));
const mockedMe = vi.mocked(api.me);

beforeEach(() => {
    vi.resetAllMocks();
    mockedMe.mockResolvedValue({ role: "admin" });
});

const renderAt = (path: string) =>
    render(
        <MemoryRouter  initialEntries={[path]}>
            <Sidebar />
        </MemoryRouter>
    );

describe("Sidebar", () => {
    it("links to every section", async () => {
        renderAt("/");

        expect(await screen.findByRole("link", { name: "Overview" })).toHaveAttribute("href", "/");
        expect(await screen.findByRole("link", { name: "Campaigns" })).toHaveAttribute("href", "/manage-campaign");
        expect(await screen.findByRole("link", { name: "Publishers" })).toHaveAttribute(
            "href",
            "/manage-publisher"
        );
    });

    it("highlights only the current section", async () => {
        renderAt("/manage-campaign");

        expect(await screen.findByRole("link", { name: "Campaigns" })).toHaveClass("font-medium");
        expect(await screen.findByRole("link", { name: "Overview" })).not.toHaveClass("font-medium");
    });

    it("does not keep Overview highlighted on nested routes (end matching)", async () => {
        renderAt("/manage-publisher");

        expect(await screen.findByRole("link", { name: "Overview" })).not.toHaveClass("font-medium");
        expect(await screen.findByRole("link", { name: "Publishers" })).toHaveClass("font-medium");
    });
});
