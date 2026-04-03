import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Input } from "@/components/ui/input";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Settings as SettingsIcon, Bell, Globe, Shield, Palette, Trash2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { usePageMeta } from "@/hooks/usePageMeta";
import { deleteAccount } from "@/hooks/useAuth";

interface UserSettings {
  notifications: boolean;
  autoplay: boolean;
  language: string;
  theme: string;
  dataSharing: boolean;
}

const defaultSettings: UserSettings = {
  notifications: true,
  autoplay: false,
  language: "en",
  theme: "system",
  dataSharing: true,
};

export default function Settings() {
  usePageMeta({
    title: "Settings",
    description: "Manage your CineGraph account settings, preferences, and notifications.",
  });

  const { toast } = useToast();
  const [notifications, setNotifications] = useState(defaultSettings.notifications);
  const [autoplay, setAutoplay] = useState(defaultSettings.autoplay);
  const [language, setLanguage] = useState(defaultSettings.language);
  const [theme, setTheme] = useState(defaultSettings.theme);
  const [dataSharing, setDataSharing] = useState(defaultSettings.dataSharing);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  useEffect(() => {
    const savedSettings = localStorage.getItem("userSettings");
    if (savedSettings) {
      try {
        const parsed: UserSettings = JSON.parse(savedSettings);
        setNotifications(parsed.notifications ?? defaultSettings.notifications);
        setAutoplay(parsed.autoplay ?? defaultSettings.autoplay);
        setLanguage(parsed.language ?? defaultSettings.language);
        setTheme(parsed.theme ?? defaultSettings.theme);
        setDataSharing(parsed.dataSharing ?? defaultSettings.dataSharing);
      } catch (error) {
        console.error("Failed to parse saved settings:", error);
      }
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    
    root.classList.remove("dark", "system");
    
    if (theme === "dark") {
      root.classList.add("dark");
    } else if (theme === "system") {
      root.classList.add("system");
    }
  }, [theme]);

  useEffect(() => {
    const settings: UserSettings = {
      notifications,
      autoplay,
      language,
      theme,
      dataSharing,
    };

    localStorage.setItem("userSettings", JSON.stringify(settings));
  }, [notifications, autoplay, language, theme, dataSharing]);

  const handleSaveSettings = () => {
    const settings: UserSettings = {
      notifications,
      autoplay,
      language,
      theme,
      dataSharing,
    };

    localStorage.setItem("userSettings", JSON.stringify(settings));

    toast({
      title: "Settings saved",
      description: "Your preferences have been saved successfully.",
    });
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== "DELETE") return;

    setIsDeleting(true);
    const result = await deleteAccount(deleteConfirmation);
    setIsDeleting(false);

    if (result.success) {
      setDeleteDialogOpen(false);
      setDeleteConfirmation("");
      toast({
        title: "Account deleted",
        description: "Your account and all associated data have been permanently deleted.",
      });
      window.history.pushState({}, "", "/");
      window.dispatchEvent(new PopStateEvent("popstate"));
    } else {
      toast({
        title: "Error",
        description: result.error || "Failed to delete account. Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center space-x-3 mb-8">
        <SettingsIcon className="h-8 w-8 text-primary" />
        <h1 className="text-3xl font-bold text-foreground" data-testid="title-settings">Settings</h1>
      </div>

      <div className="space-y-6">
        <Card data-testid="card-notifications">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Bell className="h-5 w-5" />
              <span>Notifications</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="email-notifications" data-testid="label-email-notifications">Email Notifications</Label>
                <p className="text-sm text-muted-foreground">
                  Receive email updates about new movies and recommendations
                </p>
              </div>
              <Switch
                id="email-notifications"
                checked={notifications}
                onCheckedChange={setNotifications}
                data-testid="switch-email-notifications"
              />
            </div>
            
            <Separator />
            
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="autoplay" data-testid="label-autoplay">Autoplay Trailers</Label>
                <p className="text-sm text-muted-foreground">
                  Automatically play movie trailers when browsing
                </p>
              </div>
              <Switch
                id="autoplay"
                checked={autoplay}
                onCheckedChange={setAutoplay}
                data-testid="switch-autoplay"
              />
            </div>
          </CardContent>
        </Card>

        <Card data-testid="card-display">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Palette className="h-5 w-5" />
              <span>Display & Language</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="theme" data-testid="label-theme">Theme</Label>
              <Select value={theme} onValueChange={setTheme}>
                <SelectTrigger id="theme" data-testid="select-theme">
                  <SelectValue placeholder="Select theme" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="dark">Dark</SelectItem>
                  <SelectItem value="system">System</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="language" data-testid="label-language">Language</Label>
              <Select value={language} onValueChange={setLanguage}>
                <SelectTrigger id="language" data-testid="select-language">
                  <SelectValue placeholder="Select language" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="es">Español</SelectItem>
                  <SelectItem value="fr">Français</SelectItem>
                  <SelectItem value="de">Deutsch</SelectItem>
                  <SelectItem value="ja">日本語</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card data-testid="card-privacy">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Shield className="h-5 w-5" />
              <span>Privacy & Data</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="data-sharing" data-testid="label-data-sharing">Data Sharing</Label>
                <p className="text-sm text-muted-foreground">
                  Share viewing data to improve recommendations
                </p>
              </div>
              <Switch
                id="data-sharing"
                checked={dataSharing}
                onCheckedChange={setDataSharing}
                data-testid="switch-data-sharing"
              />
            </div>
            
            <Separator />
            
            <div className="space-y-2">
              <Button variant="outline" className="w-full" data-testid="button-download-data">
                <Globe className="h-4 w-4 mr-2" />
                Download My Data
              </Button>
              <AlertDialog open={deleteDialogOpen} onOpenChange={(open) => {
                setDeleteDialogOpen(open);
                if (!open) setDeleteConfirmation("");
              }}>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" className="w-full" data-testid="button-delete-account">
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete Account
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle data-testid="title-delete-dialog">Delete Account</AlertDialogTitle>
                    <AlertDialogDescription className="space-y-3" asChild>
                      <div>
                        <p data-testid="text-delete-warning">
                          This action is <strong>permanent and cannot be undone</strong>. All of your data will be permanently deleted, including:
                        </p>
                        <ul className="list-disc list-inside text-sm space-y-1 mt-2">
                          <li>Your profile and preferences</li>
                          <li>Watchlist and favorites</li>
                          <li>Viewing history</li>
                          <li>Reviews and ratings</li>
                          <li>Lists and follows</li>
                          <li>Notifications</li>
                        </ul>
                        <p className="mt-3">
                          Type <strong>DELETE</strong> below to confirm:
                        </p>
                        <Input
                          value={deleteConfirmation}
                          onChange={(e) => setDeleteConfirmation(e.target.value)}
                          placeholder="Type DELETE to confirm"
                          className="mt-2"
                          data-testid="input-delete-confirmation"
                        />
                      </div>
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel data-testid="button-cancel-delete">Cancel</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={(e) => {
                        e.preventDefault();
                        handleDeleteAccount();
                      }}
                      disabled={deleteConfirmation !== "DELETE" || isDeleting}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      data-testid="button-confirm-delete"
                    >
                      {isDeleting ? "Deleting..." : "Delete Account"}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-end">
          <Button className="min-w-32" data-testid="button-save-settings" onClick={handleSaveSettings}>
            Save Changes
          </Button>
        </div>
      </div>
    </div>
  );
}