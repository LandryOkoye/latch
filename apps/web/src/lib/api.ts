export type LoopStatus =
  | "open"
  | "awaiting_reply"
  | "closed_verified"
  | "closed_claimed"
  | "escalated_to_human"
  | "abandoned";

export type LoopEventType =
  | "created"
  | "touched"
  | "reply_received"
  | "deferred"
  | "transferred"
  | "disputed"
  | "escalated"
  | "closed_verified"
  | "closed_claimed"
  | "abandoned";

export type Stakes = "low" | "medium" | "high";

export interface LoopEvent {
  id: string;
  loop_id: string;
  event_type: LoopEventType;
  occurred_at: string;
  channel: string | null;
  detail: string;
  evidence_span: string | null;
  message_id: string | null;
  reply_text: string | null;
}

export interface Loop {
  id: string;
  parent_id: string | null;
  promise: string;
  source_quote: string;
  source_meeting_id: string | null;
  owner_name: string;
  owner_email: string;
  counterparty_org: string;
  due_at: string;
  window_source: "stated" | "inferred";
  closure_criterion: string;
  stakes: Stakes;
  status: LoopStatus;
  touch_count: number;
  deferral_count: number;
  channels_tried: string[];
  created_at: string;
  events: LoopEvent[];
}

export type PriorityBreakdown = Record<
  "days_past_window" | "stakes" | "deferral_count" | "touch_count" | "counterparty_unreliability",
  number
>;

export interface WorklistItem {
  loop: Loop;
  priority_total: number;
  priority_breakdown: PriorityBreakdown;
}

export interface LoopDetail extends WorklistItem {
  ancestors: Loop[];
  children: Loop[];
  draft: string;
}

export interface ReliabilityRow {
  counterparty_org: string;
  loops_opened: number;
  closed_on_time: number;
  median_touches_to_closure: number;
  deferral_rate: number;
  escalation_rate: number;
  unreliability_score: number;
}

export interface PursueResult {
  result: string;
  loop: Loop;
}

export interface IngestResult {
  meeting_id: string;
  title: string;
  loops: Loop[];
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === "string" ? body.detail : `Request failed (${response.status})`;
    throw new ApiError(detail, response.status);
  }
  return response.json() as Promise<T>;
}

export const api = {
  worklist: () => request<WorklistItem[]>("/worklist"),
  loops: () => request<Loop[]>("/loops"),
  loop: (id: string) => request<LoopDetail>(`/loops/${id}`),
  pursue: (id: string) => request<PursueResult>(`/loops/${id}/pursue`, { method: "POST" }),
  reliability: () => request<ReliabilityRow[]>("/reliability"),
  ingest: (text: string) => request<IngestResult>("/meetings", { method: "POST", body: JSON.stringify({ text }) }),
};
