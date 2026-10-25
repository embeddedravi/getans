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
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
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
  const [search, setSearch] = useState("");
  const isStaff = role === "staff" || role === "admin";
  const visibleTickets = tickets.filter((ticket) => `${ticket.subject} ${ticket.customer_name} ${ticket.category} ${ticket.status} ${ticket.priority} ${ticket.id}`.toLocaleLowerCase().includes(search.trim().toLocaleLowerCase()));
  const openCount = tickets.filter((ticket) => ticket.status === "open" || ticket.status === "in_progress").length;
  const waitingCount = tickets.filter((ticket) => ticket.status === "waiting_on_customer").length;
  const resolvedCount = tickets.filter((ticket) => ticket.status === "resolved" || ticket.status === "closed").length;
  const statusTone: Record<SupportTicketStatus, string> = {
    open: "badge-info", in_progress: "badge-primary", waiting_on_customer: "badge-warning", resolved: "badge-success", closed: "badge-ghost",
  };
  const priorityTone: Record<SupportTicketPriority, string> = {
    low: "badge-ghost", normal: "badge-info", high: "badge-warning", urgent: "badge-error",
  };

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
      setCurrentUserId((user as { id?: number }).id ?? null);
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
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><p className="text-sm">{isStaff ? "Review and respond to customer requests." : "Create a request and follow replies from the support team."}</p><p className="mt-1 text-xs">{tickets.length} {tickets.length === 1 ? "ticket" : "tickets"} in this view</p></div>
        {!isStaff && <button className="btn btn-primary btn-sm" onClick={() => setShowCreate((value) => !value)}>{showCreate ? "Cancel" : "+ New support ticket"}</button>}
        {isStaff && <div className="flex flex-wrap gap-2">
          <input type="search" aria-label="Search support tickets" className="input input-bordered input-sm w-52" placeholder="Search tickets…" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select aria-label="Filter tickets by status" className="select select-bordered select-sm" value={statusFilter} onChange={(event) => void changeFilter(event.target.value)}>
            <option value="all">All statuses</option>{STATUSES.map((value) => <option key={value} value={value}>{label(value)}</option>)}
          </select>
        </div>}
      </div>

      {isStaff && <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {[{ title: "Open / in progress", value: openCount, tone: "text-info" }, { title: "Waiting on customer", value: waitingCount, tone: "text-warning" }, { title: "Resolved / closed", value: resolvedCount, tone: "text-success" }].map((item) => <div key={item.title} className="rounded border border-base-300 bg-base-200 px-4 py-3"><p className="text-xs">{item.title}</p><p className={`mt-1 text-2xl font-semibold tabular-nums ${item.tone}`}>{item.value}</p></div>)}
      </div>}

      {showCreate && <form onSubmit={createTicket} className="overflow-hidden rounded-xl border border-base-300 bg-base-200 shadow-sm">
        <div className="border-b border-base-300 bg-gradient-to-r from-primary/10 via-base-200 to-base-200 px-5 py-4 sm:px-6">
          <span className="badge badge-primary badge-outline badge-sm">SUPPORT REQUEST</span>
          <h2 className="mt-2 text-lg font-semibold">Tell us what you need help with</h2>
          <p className="mt-1 text-sm text-base-content/70">Share a few details and the support team will reply in this ticket.</p>
        </div>
        <div className="space-y-4 p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_220px]">
            <label className="form-control gap-1.5"><span className="text-sm font-medium">Subject</span><input className="input input-bordered w-full bg-base-100" placeholder="A short summary of the issue" required minLength={3} maxLength={200} value={subject} onChange={(event) => setSubject(event.target.value)} /><span className="text-xs text-base-content/60">Keep it brief and specific.</span></label>
            <label className="form-control gap-1.5"><span className="text-sm font-medium">Category</span><select className="select select-bordered w-full bg-base-100" value={category} onChange={(event) => setCategory(event.target.value as SupportTicketCategory)}>{CATEGORIES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select><span className="text-xs text-base-content/60">Choose the closest match.</span></label>
          </div>
          <label className="form-control gap-1.5"><span className="text-sm font-medium">Description</span><textarea className="textarea textarea-bordered min-h-36 w-full bg-base-100" placeholder="What happened? Include the steps you took and what you expected to happen." required maxLength={5000} rows={5} value={initialMessage} onChange={(event) => setInitialMessage(event.target.value)} /><span className="text-right text-xs text-base-content/60">{initialMessage.length}/5000</span></label>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-base-300 bg-base-100/50 px-5 py-4 sm:px-6">
          <p className="text-xs text-base-content/60">Please don’t include passwords or payment credentials.</p>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Submitting…" : "Submit support request"}<span aria-hidden="true">→</span></button>
        </div>
      </form>}

      <div className="grid gap-4 lg:grid-cols-[minmax(260px,360px)_1fr]">
        <section className="overflow-hidden rounded border border-base-300 bg-base-200">
          <header className="flex items-center justify-between border-b border-base-300 px-4 py-3"><span className="font-medium">Inbox</span><span className="badge badge-ghost badge-sm">{visibleTickets.length}</span></header>
          {loading ? <p className="p-5 text-sm">Loading tickets…</p> : visibleTickets.length ? <ul className="max-h-[72vh] divide-y divide-base-300 overflow-y-auto">
            {visibleTickets.map((ticket) => <li key={ticket.id}>
              <button className={`w-full border-l-2 p-4 text-left transition hover:bg-base-300/60 ${selected?.id === ticket.id ? "border-primary bg-primary/5" : "border-transparent"}`} onClick={() => void openTicket(ticket)}>
                <span className="flex items-start justify-between gap-2"><span className="line-clamp-2 font-medium">{ticket.subject}</span><span className={`badge badge-xs capitalize ${statusTone[ticket.status]}`}>{label(ticket.status)}</span></span>
                {isStaff && <span className="mt-2 block text-xs font-medium">{ticket.customer_name}</span>}
                <span className="mt-2 flex flex-wrap items-center gap-1.5 text-xs"><span className="text-base-content/60">#{ticket.id}</span><span className="badge badge-ghost badge-xs capitalize">{label(ticket.category)}</span><span className={`badge badge-xs capitalize ${priorityTone[ticket.priority]}`}>{ticket.priority}</span></span>
              </button>
            </li>)}
          </ul> : <div className="p-8 text-center"><p className="font-medium">{isStaff ? "No matching tickets" : "No support tickets yet"}</p><p className="mt-1 text-sm">{isStaff ? "Try another search or status." : "Open a ticket and the support team will follow up here."}</p></div>}
        </section>

        <section className="flex min-h-[32rem] flex-col overflow-hidden rounded-lg border border-base-300 bg-base-200 shadow-sm">
          {selected ? <>
            <header className="space-y-3 border-b border-base-300 bg-base-200 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h2 className="text-lg font-semibold">{selected.subject}</h2><span className={`badge badge-sm capitalize ${statusTone[selected.status]}`}>{label(selected.status)}</span></div><p className="mt-1 text-xs">Ticket #{selected.id} · {label(selected.category)} · Updated {new Date(selected.updated_at).toLocaleString()}</p>{isStaff && <p className="mt-1 text-xs font-medium">{selected.customer_name}{selected.customer_email ? ` · ${selected.customer_email}` : ""}{selected.customer_mobile ? ` · ${selected.customer_mobile}` : ""}</p>}</div><span className={`badge badge-sm capitalize ${priorityTone[selected.priority]}`}>{selected.priority} priority</span></div>
              {isStaff && <div className="flex flex-wrap items-center gap-2 border-t border-base-300 pt-3">
                <label className="text-xs">Status<select aria-label="Ticket status" className="select select-bordered select-xs ml-2" value={selected.status} onChange={(event) => void updateTicket({ status: event.target.value as SupportTicketStatus })}>{STATUSES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
                <label className="text-xs">Priority<select aria-label="Ticket priority" className="select select-bordered select-xs ml-2" value={selected.priority} onChange={(event) => void updateTicket({ priority: event.target.value as SupportTicketPriority })}>{PRIORITIES.map((value) => <option key={value} value={value}>{label(value)}</option>)}</select></label>
                <label className="text-xs">Assignee<select aria-label="Assign ticket" className="select select-bordered select-xs ml-2" value={selected.assigned_to_id ?? ""} onChange={(event) => void updateTicket({ assigned_to_id: event.target.value ? Number(event.target.value) : null })}>
                  <option value="">Unassigned</option>{staff.map((person) => <option key={person.id} value={person.id}>{person.name} ({person.role})</option>)}
                </select></label>
              </div>}
            </header>
            <div className="flex-1 space-y-4 overflow-y-auto bg-base-100/40 p-4">
              {selected.messages.map((message) => <article key={message.id} className={`max-w-[92%] rounded-xl border p-3 shadow-sm sm:max-w-[80%] ${message.is_internal ? "mx-auto border-warning/50 bg-warning/10" : message.author_id === currentUserId ? "ml-auto border-primary/20 bg-primary/10" : "mr-auto border-base-300 bg-base-100"}`}>
                <div className="flex flex-wrap justify-between gap-3 text-xs"><span className="font-medium">{message.author_id === currentUserId ? "You" : message.author_name}{message.is_internal ? " · Internal note" : ""}</span><time className="text-base-content/60">{new Date(message.created_at).toLocaleString()}</time></div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed">{message.body}</p>
              </article>)}
            </div>
            {selected.status !== "closed" ? <form onSubmit={sendReply} className="space-y-3 border-t border-base-300 bg-base-200 p-4">
              {isStaff && <label className="flex w-fit items-center gap-2 rounded bg-warning/10 px-2 py-1 text-xs"><input className="checkbox checkbox-xs" type="checkbox" checked={internal} onChange={(event) => setInternal(event.target.checked)} />Internal note — only staff can see this</label>}
              <textarea className="textarea textarea-bordered w-full bg-base-100" required maxLength={5000} rows={3} placeholder={internal ? "Write an internal note…" : "Write a reply…"} value={reply} onChange={(event) => setReply(event.target.value)} />
              <div className="flex items-center justify-between gap-3"><span className="text-xs">{reply.length}/5000</span><button className="btn btn-primary btn-sm" disabled={busy}>{busy ? "Sending…" : internal ? "Add internal note" : "Send reply"}</button></div>
            </form> : <p className="border-t border-base-300 p-4 text-center text-sm">This ticket is closed. Start a new ticket if you need more help.</p>}
          </> : <p className="p-8 text-center text-sm">Select a ticket to view its conversation.</p>}
        </section>
      </div>
    </div>
  </Layout>;
}
