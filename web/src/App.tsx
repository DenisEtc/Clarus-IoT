import React, { useEffect, useMemo, useState } from "react";
import {
  clearToken,
  downloadScoredCsv,
  getJob,
  listJobs,
  getSubscriptionStatus,
  getToken,
  login,
  register,
  renewSubscription,
  uploadCsv,
  type JobResponse,
  type SubscriptionStatus
} from "./api";
import { Badge, Button, Card, CardBody, CardHeader, Input, Label } from "./ui";

type View = "auth" | "dashboard" | "job";

function statusTone(status: string): "ok" | "warn" | "bad" | "neutral" {
  if (status === "done") return "ok";
  if (status === "running" || status === "queued") return "warn";
  if (status === "failed") return "bad";
  return "neutral";
}

function pct(x: number) {
  return (x * 100).toFixed(2) + "%";
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

function formatShortDate(iso?: string | null) {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  // compact for lists
  return d.toLocaleString(undefined, { year: "2-digit", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

export default function App() {
  const [view, setView] = useState<View>("auth");
  const [email, setEmail] = useState("example@example.com");
  const [password, setPassword] = useState("example");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [currentJob, setCurrentJob] = useState<JobResponse | null>(null);
  const [jobError, setJobError] = useState<string | null>(null);

  const [sub, setSub] = useState<SubscriptionStatus | null>(null);
  const [subLoading, setSubLoading] = useState(false);
  const [subErr, setSubErr] = useState<string | null>(null);

  const hasToken = useMemo(() => Boolean(getToken()), [view]);

  useEffect(() => {
    setView(getToken() ? "dashboard" : "auth");
  }, []);

  async function refreshSubscription() {
    if (!getToken()) return;
    setSubErr(null);
    setSubLoading(true);
    try {
      const s = await getSubscriptionStatus();
      setSub(s);
    } catch (e: any) {
      setSubErr(String(e?.message ?? e));
      setSub(null);
    } finally {
      setSubLoading(false);
    }
  }

  useEffect(() => {
    if (view === "dashboard" && getToken()) {
      refreshSubscription();
      // restore history on login / refresh
      (async () => {
        try {
          const items = await listJobs(50, 0);
          setJobs(items);
        } catch {
          // history is best-effort; UI still works without it
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  async function onRegister() {
    setErr(null);
    setLoading(true);
    try {
      await register(email, password);
      await login(email, password);
      setView("dashboard");
      // jobs list will be fetched by dashboard effect
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  async function onLogin() {
    setErr(null);
    setLoading(true);
    try {
      await login(email, password);
      setView("dashboard");
      // jobs list will be fetched by dashboard effect
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    } finally {
      setLoading(false);
    }
  }

  async function onRenew() {
    setSubErr(null);
    setSubLoading(true);
    try {
      await renewSubscription("MONTHLY_1M");
      await refreshSubscription();
    } catch (e: any) {
      setSubErr(String(e?.message ?? e));
    } finally {
      setSubLoading(false);
    }
  }

  async function onUpload(file: File) {
    setErr(null);
    setLoading(true);
    try {
      const created = await uploadCsv(file);
      setJobs((prev) => [created, ...prev]);
      setCurrentJob(created);
      setView("job");
      setJobError(null);
    } catch (e: any) {
      const msg = String(e?.message ?? e);
      // подсказка при отсутствии подписки
      if (msg.includes("Active subscription required")) {
        setErr("Подписка не активна. Продлите подписку на месяц в блоке Billing.");
        // на всякий случай обновим статус
        await refreshSubscription();
      } else {
        setErr(msg);
      }
    } finally {
      setLoading(false);
    }
  }

  // polling job
  useEffect(() => {
    let timer: number | undefined;

    async function tick() {
      if (!currentJob) return;
      try {
        const { job, jobError } = await getJob(currentJob.job_id);
        setCurrentJob(job);
        setJobs((prev) => prev.map((j) => (j.job_id === job.job_id ? job : j)));
        if (jobError) setJobError(jobError);
        if (job.status === "done" || job.status === "failed") return;
      } catch (e: any) {
        setJobError(String(e?.message ?? e));
      }
      timer = window.setTimeout(tick, 1200);
    }

    if (view === "job" && currentJob) {
      timer = window.setTimeout(tick, 400);
    }
    return () => {
      if (timer) window.clearTimeout(timer);
    };
  }, [view, currentJob?.job_id]);

  return (
    <div className="min-h-screen bg-neutral-950">
      <div className="max-w-5xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-2xl font-semibold">Clarus-IoT</div>
            <div className="text-sm text-neutral-400">Интеллектуальный сервис для анализа IoT-траффика</div>
          </div>
          {hasToken ? (
            <div className="flex gap-2">
              <Button
                variant="ghost"
                onClick={() => {
                  clearToken();
                  setJobs([]);
                  setCurrentJob(null);
                  setJobError(null);
                  setSub(null);
                  setSubErr(null);
                  setView("auth");
                }}
              >
                Logout
              </Button>
            </div>
          ) : null}
        </div>

        {err ? (
          <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {err}
          </div>
        ) : null}

        {view === "auth" ? (
          <Card>
            <CardHeader title="Вход" subtitle="Войдите или зарегистрируйтесь" />
            <CardBody>
              <div className="grid gap-3 max-w-md">
                <div>
                  <Label>Email</Label>
                  <Input value={email} onChange={(e) => setEmail(e.target.value)} />
                </div>
                <div>
                  <Label>Password</Label>
                  <Input value={password} onChange={(e) => setPassword(e.target.value)} type="password" />
                </div>
                <div className="flex gap-2 pt-2">
                  <Button disabled={loading} onClick={onLogin}>
                    Login
                  </Button>
                  <Button disabled={loading} variant="ghost" onClick={onRegister}>
                    Register + Login
                  </Button>
                </div>
              </div>
            </CardBody>
          </Card>
        ) : null}

        {view === "dashboard" ? (
          <div className="grid gap-6">
            {/* ✅ Billing card */}
            <Card>
              <CardHeader title="Billing" subtitle="Статус подписки и продление" />
              <CardBody>
                {subErr ? (
                  <div className="mb-3 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                    {subErr}
                  </div>
                ) : null}

                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div className="text-sm text-neutral-200">
                    {subLoading ? (
                      <span className="text-neutral-400">Загружаю статус подписки…</span>
                    ) : sub ? (
                      <>
                        <div className="flex items-center gap-2">
                          <Badge tone={sub.has_active ? "ok" : "bad"}>
                            {sub.has_active ? "active" : "inactive"}
                          </Badge>
                          <span className="text-neutral-300">
                            Осталось дней: <b>{sub.remaining_days}</b>
                          </span>
                        </div>
                        <div className="text-xs text-neutral-400 mt-1">Дата окончания: {formatDate(sub.ends_at)}</div>
                      </>
                    ) : (
                      <span className="text-neutral-400">Статус подписки не получен.</span>
                    )}
                  </div>

                  <div className="flex gap-2">
                    <Button variant="ghost" disabled={subLoading} onClick={refreshSubscription}>
                      Refresh
                    </Button>
                    <Button disabled={subLoading} onClick={onRenew}>
                      Продлить на месяц
                    </Button>
                  </div>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Загрузка CSV" subtitle="Модель проведет анализ IoT-траффика" />
              <CardBody>
                <div className="flex flex-col md:flex-row gap-3 md:items-center">
                  <input
                    type="file"
                    accept=".csv,text/csv"
                    className="block w-full text-sm text-neutral-300 file:mr-3 file:rounded-xl file:border file:border-neutral-800 file:bg-neutral-900 file:px-4 file:py-2 file:text-neutral-100 hover:file:bg-neutral-800"
                    onChange={(e) => {
                      const f = e.target.files?.[0];
                      if (f) onUpload(f);
                      e.currentTarget.value = "";
                    }}
                    disabled={loading}
                  />
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader title="Последние задачи" subtitle="Открой задачу, чтобы увидеть предыдущие результаты анализа" />
              <CardBody>
                {jobs.length === 0 ? (
                  <div className="text-sm text-neutral-400">Пока нет задач. Загрузи первый CSV.</div>
                ) : (
                  <div className="divide-y divide-neutral-800">
                    {jobs.map((j) => (
                      <button
                        key={j.job_id}
                        onClick={() => {
                          setCurrentJob(j);
                          setJobError(null);
                          setView("job");
                        }}
                        className="w-full text-left py-3 flex items-center justify-between hover:bg-neutral-900/40 rounded-xl px-3 -mx-3"
                      >
                        <div className="min-w-0">
                          <div className="text-sm font-medium truncate">
                            {j.original_filename ? `${j.original_filename} · ` : ""}
                            {j.job_id}
                          </div>
                          <div className="text-xs text-neutral-400">
                            {j.created_at ? `${formatShortDate(j.created_at)} · ` : ""}
                            rows: {j.summary.total_rows} · attacks: {j.summary.attack_rows} · top: {j.summary.top_class ?? "—"}
                          </div>
                        </div>
                        <Badge tone={statusTone(j.status)}>{j.status}</Badge>
                      </button>
                    ))}
                  </div>
                )}
              </CardBody>
            </Card>
          </div>
        ) : null}

        {view === "job" && currentJob ? (
          <Card>
            <CardHeader title="Результаты анализа" subtitle={currentJob.job_id}>
              <div className="mt-3 flex items-center gap-2">
                <Badge tone={statusTone(currentJob.status)}>{currentJob.status}</Badge>
                {currentJob.status === "done" ? (
                  <Button
                    variant="ghost"
                    onClick={async () => {
                      setJobError(null);
                      try {
                        await downloadScoredCsv(currentJob.job_id);
                      } catch (e: any) {
                        setJobError(String(e?.message ?? e));
                      }
                    }}
                  >
                    Download scored CSV
                  </Button>
                ) : null}
              </div>
            </CardHeader>

            <CardBody>
              {jobError ? (
                <div className="mb-4 rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {jobError}
                </div>
              ) : null}

              <div className="grid md:grid-cols-3 gap-4">
                <Card className="bg-neutral-950/40">
                  <CardHeader title="Rows" />
                  <CardBody>
                    <div className="text-2xl font-semibold">{currentJob.summary.total_rows}</div>
                  </CardBody>
                </Card>

                <Card className="bg-neutral-950/40">
                  <CardHeader title="Attacks" />
                  <CardBody>
                    <div className="text-2xl font-semibold">{currentJob.summary.attack_rows}</div>
                    <div className="text-sm text-neutral-400">{pct(currentJob.summary.attack_ratio)}</div>
                  </CardBody>
                </Card>

                <Card className="bg-neutral-950/40">
                  <CardHeader title="Top class" />
                  <CardBody>
                    <div className="text-lg font-semibold">{currentJob.summary.top_class ?? "—"}</div>
                    <div className="text-sm text-neutral-400">
                      {currentJob.summary.top_class_share == null ? "—" : pct(currentJob.summary.top_class_share)}
                    </div>
                  </CardBody>
                </Card>
              </div>

              <div className="pt-4 flex gap-2">
                <Button
                  variant="ghost"
                  onClick={() => {
                    setView("dashboard");
                    setCurrentJob(null);
                    setJobError(null);
                  }}
                >
                  Back
                </Button>
              </div>
            </CardBody>
          </Card>
        ) : null}
      </div>
    </div>
  );
}
