const BASE_URL = "/api";

function getToken(): string | null {
  return localStorage.getItem("access_token");
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
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  login: (email: string, password: string) =>
    request<{ access_token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request("/auth/me"),

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
    request(`/analytics/campaigns?start=${start}&end=${end}`),
};
