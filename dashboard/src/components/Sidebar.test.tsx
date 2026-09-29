import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { Sidebar } from "./Sidebar";

const renderAt = (path: string) =>
    render(
        <MemoryRouter initialEntries={[path]}>
            <Sidebar />
        </MemoryRouter>
    );

describe("Sidebar", () => {
    it("links to every section", () => {
        renderAt("/");

        expect(screen.getByRole("link", { name: "Analytics" })).toHaveAttribute("href", "/");
        expect(screen.getByRole("link", { name: "Campaigns" })).toHaveAttribute("href", "/campaigns");
        expect(screen.getByRole("link", { name: "Publishers & slots" })).toHaveAttribute(
            "href",
            "/publishers"
        );
    });

    it("highlights only the current section", () => {
        renderAt("/campaigns");

        expect(screen.getByRole("link", { name: "Campaigns" })).toHaveClass("font-medium");
        expect(screen.getByRole("link", { name: "Analytics" })).not.toHaveClass("font-medium");
    });

    it("does not keep Analytics highlighted on nested routes (end matching)", () => {
        renderAt("/publishers");

        expect(screen.getByRole("link", { name: "Analytics" })).not.toHaveClass("font-medium");
        expect(screen.getByRole("link", { name: "Publishers & slots" })).toHaveClass("font-medium");
    });
});