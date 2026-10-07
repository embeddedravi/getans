import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { fill, submitForm } from "../tests/utils";
import { SignupPage } from "./SignupPage";

vi.mock("../lib/api", () => ({ api: { signup: vi.fn() } }));
const signup = vi.mocked(api.signup);

function renderPage() {
    return render(
        <MemoryRouter  initialEntries={["/signup"]}>
            <Routes>
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/verify" element={<div>verify page</div>} />
                <Route path="/login" element={<div>login page</div>} />
            </Routes>
        </MemoryRouter>
    );
}

function fillCommon() {
    fill(screen.getByLabelText("Company name"), "Acme Ads");
    fill(screen.getByLabelText("Mobile number"), "98765 43210");
    fill(screen.getByLabelText("Billing email"), "billing@acme.example");
    fill(screen.getByLabelText("Password"), "supersecret1");
}

beforeEach(() => {
    vi.resetAllMocks();
});

describe("SignupPage", () => {
    it("submits an advertiser signup and goes to /verify", async () => {
        signup.mockResolvedValue({});
        renderPage();
        fillCommon();

        submitForm(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByText("verify page")).toBeInTheDocument();
        expect(signup).toHaveBeenCalledWith({
            role: "advertiser",
            organization_name: "Acme Ads",
            mobile: "98765 43210",
            password: "supersecret1",
            email: "billing@acme.example",
            billing_email: "billing@acme.example",
        });
    });

    it("shows publisher fields and sends site_url and payout_email", async () => {
        signup.mockResolvedValue({});
        renderPage();
        fill(screen.getByLabelText("I am a"), "publisher");
        fill(screen.getByLabelText("Site / company name"), "Daily News");
        fill(screen.getByLabelText("Mobile number"), "98765 43210");
        fill(screen.getByLabelText("Site URL"), "https://news.example.com");
        fill(screen.getByLabelText("Payout email"), "pay@news.example.com");
        fill(screen.getByLabelText("Password"), "supersecret1");

        submitForm(screen.getByRole("button", { name: "Create account" }));

        await waitFor(() =>
            expect(signup).toHaveBeenCalledWith({
                role: "publisher",
                organization_name: "Daily News",
                mobile: "98765 43210",
                password: "supersecret1",
                email: null,
                site_url: "https://news.example.com",
                payout_email: "pay@news.example.com",
            })
        );
    });

    it("shows the server error and stays on the page", async () => {
        signup.mockRejectedValue(new Error("An account with these details already exists"));
        renderPage();
        fillCommon();

        submitForm(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("already exists");
        expect(screen.queryByText("verify page")).not.toBeInTheDocument();
    });

    it("uses a generic message when the rejection is not an Error", async () => {
        signup.mockRejectedValue("boom");
        renderPage();
        fillCommon();

        submitForm(screen.getByRole("button", { name: "Create account" }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not create account");
    });

    it("links back to sign in", () => {
        renderPage();
        fireEvent.click(screen.getByRole("link", { name: "Sign in" }));
        expect(screen.getByText("login page")).toBeInTheDocument();
    });
});
