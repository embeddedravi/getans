import { FormEvent, useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { SupportTicket, SupportTicketCategory, SupportTicketPriority, SupportTicketStatus, SupportTicketSummary } from "../types";

const STATUSES: SupportTicketStatus[] = ["open", "in_progress", "waiting_on_customer", "resolved", "closed"];
const PRIORITIES: SupportTicketPriority[] = ["low", "normal", "high", "urgent"];
const CATEGORIES: SupportTicketCategory[] = ["account", "billing", "campaign", "creative", "ad_delivery", "payout", "other"];
const label = (value: string) => value.replace(/_/g, " ");

export function SupportPage() {
  const [role, setRole] = useState<string | null>(null);
  const [tickets, setTickets] = useState<SupportTicketSummary[]>([]);
  const [staff, setStaff] = useState<{ id: number; name: string; role: "staff" | "admin" }[]>([]);
  const [selected, setSelected] = useState<SupportTicket | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [showCreate, setShowCreate] = useState(false);
  const [subject, setSubject] = useState("");
  const [category, setCategory] = useState<SupportTicketCategory>("other");
  const [initialMessage, setInitialMessage] = useState("");
  const [reply, setReply] = useState("");
  const [internal, setInternal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const isStaff = role === "staff" || role === "admin";

  async function refreshTickets(filter = statusFilter) {
    const rows = await api.listSupportTickets(filter);
    setTickets(rows);
    if (selected) {
      const refreshed = rows.find((ticket) => ticket.id === selected.id);
      if (refreshed) setSelected(await api.getSupportTicket(refreshed.id));
      else setSelected(null);
    }
  }

  useEffect(() => {
    api.me().then(async (user) => {
      const accountRole = (user as { role?: string }).role || "";
      setRole(accountRole);
      const rows = await api.listSupportTickets();
      setTickets(rows);
      if (accountRole === "staff" || accountRole === "admin") setStaff(await api.listSupportStaff());
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load support tickets"))
      .finally(() => setLoading(false));
  }, []);

  async function openTicket(ticket: SupportTicketSummary) {
    setError("");
    try { setSelected(await api.getSupportTicket(ticket.id)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load this ticket"); }
  }

  async function createTicket(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const created = await api.createSupportTicket({ subject, category, message: initialMessage });
      setSubject(""); setInitialMessage(""); setCategory("other"); setShowCreate(false);
      await refreshTickets();
      await openTicket(created);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not create ticket"); }
    finally { setBusy(false); }
  }

  async function sendReply(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setError("");
    try {
      await api.addSupportTicketMessage(selected.id, reply, internal);
      setReply(""); setInternal(false);
      await refreshTickets();
      setSelected(await api.getSupportTicket(selected.id));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not send reply"); }
    finally { setBusy(false); }
  }

  async function updateTicket(payload: { status?: SupportTicketStatus; priority?: SupportTicketPriority; assigned_to_id?: number | null }) {
    if (!selected) return;
    setError("");
    try {
      await api.updateSupportTicket(selected.id, payload);
      await refreshTickets();
      setSelected(await api.getSupportTicket(selected.id));
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not update ticket"); }
  }

  async function changeFilter(value: string) {
    setStatusFilter(value);
    setLoading(true);
    try {
      const rows = await api.listSupportTickets(value);
      setTickets(rows);
      if (selected && !rows.some((ticket) => ticket.id === selected.id)) setSelected(null);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load tickets"); }
    finally { setLoading(false); }
  }

  return <Layout title={isStaff ? "Support queue" : "Customer support"}>
    <div className="space-y-4">
      {error && <div role="alert" className="alert alert-error py-2 text-sm">{error}</div>}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">{isStaff ? "Review and respond to customer requests." : "Create a request and follow replies from the support team."}</p>
        {!isStaff && <button className="btn btn-primary btn-sm" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Cancel" : "New support ticket"}</button>}
        {isStaff && <select aria-label="Filter tickets by status" className="select select-bordered select-sm" value={statusFilter} onChange={(event) => void changeFilter(event.target.value)}>
          <option value="all">All statuses</option>{STATUSES.map((value) => <option key={value} value={value}>{label(value)}</option>)}
        </select>}
      </div>

      {showCreate && <form onSubmit={createTicket} className="space-y-3 rounded border border-base-300 bg-base-200 p-4">
        <h2 className="font-semibold">Open a support ticket</h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="form-control"><span className="label-text mb-1">Subject</span><input className="input input-bordered input-sm" required minLength={3} maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} /></label>
          <label className="form-control"><span className="label-text mb-1">Category</span><select className="select select-bordered select-sm" value={category} onChange={(event) => setCategory(event.target.value as SupportTicketCategory)}>{CATEGORIES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
        </div>
        <label className="form-control"><span className="label-text mb-1">How can we help?</span><textarea className="textarea textarea-bordered" required maxLength={5000} rows={4} value={initialMessage} onChange={(event) => setInitialMessage(event.target.value)} /></label>
        <button className="btn btn-primary btn-sm" disabled={busy}>{busy ? "Sending…" : "Submit ticket"}</button>
      </form>}

      <div className="grid gap-4 lg:grid-cols-[minmax(260px,360px)_1fr]">
        <section className="overflow-hidden rounded border border-base-300 bg-base-200">
          <header className="border-b border-base-300 px-4 py-3 font-medium">Tickets <span className="text-xs font-normal">({tickets.length})</span></header>
          {loading ? <p className="p-5 text-sm">Loading tickets…</p> : tickets.length ? <ul className="divide-y divide-base-300">
            {tickets.map((ticket) => <li key={ticket.id}>
              <button className={`w-full p-4 text-left hover:bg-base-300/60 ${selected?.id === ticket.id ? "bg-base-300/60" : ""}`} onClick={() => void openTicket(ticket)}>
                <span className="flex items-center justify-between gap-2"><span className="truncate font-medium">{ticket.subject}</span><span className="badge badge-xs">{label(ticket.status)}</span></span>
                {isStaff && <span className="mt-1 block text-xs">{ticket.customer_name}</span>}
                <span className="mt-1 block text-xs">#{ticket.id} · {label(ticket.category)} · {label(ticket.priority)}</span>
              </button>
            </li>)}
          </ul> : <p className="p-5 text-sm">{isStaff ? "No tickets match this filter." : "No support tickets yet."}</p>}
        </section>

        <section className="min-h-80 rounded border border-base-300 bg-base-200">
          {selected ? <>
            <header className="flex flex-wrap items-start justify-between gap-3 border-b border-base-300 p-4">
              <div><h2 className="font-semibold">{selected.subject}</h2><p className="mt-1 text-xs">#{selected.id} · {label(selected.category)} · {selected.customer_name}</p>{isStaff && (selected.customer_email || selected.customer_mobile) && <p className="mt-1 text-xs">{selected.customer_email}{selected.customer_email && selected.customer_mobile ? " · " : ""}{selected.customer_mobile}</p>}</div>
              {isStaff && <div className="flex flex-wrap gap-2">
                <select aria-label="Ticket status" className="select select-bordered select-xs" value={selected.status} onChange={(event) => void updateTicket({ status: event.target.value as SupportTicketStatus })}>{STATUSES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select>
                <select aria-label="Ticket priority" className="select select-bordered select-xs" value={selected.priority} onChange={(event) => void updateTicket({ priority: event.target.value as SupportTicketPriority })}>{PRIORITIES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select>
                <select aria-label="Assign ticket" className="select select-bordered select-xs" value={selected.assigned_to_id ?? ""} onChange={(event) => void updateTicket({ assigned_to_id: event.target.value ? Number(event.target.value) : null })}>
                  <option value="">Unassigned</option>{staff.map((person) => <option key={person.id} value={person.id}>{person.name} ({person.role})</option>)}
                </select>
              </div>}
            </header>
            <div className="max-h-[55vh] space-y-3 overflow-y-auto p-4">
              {selected.messages.map((message) => <article key={message.id} className={`rounded p-3 ${message.is_internal ? "border border-warning/50 bg-warning/10" : "bg-base-100"}`}>
                <div className="flex flex-wrap justify-between gap-2 text-xs"><span className="font-medium">{message.author_name}{message.is_internal ? " · Internal note" : ""}</span><time>{new Date(message.created_at).toLocaleString()}</time></div>
                <p className="mt-2 whitespace-pre-wrap text-sm">{message.body}</p>
              </article>)}
            </div>
            {selected.status !== "closed" && <form onSubmit={sendReply} className="space-y-2 border-t border-base-300 p-4">
              {isStaff && <label className="flex items-center gap-2 text-xs"><input className="checkbox checkbox-xs" type="checkbox" checked={internal} onChange={(event) => setInternal(event.target.checked)} />Add internal note (customer cannot see this)</label>}
              <textarea className="textarea textarea-bordered w-full" required maxLength={5000} rows={3} placeholder={internal ? "Write an internal note…" : "Write a reply…"} value={reply} onChange={(event) => setReply(event.target.value)} />
              <button className="btn btn-primary btn-sm" disabled={busy}>{busy ? "Sending…" : internal ? "Add note" : "Send reply"}</button>
            </form>}
          </> : <p className="p-8 text-center text-sm">Select a ticket to view its conversation.</p>}
        </section>
      </div>
    </div>
  </Layout>;
}
