"use client";

import {
  Bot,
  Briefcase,
  Building2,
  ChevronsUpDown,
  ClipboardList,
  LogOut,
  Mail,
  Sparkles,
  User,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { ThemeToggle } from "@/components/theme-toggle";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import { useAuth } from "@/hooks/use-auth";

const CANDIDATE_ITEMS = [
  { href: "/profile", label: "Profile", icon: User },
  { href: "/jobs", label: "Recommended jobs", icon: Sparkles },
  { href: "/applications", label: "My applications", icon: ClipboardList },
  { href: "/agent", label: "Auto-Apply", icon: Bot },
];

const RECRUITER_ITEMS = [
  { href: "/recruiter/jobs", label: "Jobs", icon: Briefcase },
  { href: "/recruiter/outreach", label: "Outreach", icon: Mail },
  { href: "/recruiter/company", label: "Company", icon: Building2 },
];

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const chars =
    parts.length > 1
      ? [parts[0][0], parts[parts.length - 1][0]]
      : [parts[0]?.[0]];
  return chars.join("").toUpperCase() || "?";
}

export function AppSidebar() {
  const { user, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  const items = user.role === "candidate" ? CANDIDATE_ITEMS : RECRUITER_ITEMS;

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" render={<Link href="/" />}>
              <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Sparkles className="size-4" />
              </div>
              <div className="flex flex-col leading-tight">
                <span className="font-heading text-sm font-semibold">
                  AI Talent Match
                </span>
                <span className="text-xs text-muted-foreground capitalize">
                  {user.role} workspace
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {items.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <SidebarMenuItem key={item.href}>
                    <SidebarMenuButton
                      isActive={isActive}
                      tooltip={item.label}
                      render={<Link href={item.href} />}
                      className={
                        isActive
                          ? "bg-primary/10 text-primary hover:bg-primary/15 hover:text-primary"
                          : undefined
                      }
                    >
                      <item.icon />
                      <span>{item.label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <SidebarMenuButton size="lg">
                    <Avatar size="sm" className="rounded-lg">
                      <AvatarFallback className="rounded-lg bg-primary/10 text-primary">
                        {initials(user.full_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col overflow-hidden leading-tight">
                      <span className="truncate text-sm font-medium">
                        {user.full_name}
                      </span>
                      <span className="truncate text-xs text-muted-foreground">
                        {user.email}
                      </span>
                    </div>
                    <ChevronsUpDown className="ml-auto size-4 text-muted-foreground" />
                  </SidebarMenuButton>
                }
              />
              <DropdownMenuContent align="end" className="w-56">
                <ThemeToggle />
                <DropdownMenuSeparator />
                <DropdownMenuItem variant="destructive" onClick={logout}>
                  <LogOut />
                  Log out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
