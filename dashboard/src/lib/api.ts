const BASE_URL = "/api";

function getToken(): string | null {
  return localStorage.getItem("access_token");
}

// FastAPI returns `detail` as a string for most errors, but as a list of
// {msg} objects for 422 validation errors.
function errorMessage(body: { detail?: unknown }, status: number): string {
  const { detail } = body;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => String((d as { msg?: string }).msg ?? "Invalid input").replace(/^Value error, /, ""))
      .join(", ");
  }
  return `Request failed: ${status}`;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();

  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(errorMessage(body, res.status));
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (mobile: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ mobile, password }),
    }),

  me: () => request("/auth/me"),
  signup: (payload: unknown) =>
    request("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  requestOtp: (mobile: string) =>
    request<{ message: string; expires_in: number; resend_after: number }>("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ mobile }),
    }),
  verifyOtp: (mobile: string, code: string) =>
    request<{ message: string }>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ mobile, code }),
    }),
  resetPassword: (payload: unknown) =>
    request<{ message: string }>("/auth/forgot-password/reset", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listCampaigns: () => request("/campaigns"),
  createCampaign: (payload: unknown) =>
    request("/campaigns", { method: "POST", body: JSON.stringify(payload) }),
  updateCampaign: (id: number, payload: unknown) =>
    request(`/campaigns/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCampaign: (id: number) => request(`/campaigns/${id}`, { method: "DELETE" }),

  listCreativesForCampaign: (campaignId: number) =>
    request(`/creatives/by-campaign/${campaignId}`),
  createCreative: (payload: unknown) =>
    request("/creatives", { method: "POST", body: JSON.stringify(payload) }),
  deleteCreative: (id: number) => request(`/creatives/${id}`, { method: "DELETE" }),
  updateCreative: (id: number, payload: unknown) =>
    request(`/creatives/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  reviewCreative: (id: number, review_status: string, rejection_reason?: string) =>
    request(`/creatives/${id}/review`, {
      method: "PATCH",
      body: JSON.stringify({ review_status, rejection_reason }),
    }),

  listPublishers: () => request("/publishers"),
  createPublisher: (payload: unknown) =>
    request("/publishers", { method: "POST", body: JSON.stringify(payload) }),
  listAdUnits: (publisherId: number) => request(`/publishers/${publisherId}/ad-units`),
  createAdUnit: (publisherId: number, payload: unknown) =>
    request(`/publishers/${publisherId}/ad-units`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  campaignStats: (start: string, end: string) =>
    request(`/analytics/campaigns?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`),
};
