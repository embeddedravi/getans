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
  captchaChallenge: () => request<{ challenge: string; question: string }>("/auth/captcha-challenge"),
  login: (mobile: string, password: string, captcha_challenge?: string, captcha_answer?: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ mobile, password, captcha_challenge, captcha_answer }),
    }),

  me: () => request("/auth/me"),
  updateProfile: (payload: { first_name: string | null; last_name: string | null; email: string | null }) =>
    request("/auth/me", { method: "PATCH", body: JSON.stringify(payload) }),
  changePassword: (current_password: string, new_password: string) =>
    request<{ message: string }>("/auth/me/password", { method: "POST", body: JSON.stringify({ current_password, new_password }) }),
  deleteAccount: (password: string) =>
    request<void>("/auth/me", { method: "DELETE", body: JSON.stringify({ password }) }),
  listAdminAdvertisers: () => request<import("../types").Advertiser[]>("/admin/advertisers"),
  listAdminUsers: () => request<import("../types").AdminUser[]>("/admin/users"),
  updateAdminUser: (id: number, payload: {
    role: import("../types").UserRole;
    is_active: boolean;
    publisher_id: number | null;
    advertiser_id: number | null;
  }) => request<import("../types").AdminUser>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listPendingApprovals: () => request<import("../types").PendingApprovals>("/admin/approvals/pending"),
  listPayouts: (status?: string) => request<import("../types").Payout[]>(`/payouts${status ? `?status=${encodeURIComponent(status)}` : ""}`),
  listAdvertiserTopUps: () => request<import("../types").AdvertiserTopUp[]>("/payments/topups"),
  listRecentEvents: (limit = 100, afterId?: number) => request<import("../types").LiveEvent[]>(`/admin/events/recent?limit=${limit}${afterId === undefined ? "" : `&after_id=${afterId}`}`),
  listMyRecentEvents: (limit = 100, afterId?: number) => request<import("../types").LiveEvent[]>(`/admin/events/mine?limit=${limit}${afterId === undefined ? "" : `&after_id=${afterId}`}`),
  updatePayout: (id: number, payload: { status?: import("../types").PayoutStatus; reference?: string }) =>
    request<import("../types").Payout>(`/payouts/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  reviewPublisher: (id: number, status: "active" | "suspended" | "rejected", rejection_reason?: string) =>
    request(`/admin/publishers/${id}/review`, { method: "PATCH", body: JSON.stringify({ status, rejection_reason }) }),
  reviewAdvertiser: (id: number, status: "active" | "suspended" | "rejected", rejection_reason?: string) =>
    request(`/admin/advertisers/${id}/review`, { method: "PATCH", body: JSON.stringify({ status, rejection_reason }) }),
  reviewAdUnit: (id: number, status: "approved" | "rejected", rejection_reason?: string) =>
    request(`/admin/ad-units/${id}/review`, { method: "PATCH", body: JSON.stringify({ status, rejection_reason }) }),
  listAdUnitReports: (id: number) =>
    request<{ id: number; creative_id: number | null; reason: string; created_at: string }[]>(`/admin/ad-units/${id}/reports`),
  listAvailablePublisherAdUnits: () => request<import("../types").AvailablePublisherAdUnit[]>("/publishers/available-ad-units"),
  listSupportTickets: (status?: string) => request<import("../types").SupportTicketSummary[]>(`/support/tickets${status && status !== "all" ? `?status=${encodeURIComponent(status)}` : ""}`),
  getSupportTicket: (id: number) => request<import("../types").SupportTicket>(`/support/tickets/${id}`),
  createSupportTicket: (payload: { subject: string; category: import("../types").SupportTicketCategory; message: string }) =>
    request<import("../types").SupportTicketSummary>("/support/tickets", { method: "POST", body: JSON.stringify(payload) }),
  addSupportTicketMessage: (id: number, body: string, is_internal = false) =>
    request<import("../types").SupportTicketMessage>(`/support/tickets/${id}/messages`, { method: "POST", body: JSON.stringify({ body, is_internal }) }),
  updateSupportTicket: (id: number, payload: { status?: import("../types").SupportTicketStatus; priority?: import("../types").SupportTicketPriority; assigned_to_id?: number | null }) =>
    request<import("../types").SupportTicketSummary>(`/support/tickets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  listSupportStaff: () => request<{ id: number; name: string; role: "staff" | "admin" }[]>("/support/staff"),
  setAdUnitActive: (id: number, is_active: boolean) =>
    request(`/admin/ad-units/${id}/active`, { method: "PATCH", body: JSON.stringify({ is_active }) }),
  signup: (payload: unknown) =>
    request("/auth/signup", { method: "POST", body: JSON.stringify(payload) }),
  requestOtp: (mobile: string, captcha_challenge?: string, captcha_answer?: string) =>
    request<{ message: string; expires_in: number; resend_after: number }>("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ mobile, captcha_challenge, captcha_answer }),
    }),
  verifyOtp: (mobile: string, code: string, captcha_challenge?: string, captcha_answer?: string) =>
    request<{ message: string }>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ mobile, code, captcha_challenge, captcha_answer }),
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
  listPollCreatives: () => request<{ creative: import("../types").Creative; campaign: { id: number; name: string } }[]>("/creatives/polls"),
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
  getPollResults: (creativeId: number) =>
    request<import("../types").PollResults>(`/creatives/${creativeId}/poll-results`),

  listMedia: () => request<import("../types").MediaAsset[]>("/media"),
  uploadMedia: async (file: File) => {
    const form = new FormData();
    form.append("file", file);
    const token = getToken();
    const res = await fetch(`${BASE_URL}/media`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(errorMessage(body, res.status));
    }
    return res.json() as Promise<import("../types").MediaAsset>;
  },
  deleteMedia: (id: number) => request<void>(`/media/${id}`, { method: "DELETE" }),

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

  advertiserWallet: () => request<import("../types").AdvertiserWallet>("/payments/wallet"),
  advertiserTopUpHistory: () => request<import("../types").AdvertiserTopUp[]>("/payments/history"),
  createAdvertiserTopUpOrder: (amount: number) =>
    request<import("../types").RazorpayTopUpOrder>("/payments/orders", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  verifyAdvertiserTopUp: (payload: {
    razorpay_order_id: string;
    razorpay_payment_id: string;
    razorpay_signature: string;
  }) => request<import("../types").AdvertiserWallet>("/payments/verify", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
};
