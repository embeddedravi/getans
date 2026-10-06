import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { api } from "../lib/api";
import type { AdminUser, Advertiser, Publisher, UserRole } from "../types";

type UserEdit = {
  role: UserRole;
  is_active: boolean;
  publisher_id: number | null;
  advertiser_id: number | null;
};

function editFromUser(user: AdminUser): UserEdit {
  return {
    role: user.role,
    is_active: user.is_active,
    publisher_id: user.publisher_id,
    advertiser_id: user.advertiser_id,
  };
}

function sameEdit(edit: UserEdit, user: AdminUser) {
  return edit.role === user.role
    && edit.is_active === user.is_active
    && edit.publisher_id === user.publisher_id
    && edit.advertiser_id === user.advertiser_id;
}

export function AdminUsersPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [publishers, setPublishers] = useState<Publisher[]>([]);
  const [advertisers, setAdvertisers] = useState<Advertiser[]>([]);
  const [edits, setEdits] = useState<Record<number, UserEdit>>({});
  const [currentUserId, setCurrentUserId] = useState<number | null>(null);
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listAdminUsers(), api.listPublishers(), api.listAdminAdvertisers(), api.me()])
      .then(([userList, publisherList, advertiserList, current]) => {
        const records = userList as AdminUser[];
        setUsers(records);
        setEdits(Object.fromEntries(records.map((user) => [user.id, editFromUser(user)])));
        setPublishers(publisherList as Publisher[]);
        setAdvertisers(advertiserList as Advertiser[]);
        setCurrentUserId((current as { id: number }).id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load users"))
      .finally(() => setLoading(false));
  }, []);

  function changeRole(user: AdminUser, role: UserRole) {
    const current = edits[user.id] ?? editFromUser(user);
    setEdits((previous) => ({
      ...previous,
      [user.id]: {
        ...current,
        role,
        publisher_id: role === "publisher"
          ? (current.role === "publisher" ? current.publisher_id : null)
          : null,
        advertiser_id: role === "advertiser"
          ? (current.role === "advertiser" ? current.advertiser_id : null)
          : null,
      },
    }));
  }

  async function save(user: AdminUser) {
    const edit = edits[user.id] ?? editFromUser(user);
    if (edit.role === "publisher" && edit.publisher_id == null) {
      setError("Choose a publisher before assigning the publisher role.");
      return;
    }
    if (edit.role === "advertiser" && edit.advertiser_id == null) {
      setError("Choose an advertiser before assigning the advertiser role.");
      return;
    }
    if (user.is_active && !edit.is_active && !window.confirm(`Deactivate ${user.first_name || user.mobile || user.email}?`)) return;

    setError("");
    setBusy(user.id);
    try {
      const updated = await api.updateAdminUser(user.id, edit);
      setUsers((previous) => previous.map((item) => item.id === user.id ? updated : item));
      setEdits((previous) => ({ ...previous, [user.id]: editFromUser(updated) }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not update user");
    } finally {
      setBusy(null);
    }
  }

  return (
    <Layout title="Manage users">
      <div className="space-y-4">
        <div>
          <p className="text-sm text-neutral-content">Manage dashboard roles, tenant access, and account status.</p>
          <p className="mt-1 text-xs text-neutral-content">Superuser accounts and your own role or status are protected.</p>
        </div>
        {error && <div role="alert" className="alert alert-error py-2 text-sm"><span>{error}</span></div>}

        <div className="overflow-x-auto rounded border border-base-300 bg-base-200">
          <table className="table">
            <thead>
              <tr className="text-xs text-neutral-content">
                <th>User</th><th>Role</th><th>Tenant</th><th>Status</th><th>Last login</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => {
                const edit = edits[user.id] ?? editFromUser(user);
                const locked = user.is_superuser || user.id === currentUserId;
                const dirty = !sameEdit(edit, user);
                const displayName = [user.first_name, user.last_name].filter(Boolean).join(" ");
                const tenantLabel = user.role === "publisher"
                  ? publishers.find((publisher) => publisher.id === user.publisher_id)?.name ?? `Publisher #${user.publisher_id}`
                  : user.role === "advertiser"
                    ? advertisers.find((advertiser) => advertiser.id === user.advertiser_id)?.name ?? `Advertiser #${user.advertiser_id}`
                    : "—";

                return (
                  <tr key={user.id} className="border-b border-base-300 last:border-0 align-top">
                    <td className="min-w-52">
                      <div className="font-medium">{displayName || user.mobile || user.email || `User #${user.id}`}</div>
                      <div className="text-xs text-neutral-content">{user.mobile || user.email || `#${user.id}`}</div>
                      {user.is_superuser && <span className="badge badge-xs badge-warning mt-1">Superuser</span>}
                    </td>
                    <td>
                      <select
                        className="select select-bordered select-xs bg-base-100"
                        value={edit.role}
                        disabled={locked || busy === user.id}
                        onChange={(event) => changeRole(user, event.target.value as UserRole)}
                        aria-label={`Role for user ${user.id}`}
                      >
                        <option value="admin">Admin</option>
                        <option value="staff">Staff</option>
                        <option value="publisher">Publisher</option>
                        <option value="advertiser">Advertiser</option>
                      </select>
                    </td>
                    <td>
                      {edit.role === "publisher" ? (
                        <select
                          className="select select-bordered select-xs max-w-48 bg-base-100"
                          value={edit.publisher_id ?? ""}
                          disabled={locked || busy === user.id}
                          onChange={(event) => setEdits((previous) => ({
                            ...previous,
                            [user.id]: { ...edit, publisher_id: event.target.value ? Number(event.target.value) : null },
                          }))}
                          aria-label={`Publisher for user ${user.id}`}
                        >
                          <option value="">Choose publisher</option>
                          {publishers.map((publisher) => <option key={publisher.id} value={publisher.id}>{publisher.name}</option>)}
                        </select>
                      ) : edit.role === "advertiser" ? (
                        <select
                          className="select select-bordered select-xs max-w-48 bg-base-100"
                          value={edit.advertiser_id ?? ""}
                          disabled={locked || busy === user.id}
                          onChange={(event) => setEdits((previous) => ({
                            ...previous,
                            [user.id]: { ...edit, advertiser_id: event.target.value ? Number(event.target.value) : null },
                          }))}
                          aria-label={`Advertiser for user ${user.id}`}
                        >
                          <option value="">Choose advertiser</option>
                          {advertisers.map((advertiser) => <option key={advertiser.id} value={advertiser.id}>{advertiser.name}</option>)}
                        </select>
                      ) : tenantLabel}
                    </td>
                    <td>
                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          className="toggle toggle-success toggle-sm"
                          checked={edit.is_active}
                          disabled={locked || busy === user.id}
                          onChange={(event) => setEdits((previous) => ({
                            ...previous,
                            [user.id]: { ...edit, is_active: event.target.checked },
                          }))}
                          aria-label={`${edit.is_active ? "Active" : "Inactive"} status for user ${user.id}`}
                        />
                        <span className={`badge badge-xs ${edit.is_active ? "badge-success" : "badge-ghost"}`}>
                          {edit.is_active ? "Active" : "Inactive"}
                        </span>
                      </label>
                    </td>
                    <td className="text-xs text-neutral-content">
                      {user.last_login_at ? new Date(user.last_login_at).toLocaleString() : "Never"}
                    </td>
                    <td>
                      <button
                        className="btn btn-primary btn-xs"
                        disabled={!dirty || locked || busy === user.id}
                        onClick={() => void save(user)}
                      >
                        {busy === user.id ? "Saving..." : "Save"}
                      </button>
                    </td>
                  </tr>
                );
              })}
              {!loading && users.length === 0 && <tr><td colSpan={6} className="py-8 text-center text-sm text-neutral-content">No users found.</td></tr>}
              {loading && <tr><td colSpan={6} className="py-8 text-center text-sm text-neutral-content">Loading users...</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}
