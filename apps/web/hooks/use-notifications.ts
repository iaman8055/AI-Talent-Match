"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as notificationsApi from "@/lib/api-client/notifications";
import { useAuth } from "@/hooks/use-auth";

const NOTIFICATIONS_KEY = ["notifications"];
const UNREAD_COUNT_KEY = ["notifications", "unread-count"];
const POLL_INTERVAL_MS = 30_000;

export function useNotifications() {
  const { user } = useAuth();
  return useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: notificationsApi.listNotifications,
    enabled: !!user,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useUnreadCount() {
  const { user } = useAuth();
  return useQuery({
    queryKey: UNREAD_COUNT_KEY,
    queryFn: notificationsApi.getUnreadCount,
    enabled: !!user,
    refetchInterval: POLL_INTERVAL_MS,
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (notificationId: string) =>
      notificationsApi.markNotificationRead(notificationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      void queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: notificationsApi.markAllNotificationsRead,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      void queryClient.invalidateQueries({ queryKey: UNREAD_COUNT_KEY });
    },
  });
}
