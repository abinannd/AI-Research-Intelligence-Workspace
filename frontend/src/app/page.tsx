"use client";

import { useEffect, useState, type FormEvent } from "react";

import { api } from "@/lib/api";
import { getAccessToken, setAccessToken } from "@/lib/token";
import type { User, Workspace } from "@/lib/types";
import { formatClock } from "@/lib/utils";

const SELECTED_WORKSPACE_KEY = "ari_selected_workspace_id";

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Something went wrong. Please try again.";
}

export default function Home() {
  const [user, setUser] = useState<User | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [authPending, setAuthPending] = useState(false);

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string | null>(null);
  const [workspaceLoading, setWorkspaceLoading] = useState(false);
  const [workspaceError, setWorkspaceError] = useState<string | null>(null);
  const [refreshCount, setRefreshCount] = useState(0);
  const [workspaceName, setWorkspaceName] = useState("");
  const [createPending, setCreatePending] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [createSuccess, setCreateSuccess] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      if (!getAccessToken()) {
        setSessionReady(true);
        return;
      }

      try {
        const currentUser = await api.me();
        if (active) setUser(currentUser);
      } catch (error) {
        if (active) setAuthError(`Your saved session could not be restored: ${errorMessage(error)}`);
      } finally {
        if (active) setSessionReady(true);
      }
    }

    void restoreSession();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!user) return;
    let active = true;

    async function loadWorkspaces() {
      setWorkspaceLoading(true);
      setWorkspaceError(null);
      try {
        const results = await api.listWorkspaces();
        if (!active) return;
        setWorkspaces(results);

        const savedId = window.localStorage.getItem(SELECTED_WORKSPACE_KEY);
        setSelectedWorkspaceId((currentId) => {
          if (currentId && results.some((workspace) => workspace.id === currentId)) return currentId;
          if (savedId && results.some((workspace) => workspace.id === savedId)) return savedId;
          return null;
        });
      } catch (error) {
        if (active) setWorkspaceError(errorMessage(error));
      } finally {
        if (active) setWorkspaceLoading(false);
      }
    }

    void loadWorkspaces();
    return () => {
      active = false;
    };
  }, [user, refreshCount]);

  async function handleAuthSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError(null);
    setAuthPending(true);
    try {
      const normalizedEmail = email.trim();
      const response =
        authMode === "signup"
          ? await api.signup(normalizedEmail, password)
          : await api.login(normalizedEmail, password);
      setAccessToken(response.access_token);
      setUser(response.user);
      setPassword("");
    } catch (error) {
      setAuthError(errorMessage(error));
    } finally {
      setAuthPending(false);
    }
  }

  async function handleCreateWorkspace(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = workspaceName.trim();
    if (!name) {
      setCreateError("Enter a workspace name.");
      setCreateSuccess(null);
      return;
    }

    setCreatePending(true);
    setCreateError(null);
    setCreateSuccess(null);
    try {
      const created = await api.createWorkspace(name);
      setWorkspaces((current) => [created, ...current.filter((workspace) => workspace.id !== created.id)]);
      setSelectedWorkspaceId(created.id);
      window.localStorage.setItem(SELECTED_WORKSPACE_KEY, created.id);
      setWorkspaceName("");
      setCreateSuccess(`Workspace "${created.name}" created.`);
    } catch (error) {
      setCreateError(errorMessage(error));
    } finally {
      setCreatePending(false);
    }
  }

  function handleSelectWorkspace(workspaceId: string) {
    setSelectedWorkspaceId(workspaceId);
    window.localStorage.setItem(SELECTED_WORKSPACE_KEY, workspaceId);
    setCreateSuccess(null);
  }

  function handleSignOut() {
    setAccessToken(null);
    window.localStorage.removeItem(SELECTED_WORKSPACE_KEY);
    setUser(null);
    setWorkspaces([]);
    setSelectedWorkspaceId(null);
    setWorkspaceError(null);
    setCreateError(null);
    setCreateSuccess(null);
    setAuthError(null);
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-8 px-4 py-8 sm:px-6 sm:py-12">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-wide text-sky-700">
            AI Research Intelligence
          </p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
            Research Workspace
          </h1>
          <p className="mt-2 max-w-2xl text-base text-slate-600">
            Create a workspace or choose one to continue your research.
          </p>
        </div>
        {user && (
          <div className="flex items-center gap-3">
            <span className="max-w-56 truncate text-sm text-slate-600" title={user.email}>
              {user.email}
            </span>
            <button
              className="rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
              onClick={handleSignOut}
              type="button"
            >
              Sign out
            </button>
          </div>
        )}
      </header>

      {!sessionReady ? (
        <p className="text-sm text-slate-600" role="status">Checking your session…</p>
      ) : !user ? (
        <section className="w-full max-w-xl rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <h2 className="text-xl font-semibold text-slate-900">
            {authMode === "login" ? "Sign in to your account" : "Create your account"}
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            Use your existing Research Workspace account to view and manage workspaces.
          </p>
          <form className="mt-6 flex flex-col gap-4" onSubmit={handleAuthSubmit}>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
              Email
              <input
                autoComplete="email"
                className="rounded-md border border-slate-300 px-3 py-2.5 text-base text-slate-950 outline-none focus:border-sky-700 focus:ring-2 focus:ring-sky-100"
                onChange={(event) => setEmail(event.target.value)}
                required
                type="email"
                value={email}
              />
            </label>
            <label className="flex flex-col gap-1.5 text-sm font-medium text-slate-700">
              Password
              <input
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
                className="rounded-md border border-slate-300 px-3 py-2.5 text-base text-slate-950 outline-none focus:border-sky-700 focus:ring-2 focus:ring-sky-100"
                minLength={authMode === "signup" ? 8 : undefined}
                onChange={(event) => setPassword(event.target.value)}
                required
                type="password"
                value={password}
              />
            </label>
            {authError && (
              <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
                {authError}
              </p>
            )}
            <button
              className="rounded-md bg-sky-800 px-4 py-2.5 font-semibold text-white hover:bg-sky-900 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800"
              disabled={authPending}
              type="submit"
            >
              {authPending
                ? "Please wait…"
                : authMode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
          </form>
          <p className="mt-5 text-sm text-slate-600">
            {authMode === "login" ? "New to the workspace?" : "Already have an account?"}{" "}
            <button
              className="font-semibold text-sky-800 underline underline-offset-2 hover:text-sky-950"
              onClick={() => {
                setAuthMode(authMode === "login" ? "signup" : "login");
                setAuthError(null);
              }}
              type="button"
            >
              {authMode === "login" ? "Create an account" : "Sign in"}
            </button>
          </p>
        </section>
      ) : (
        <div className="grid gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1.35fr)]">
          <section className="h-fit rounded-xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
            <h2 className="text-xl font-semibold text-slate-900">Create workspace</h2>
            <p className="mt-1 text-sm text-slate-600">
              Start a separate space for a research project or topic.
            </p>
            <form className="mt-5 flex flex-col gap-3" onSubmit={handleCreateWorkspace}>
              <label className="text-sm font-medium text-slate-700" htmlFor="workspace-name">
                Workspace name
              </label>
              <input
                autoComplete="off"
                className="rounded-md border border-slate-300 px-3 py-2.5 text-base text-slate-950 outline-none focus:border-sky-700 focus:ring-2 focus:ring-sky-100"
                id="workspace-name"
                maxLength={200}
                onChange={(event) => setWorkspaceName(event.target.value)}
                placeholder="e.g. Climate policy review"
                value={workspaceName}
              />
              {createError && (
                <p className="text-sm text-red-800" role="alert">{createError}</p>
              )}
              {createSuccess && (
                <p className="text-sm text-emerald-800" role="status">{createSuccess}</p>
              )}
              <button
                className="mt-1 rounded-md bg-sky-800 px-4 py-2.5 font-semibold text-white hover:bg-sky-900 disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-800"
                disabled={createPending}
                type="submit"
              >
                {createPending ? "Creating…" : "Create workspace"}
              </button>
            </form>
          </section>

          <section className="min-w-0">
            <div className="mb-4 flex items-center justify-between gap-3">
              <div>
                <h2 className="text-xl font-semibold text-slate-900">Your workspaces</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Select a workspace to continue.
                </p>
              </div>
              <button
                className="shrink-0 rounded-md border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white disabled:cursor-not-allowed disabled:opacity-60 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700"
                disabled={workspaceLoading}
                onClick={() => setRefreshCount((count) => count + 1)}
                type="button"
              >
                {workspaceLoading ? "Loading…" : "Refresh"}
              </button>
            </div>

            {workspaceError && (
              <div className="mb-4 flex flex-col gap-3 rounded-lg border border-red-200 bg-red-50 p-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-red-800" role="alert">
                  Could not load workspaces: {workspaceError}
                </p>
                <button
                  className="shrink-0 self-start rounded-md border border-red-300 px-3 py-2 text-sm font-medium text-red-900 hover:bg-red-100 sm:self-auto"
                  onClick={() => setRefreshCount((count) => count + 1)}
                  type="button"
                >
                  Try again
                </button>
              </div>
            )}

            {workspaceLoading && workspaces.length === 0 ? (
              <p className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600" role="status">
                Loading workspaces…
              </p>
            ) : workspaces.length > 0 ? (
              <ul className="grid gap-3 sm:grid-cols-2">
                {workspaces.map((workspace) => {
                  const selected = selectedWorkspaceId === workspace.id;
                  return (
                    <li key={workspace.id}>
                      <button
                        aria-pressed={selected}
                        className={`h-full w-full rounded-lg border bg-white p-4 text-left shadow-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-700 ${
                          selected
                            ? "border-sky-700 ring-1 ring-sky-700"
                            : "border-slate-200 hover:border-slate-400"
                        }`}
                        onClick={() => handleSelectWorkspace(workspace.id)}
                        type="button"
                      >
                        <span className="block break-words font-semibold text-slate-900">
                          {workspace.name}
                        </span>
                        <span className="mt-2 block text-sm text-slate-600">
                          Created {formatClock(workspace.created_at)}
                        </span>
                        {selected && (
                          <span className="mt-3 inline-block rounded-full bg-sky-100 px-2.5 py-1 text-xs font-semibold text-sky-900">
                            Selected
                          </span>
                        )}
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : !workspaceLoading && !workspaceError ? (
              <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-center">
                <h3 className="font-semibold text-slate-900">No workspaces yet</h3>
                <p className="mt-1 text-sm text-slate-600">
                  Create your first workspace to get started.
                </p>
              </div>
            ) : null}

            {selectedWorkspaceId && (
              <p className="mt-4 rounded-lg bg-sky-50 px-4 py-3 text-sm text-sky-950" role="status">
                Current workspace:{" "}
                <span className="font-semibold">
                  {workspaces.find((workspace) => workspace.id === selectedWorkspaceId)?.name}
                </span>
              </p>
            )}
          </section>
        </div>
      )}
    </main>
  );
}
