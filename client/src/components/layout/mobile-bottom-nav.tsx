import { Link, useLocation } from "wouter";
import { Home, Film, Tv, Sparkles, Users, Heart } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Home", icon: Home, exact: true },
  { href: "/movies", label: "Movies", icon: Film },
  { href: "/tv-shows", label: "TV", icon: Tv },
  { href: "/recommendations", label: "AI", icon: Sparkles, isSpecial: true },
  { href: "/community", label: "Community", icon: Users },
];

export default function MobileBottomNav() {
  const [location] = useLocation();

  return (
    <nav
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
                className={cn(
                  "w-full h-full flex flex-col items-center justify-center gap-0.5 transition-colors touch-manipulation",
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
