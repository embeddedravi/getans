import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import App from "./App";

vi.mock("./pages/AnalyticsPage", () => ({ AnalyticsPage: () => <div>analytics page</div> }));
vi.mock("./pages/CampaignsPage", () => ({ CampaignsPage: () => <div>campaigns page</div> }));
vi.mock("./pages/PublishersPage", () => ({ PublishersPage: () => <div>publishers page</div> }));
vi.mock("./pages/SignupPage", () => ({ SignupPage: () => <div>signup page</div> }));
vi.mock("./pages/LoginPage", () => ({ LoginPage: () => <div>login page</div> }));
vi.mock("./pages/VerifyMobilePage", () => ({ VerifyMobilePage: () => <div>verify page</div> }));

function visit(path: string) {
    window.history.pushState({}, "", path);
    return render(<App />);
}

beforeEach(() => {
    window.history.pushState({}, "", "/");
});

describe("routing and auth guard", () => {
    it.each(["/", "/campaigns", "/publishers"])(
        "redirects %s to /login without a token",
        (path) => {
            visit(path);

            expect(screen.getByText("login page")).toBeInTheDocument();
            expect(window.location.pathname).toBe("/login");
        }
    );

    it.each([
        ["/", "analytics page"],
        ["/campaigns", "campaigns page"],
        ["/publishers", "publishers page"],
    ])("renders %s when a token is present", (path, text) => {
        localStorage.setItem("access_token", "tok");

        visit(path);

        expect(screen.getByText(text)).toBeInTheDocument();
    });

    it("serves /verify without a token", () => {
        visit("/verify");

        expect(screen.getByText("verify page")).toBeInTheDocument();
    });
    it("serves /signup without a token", () => {
        visit("/signup");

        expect(screen.getByText("signup page")).toBeInTheDocument();
    });
});