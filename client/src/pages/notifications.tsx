import { useState, useEffect } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { Bell, Trash2, CheckCheck, MessageSquare, Users, List, Heart } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useAuth } from "@/hooks/useAuth";
import { useToast } from "@/hooks/use-toast";
import { apiRequest, queryClient } from "@/lib/queryClient";
import type { Notification } from "@shared/schema";
import { usePageMeta } from "@/hooks/usePageMeta";
import { useTranslation } from "react-i18next";

export default function NotificationsPage() {
  const { t } = useTranslation();

  usePageMeta({
    title: t("notifications.title"),
    description: "Stay updated with activity from the CineGraph community.",
  });

  const [, setLocation] = useLocation();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const { toast } = useToast();
  const [filterType, setFilterType] = useState<string>('all');

  const { data: notifications = [], isLoading } = useQuery<Notification[]>({
    queryKey: ['/api/community/notifications', filterType],
    queryFn: async () => {
      const params = new URLSearchParams({ limit: '50' });
      if (filterType === 'unread') {
        params.set('unreadOnly', 'true');
      }

      const response = await fetch(`/api/community/notifications?${params}`, {
        credentials: "include",
      });
      if (!response.ok) throw new Error('Failed to fetch notifications');
      return response.json();
    },
    enabled: isAuthenticated,
  });

  const markAsReadMutation = useMutation({
    mutationFn: async (notificationId: number) => {
      return apiRequest('PUT', `/api/community/notifications/${notificationId}/read`, {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications'] });
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications/unread/count'] });
    },
  });

  const markAllAsReadMutation = useMutation({
    mutationFn: async () => {
      return apiRequest('PUT', '/api/community/notifications/read-all', {});
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications'] });
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications/unread/count'] });
      toast({
        title: t("notifications.allMarkedRead"),
      });
    },
  });

  const deleteNotificationMutation = useMutation({
    mutationFn: async (notificationId: number) => {
      return apiRequest('DELETE', `/api/community/notifications/${notificationId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications'] });
      queryClient.invalidateQueries({ queryKey: ['/api/community/notifications/unread/count'] });
      toast({
        title: t("notifications.deleted"),
      });
    },
  });

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.isRead) {
      markAsReadMutation.mutate(notification.id);
    }

    if (notification.relatedTmdbId && notification.relatedMediaType) {
      setLocation(`/${notification.relatedMediaType}/${notification.relatedTmdbId}`);
    } else if (notification.type === 'follow' && notification.relatedUserId) {
      setLocation(`/profile/${notification.relatedUserId}`);
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'follow':
        return <Users className="h-4 w-4" />;
      case 'comment':
        return <MessageSquare className="h-4 w-4" />;
      case 'like':
        return <Heart className="h-4 w-4" />;
      case 'list_follow':
        return <List className="h-4 w-4" />;
      case 'recommendation':
        return <Bell className="h-4 w-4" />;
      default:
        return <Bell className="h-4 w-4" />;
    }
  };

  const filteredNotifications = filterType === 'all' || filterType === 'unread'
    ? notifications
    : notifications.filter(n => n.type === filterType);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      setLocation('/login');
    }
  }, [authLoading, isAuthenticated, setLocation]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <p className="text-muted-foreground">{t("common.loading")}</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-background py-8">
      <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold" data-testid="text-notifications-heading">{t("notifications.title")}</h1>
            <p className="text-muted-foreground mt-1">{t("notifications.subtitle")}</p>
          </div>
          {notifications.some(n => !n.isRead) && (
            <Button
              onClick={() => markAllAsReadMutation.mutate()}
              disabled={markAllAsReadMutation.isPending}
              data-testid="button-mark-all-read"
            >
              <CheckCheck className="h-4 w-4 mr-2" />
              {t("notifications.markAllRead")}
            </Button>
          )}
        </div>

        <Tabs value={filterType} onValueChange={setFilterType} className="mb-6">
          <TabsList>
            <TabsTrigger value="all" data-testid="tab-all">{t("notifications.all")}</TabsTrigger>
            <TabsTrigger value="unread" data-testid="tab-unread">{t("notifications.unread")}</TabsTrigger>
            <TabsTrigger value="follow" data-testid="tab-follow">{t("notifications.follows")}</TabsTrigger>
            <TabsTrigger value="comment" data-testid="tab-comment">{t("notifications.comments")}</TabsTrigger>
            <TabsTrigger value="like" data-testid="tab-like">{t("notifications.likes")}</TabsTrigger>
            <TabsTrigger value="list_follow" data-testid="tab-list-follow">{t("notifications.listFollows")}</TabsTrigger>
          </TabsList>
        </Tabs>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <Card key={i} className="p-4">
                <div className="flex items-start space-x-4">
                  <Skeleton className="h-10 w-10 rounded-full" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-3 w-1/4" />
                  </div>
                </div>
              </Card>
            ))}
          </div>
        ) : filteredNotifications.length === 0 ? (
          <Card className="p-12">
            <div className="text-center" data-testid="text-no-notifications-found">
              <Bell className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">{t("notifications.noNotifications")}</h3>
              <p className="text-muted-foreground">
                {filterType === 'all' 
                  ? t("notifications.noNotificationsYet")
                  : t("notifications.noTypeNotifications", { type: filterType })}
              </p>
            </div>
          </Card>
        ) : (
          <div className="space-y-2">
            {filteredNotifications.map((notification) => (
              <Card
                key={notification.id}
                className={`p-4 cursor-pointer hover:bg-accent transition-colors ${
                  !notification.isRead ? 'border-primary/50 bg-accent/50' : ''
                }`}
                onClick={() => handleNotificationClick(notification)}
                data-testid={`notification-card-${notification.id}`}
              >
                <div className="flex items-start space-x-4">
                  <div className="h-10 w-10 rounded-full bg-accent flex items-center justify-center">
                    {getNotificationIcon(notification.type)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm leading-relaxed" data-testid={`text-notification-message-${notification.id}`}>
                      {notification.message}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1" data-testid={`text-notification-time-${notification.id}`}>
                      {notification.createdAt && formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
                    </p>
                  </div>

                  <div className="flex items-center space-x-2">
                    {!notification.isRead && (
                      <div className="h-2 w-2 rounded-full bg-primary" data-testid={`indicator-unread-${notification.id}`} />
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteNotificationMutation.mutate(notification.id);
                      }}
                      data-testid={`button-delete-${notification.id}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
