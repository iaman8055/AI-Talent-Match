"use client";

import { Bell, CheckCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
  useUnreadCount,
} from "@/hooks/use-notifications";
import type { NotificationResponse } from "@/lib/api-client/notifications";

function timeAgo(isoDate: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoDate).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function NotificationRow({
  notification,
  onRead,
}: {
  notification: NotificationResponse;
  onRead: (id: string) => void;
}) {
  const unread = notification.read_at === null;

  return (
    <DropdownMenuItem
      render={notification.link ? <Link href={notification.link} /> : undefined}
      onClick={() => unread && onRead(notification.id)}
      className="flex flex-col items-start gap-0.5 whitespace-normal"
    >
      <div className="flex w-full items-center gap-2">
        {unread && (
          <span className="size-1.5 shrink-0 rounded-full bg-primary" />
        )}
        <span className={unread ? "font-medium" : "text-muted-foreground"}>
          {notification.title}
        </span>
      </div>
      <p className="text-xs text-muted-foreground">{notification.body}</p>
      <p className="text-xs text-muted-foreground">
        {timeAgo(notification.created_at)}
      </p>
    </DropdownMenuItem>
  );
}

export function NotificationBell() {
  const { data: notifications, isLoading } = useNotifications();
  const { data: unreadData } = useUnreadCount();
  const markRead = useMarkNotificationRead();
  const markAllRead = useMarkAllNotificationsRead();

  const unreadCount = unreadData?.count ?? 0;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon" className="relative">
            <Bell />
            {unreadCount > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-1 -right-1 h-4 min-w-4 justify-center rounded-full px-1 text-[10px]"
              >
                {unreadCount > 9 ? "9+" : unreadCount}
              </Badge>
            )}
          </Button>
        }
      />
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex items-center justify-between px-2 py-1.5">
          <span className="text-sm font-medium">Notifications</span>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => markAllRead.mutate()}
            >
              <CheckCheck className="size-3.5" />
              Mark all read
            </Button>
          )}
        </div>
        <DropdownMenuSeparator />
        {isLoading && (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            Loading…
          </div>
        )}
        {!isLoading && (notifications ?? []).length === 0 && (
          <div className="px-2 py-4 text-center text-sm text-muted-foreground">
            No notifications yet.
          </div>
        )}
        {(notifications ?? []).map((notification) => (
          <NotificationRow
            key={notification.id}
            notification={notification}
            onRead={(id) => markRead.mutate(id)}
          />
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
