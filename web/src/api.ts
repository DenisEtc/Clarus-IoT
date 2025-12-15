export type PredictionSummary = {
  total_rows: number;
  attack_rows: number;
  attack_ratio: number;
  top_class: string | null;
  top_class_share: number | null;
};

export type JobResponse = {
  job_id: string;
  status: string;
  summary: PredictionSummary;
  // optional fields available in /predictions/jobs (history)
  created_at?: string | null;
  original_filename?: string | null;
};

export type SubscriptionStatus = {
  has_active: boolean;
  ends_at: string | null; // ISO string
  remaining_days: number;
};

export type RenewOut = {
  payment_id: string;
  subscription_id: string;
  ends_at: string; // ISO string
};

type LoginResponse = { access_token: string; token_type: string };

const TOKEN_KEY = "clarus_token";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(t: string) {
  localStorage.setItem(TOKEN_KEY, t);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function authHeaders(): HeadersInit {
  const t = getToken();
  return t ? { Authorization: `Bearer ${t}` } : {};
}

export async function register(email: string, password: string): Promise<void> {
  const res = await fetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json", accept: "application/json" },
    body: JSON.stringify({ email, password })
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Register failed (${res.status})`);
}

export async function login(email: string, password: string): Promise<void> {
  // FastAPI OAuth2PasswordRequestForm ожидает username/password в form-urlencoded
  const form = new URLSearchParams();
  form.set("username", email);
  form.set("password", password);

  const res = await fetch("/auth/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      accept: "application/json"
    },
    body: form.toString()
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Login failed (${res.status})`);

  const data: LoginResponse = JSON.parse(txt);
  setToken(data.access_token);
}

export async function getSubscriptionStatus(): Promise<SubscriptionStatus> {
  const res = await fetch("/billing/subscription", {
    method: "GET",
    headers: { ...authHeaders(), accept: "application/json" }
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Subscription status failed (${res.status})`);
  return JSON.parse(txt) as SubscriptionStatus;
}

export async function renewSubscription(planCode = "MONTHLY_1M"): Promise<RenewOut> {
  const res = await fetch("/billing/renew", {
    method: "POST",
    headers: { ...authHeaders(), accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify({ plan_code: planCode })
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Renew failed (${res.status})`);
  return JSON.parse(txt) as RenewOut;
}

export async function uploadCsv(file: File): Promise<JobResponse> {
  const form = new FormData();
  form.append("csv_file", file);

  const res = await fetch("/predictions/upload", {
    method: "POST",
    headers: { ...authHeaders(), accept: "application/json" },
    body: form
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Upload failed (${res.status})`);
  return JSON.parse(txt) as JobResponse;
}

export async function getJob(jobId: string): Promise<{ job: JobResponse; jobError?: string }> {
  const res = await fetch(`/predictions/${jobId}`, {
    method: "GET",
    headers: { ...authHeaders(), accept: "application/json" }
  });

  const jobError = res.headers.get("X-Job-Error") ?? undefined;

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `Get job failed (${res.status})`);
  return { job: JSON.parse(txt) as JobResponse, jobError };
}

export async function listJobs(limit = 50, offset = 0): Promise<JobResponse[]> {
  const res = await fetch(`/predictions/jobs?limit=${encodeURIComponent(limit)}&offset=${encodeURIComponent(offset)}`, {
    method: "GET",
    headers: { ...authHeaders(), accept: "application/json" }
  });

  const txt = await res.text();
  if (!res.ok) throw new Error(txt || `List jobs failed (${res.status})`);
  return JSON.parse(txt) as JobResponse[];
}

function parseFilenameFromContentDisposition(cd: string | null): string | null {
  if (!cd) return null;
  // Handles: attachment; filename="..." and RFC5987: filename*=UTF-8''...
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(cd);
  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1]);
    } catch {
      return utf8[1];
    }
  }
  const simple = /filename="?([^";]+)"?/i.exec(cd);
  return simple?.[1] ?? null;
}

export async function downloadScoredCsv(jobId: string): Promise<void> {
  const res = await fetch(`/predictions/${jobId}/download`, {
    method: "GET",
    headers: { ...authHeaders() }
  });

  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(txt || `Download failed (${res.status})`);
  }

  const blob = await res.blob();
  const cd = res.headers.get("Content-Disposition");
  const filename = parseFilenameFromContentDisposition(cd) ?? `scored_${jobId}.csv`;

  const url = URL.createObjectURL(blob);
  try {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
  } finally {
    URL.revokeObjectURL(url);
  }
}

export function downloadUrl(jobId: string) {
  return `/predictions/${jobId}/download`;
}
