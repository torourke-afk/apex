import {
  LayoutDashboard, Wallet, BarChart3, Palette, Users,
  Radar, Boxes, Filter, RefreshCw, ClipboardCheck,
  SlidersHorizontal, Network, Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface NavEntry {
  code: string;       // 2-letter rail tile label
  name: string;       // rail label
  view: string;       // router id
  crumb: string;      // breadcrumb prefix
  title: string;      // screen title
  icon: LucideIcon;   // lucide icon component
  badge?: number;     // optional count badge (e.g. Operations pending)
}

export const NAV: NavEntry[] = [
  { code: "SC", name: "Scorecard",  view: "scorecard",  crumb: "COMMAND / SCORECARD",       title: "Executive Scorecard",       icon: LayoutDashboard },
  { code: "SB", name: "Spend",      view: "spend",      crumb: "PLAN / SPEND & BUDGET",     title: "Spend & Budget",            icon: Wallet },
  { code: "MP", name: "Media",      view: "media",      crumb: "PERFORMANCE / MEDIA",       title: "Media Performance",         icon: BarChart3 },
  { code: "CR", name: "Creative",   view: "creative",   crumb: "PERFORMANCE / CREATIVE",    title: "Creative & Messaging",      icon: Palette },
  { code: "AG", name: "Audience",   view: "audience",   crumb: "PERFORMANCE / AUDIENCE",    title: "Audience & Geo",            icon: Users },
  { code: "BA", name: "Awareness",  view: "brand",      crumb: "AWARENESS / SHARE OF SEARCH", title: "Brand Awareness Tracker", icon: Radar },
  { code: "PC", name: "Product",    view: "product",    crumb: "PERFORMANCE / PRODUCT",     title: "Product & Conversion",      icon: Boxes },
  { code: "FN", name: "Funnel",     view: "funnel",     crumb: "ANALYZE / ACQUISITION",     title: "Acquisition Funnel",        icon: Filter },
  { code: "RL", name: "Retention",  view: "retention",  crumb: "ANALYZE / RETENTION",       title: "Retention & LTV",           icon: RefreshCw },
  { code: "OP", name: "Operations", view: "operations", crumb: "CONTROL / OPERATIONS",      title: "Operations Command",        icon: ClipboardCheck, badge: 3 },
  { code: "SM", name: "Simulator",  view: "simulator",  crumb: "MODEL / SIMULATOR",         title: "Full-Funnel Simulator",     icon: SlidersHorizontal },
  { code: "MA", name: "Modeling",   view: "modeling",   crumb: "MODEL / ATTRIBUTION",       title: "Modeling & Attribution",     icon: Network },
  { code: "ST", name: "Settings",   view: "settings",   crumb: "SYSTEM / SETTINGS",         title: "Settings & Configuration",  icon: Settings },
];

export const DEFAULT_VIEW = "scorecard";
