import "@testing-library/jest-dom/vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter }  from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { fill, submitForm } from "../tests/utils";
import { VerifyMobilePage } from "./VerifyMobilePage";

vi.mock("../lib/api", () => ({ api: { requestOtp: vi.fn(), verifyOtp: vi.fn() } }));
const requestOtp = vi.mocked(api.requestOtp);
const verifyOtp = vi.mocked(api.verifyOtp);

const MOBILE = "98765 43210";

function renderPage() {
    return render(
        <MemoryRouter >
            <VerifyMobilePage />
        </MemoryRouter>
    );
}

async function requestCode() {
    fill(screen.getByLabelText("Mobile number"), MOBILE);
    submitForm(screen.getByRole("button", { name: /send code/i }));
    return screen.findByLabelText("Verification code");
}

beforeEach(() => {
    vi.resetAllMocks();
    requestOtp.mockResolvedValue({ message: "ok", expires_in: 300, resend_after: 60 });
});

afterEach(() => {
    vi.useRealTimers();
});

describe("step 1: request a code", () => {
    it("sends the code and moves to the code step with a resend cooldown", async () => {
        renderPage();

        await requestCode();

        expect(requestOtp).toHaveBeenCalledWith(MOBILE);
        expect(screen.getByText(/has an account/i)).toHaveTextContent(MOBILE);
        expect(screen.getByRole("button", { name: "Resend in 60s" })).toBeDisabled();
    });

    it("stays on the mobile step and shows the error when the request fails", async () => {
        requestOtp.mockRejectedValue(new Error("Please wait before requesting another code"));
        renderPage();

        fill(screen.getByLabelText("Mobile number"), MOBILE);
        submitForm(screen.getByRole("button", { name: /send code/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Please wait");
        expect(screen.getByLabelText("Mobile number")).toBeInTheDocument();
        expect(screen.queryByLabelText("Verification code")).not.toBeInTheDocument();
    });
});

describe("step 2: verify the code", () => {
    it("strips non-digits and only enables Verify at six digits", async () => {
        renderPage();
        const code = await requestCode();
        const verify = screen.getByRole("button", { name: /verify number/i });

        fill(code, "12ab3");
        expect(code).toHaveValue("123");
        expect(verify).toBeDisabled();

        fill(code, "123456");
        expect(verify).toBeEnabled();
    });

    it("shows the success screen once the code is accepted", async () => {
        verifyOtp.mockResolvedValue({ message: "Mobile number verified" });
        renderPage();
        fill(await requestCode(), "123456");

        submitForm(screen.getByRole("button", { name: /verify number/i }));

        expect(await screen.findByText(/is verified/i)).toHaveTextContent(MOBILE);
        expect(verifyOtp).toHaveBeenCalledWith(MOBILE, "123456");
        expect(screen.getByRole("link", { name: "Go to sign in" })).toHaveAttribute("href", "/login");
    });

    it("shows an error and keeps the code form when verification fails", async () => {
        verifyOtp.mockRejectedValue(new Error("Invalid or expired code"));
        renderPage();
        fill(await requestCode(), "123456");

        submitForm(screen.getByRole("button", { name: /verify number/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Invalid or expired code");
        expect(screen.getByLabelText("Verification code")).toBeInTheDocument();
    });

    it("lets the user go back and use a different number", async () => {
        renderPage();
        await requestCode();

        fireEvent.click(screen.getByRole("button", { name: /use a different number/i }));

        expect(screen.getByLabelText("Mobile number")).toBeInTheDocument();
    });

    it("counts the resend cooldown down and re-enables the button", async () => {
        vi.useFakeTimers();
        requestOtp.mockResolvedValue({ message: "ok", expires_in: 300, resend_after: 3 });
        renderPage();

        fill(screen.getByLabelText("Mobile number"), MOBILE);
        await act(async () => {
            submitForm(screen.getByRole("button", { name: /send code/i }));
            await Promise.resolve();
            await Promise.resolve();
        });
        expect(screen.getByRole("button", { name: "Resend in 3s" })).toBeDisabled();

        for (let i = 0; i < 3; i++) {
            act(() => {
                vi.advanceTimersByTime(1000);
            });
        }

        expect(screen.getByRole("button", { name: "Resend code" })).toBeEnabled();
    });
});
