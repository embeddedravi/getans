import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { fill, submitForm } from "../tests/utils";
import { LoginPage } from "./LoginPage";

vi.mock("../lib/api", () => ({ api: { login: vi.fn() } }));
const login = vi.mocked(api.login);

function renderPage() {
    return render(
        <MemoryRouter initialEntries={["/login"]}>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/" element={<div>dashboard home</div>} />
                <Route path="/verify" element={<div>verify page</div>} />
            </Routes>
        </MemoryRouter>
    );
}

function signIn(mobile = "98765 43210", password = "hunter2hunter2") {
    fill(screen.getByLabelText("Mobile number"), mobile);
    fill(screen.getByLabelText("Password"), password);
    submitForm(screen.getByRole("button", { name: /sign in/i }));
}

beforeEach(() => {
    vi.resetAllMocks();
});

describe("LoginPage", () => {
    it("stores the token and navigates home on success", async () => {
        login.mockResolvedValue({ access_token: "tok-123" });
        renderPage();

        signIn();

        expect(await screen.findByText("dashboard home")).toBeInTheDocument();
        expect(login).toHaveBeenCalledWith("98765 43210", "hunter2hunter2");
        expect(localStorage.getItem("access_token")).toBe("tok-123");
    });

    it("shows the server's error and stays on the page when login fails", async () => {
        login.mockRejectedValue(new Error("Incorrect mobile number or password"));
        renderPage();

        signIn();

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Incorrect mobile number or password"
        );
        expect(localStorage.getItem("access_token")).toBeNull();
        expect(screen.queryByText("dashboard home")).not.toBeInTheDocument();
    });

    it("uses a generic message when the rejection is not an Error", async () => {
        login.mockRejectedValue("boom");
        renderPage();

        signIn();

        expect(await screen.findByRole("alert")).toHaveTextContent("Login failed");
    });

    it("disables the button while the request is in flight", async () => {
        login.mockReturnValue(new Promise(() => { })); // never settles
        renderPage();

        signIn();

        const busy = await screen.findByRole("button", { name: /signing in/i });
        expect(busy).toBeDisabled();
    });

    it("nudges unverified users toward verification", async () => {
        login.mockRejectedValue(new Error("Mobile number not verified"));
        renderPage();
        expect(screen.getByText(/first time signing in/i)).toBeInTheDocument();

        signIn();

        expect(await screen.findByText(/isn't verified yet/i)).toBeInTheDocument();
    });

    it("links to the verification page", () => {
        renderPage();
        expect(screen.getByRole("link", { name: /verify your mobile number/i })).toHaveAttribute(
            "href",
            "/verify"
        );
    });
    it("links to the signup page", () => {
        renderPage();
        expect(screen.getByRole("link", { name: /create an account/i })).toHaveAttribute(
            "href",
            "/signup"
        );
    });
});