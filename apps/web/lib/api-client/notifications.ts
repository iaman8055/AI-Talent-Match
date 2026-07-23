import { apiFetch } from "./client";

// Hand-written to mirror apps/api/src/api/v1/notifications/schemas.py — same rationale as
// lib/api-client/agent.ts (no server was started this session to regenerate schema.d.ts).

export type NotificationType =
  | "candidate_invited"
  | "application_status_changed"
  | "auto_applied"
  | "new_outreach_draft";

export interface NotificationResponse {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  link: string | null;
  read_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

export async function listNotifications(): Promise<NotificationResponse[]> {
  return apiFetch<NotificationResponse[]>("/notifications");
}

export async function getUnreadCount(): Promise<UnreadCountResponse> {
  return apiFetch<UnreadCountResponse>("/notifications/unread-count");
}

export async function markNotificationRead(
  notificationId: string,
): Promise<NotificationResponse> {
  return apiFetch<NotificationResponse>(
    `/notifications/${notificationId}/read`,
    { method: "POST" },
  );
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiFetch<void>("/notifications/read-all", { method: "POST" });
}
