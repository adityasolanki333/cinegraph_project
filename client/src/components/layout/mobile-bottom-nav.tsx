import { Link, useLocation } from "wouter";
import { Home, Film, Tv, Sparkles, Users, Heart } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";

export default function MobileBottomNav() {
  const [location] = useLocation();
  const { t } = useTranslation();

  const navItems = [
    { href: "/", label: t("nav.home"), icon: Home, exact: true },
    { href: "/movies", label: t("nav.movies"), icon: Film },
    { href: "/tv-shows", label: t("nav.tv"), icon: Tv },
    { href: "/recommendations", label: t("nav.ai"), icon: Sparkles, isSpecial: true },
    { href: "/community", label: t("nav.community"), icon: Users },
  ];

  return (
    <nav
      aria-label="Mobile navigation"
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-background/95 backdrop-blur-md border-t border-border safe-area-bottom"
      data-testid="mobile-bottom-nav"
    >
      <div className="flex items-stretch h-14">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = item.exact
            ? location === item.href
            : location === item.href || location.startsWith(item.href + "/");

          return (
            <Link key={item.href} href={item.href} className="flex-1">
              <button
                aria-label={item.label}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "w-full h-full flex flex-col items-center justify-center gap-0.5 transition-colors touch-manipulation min-h-[44px]",
                  isActive
                    ? "text-primary"
                    : "text-muted-foreground active:text-foreground",
                  item.isSpecial && !isActive && "text-accent"
                )}
                data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
              >
                <div className={cn(
                  "flex items-center justify-center w-8 h-5 rounded-full transition-all",
                  isActive && "bg-primary/10"
                )}>
                  <Icon className="h-4.5 w-4.5" style={{ height: "18px", width: "18px" }} />
                </div>
                <span className={cn(
                  "text-[10px] leading-tight font-medium",
                  isActive ? "text-primary" : "text-muted-foreground"
                )}>
                  {item.label}
                </span>
              </button>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
