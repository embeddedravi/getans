import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { fill, submitForm } from "../tests/utils";
import { VerifyMobilePage } from "./VerifyMobilePage";

vi.mock("../lib/api", () => ({ api: { requestOtp: vi.fn(), verifyOtp: vi.fn() } }));
const requestOtp = vi.mocked(api.requestOtp);
const verifyOtp = vi.mocked(api.verifyOtp);

const MOBILE = "98765 43210";

function renderPage() {
    return render(
        <MemoryRouter>
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
});

describe("VerifyMobilePage gaps", () => {
    it("uses a generic message when sending rejects with a non-Error", async () => {
        requestOtp.mockRejectedValue("boom");
        renderPage();

        fill(screen.getByLabelText("Mobile number"), MOBILE);
        submitForm(screen.getByRole("button", { name: /send code/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not send the code");
    });

    it("uses a generic message when verifying rejects with a non-Error", async () => {
        requestOtp.mockResolvedValue({ message: "ok", expires_in: 300, resend_after: 60 });
        verifyOtp.mockRejectedValue("boom");
        renderPage();
        fill(await requestCode(), "123456");

        submitForm(screen.getByRole("button", { name: /verify number/i }));

        expect(await screen.findByRole("alert")).toHaveTextContent("Could not verify the code");
    });

    it("requests a new code when Resend is clicked and clears the entered code", async () => {
        // resend_after: 0 means the button is enabled immediately, no timers needed.
        requestOtp.mockResolvedValue({ message: "ok", expires_in: 300, resend_after: 0 });
        renderPage();
        const code = await requestCode();
        fill(code, "123");

        fireEvent.click(screen.getByRole("button", { name: "Resend code" }));

        await waitFor(() => expect(requestOtp).toHaveBeenCalledTimes(2));
        expect(requestOtp).toHaveBeenLastCalledWith(MOBILE);
        await waitFor(() => expect(screen.getByLabelText("Verification code")).toHaveValue(""));
    });
});
