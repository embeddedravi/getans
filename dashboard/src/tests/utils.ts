import { fireEvent } from "@testing-library/react";

/** Set a controlled input/select value. */
export function fill(el: HTMLElement, value: string) {
    fireEvent.change(el, { target: { value } });
}

/**
 * Submit the form containing `control`. Uses a submit event directly so tests
 * exercise our handlers rather than jsdom's constraint validation (e.g. the
 * float-step check on `step="0.0001"` inputs).
 */
export function submitForm(control: HTMLElement) {
    const form = control.closest("form");
    if (!form) throw new Error("control is not inside a <form>");
    fireEvent.submit(form);
}