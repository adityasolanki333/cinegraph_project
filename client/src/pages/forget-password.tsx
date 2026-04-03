import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import { Loader2, Mail, Lock, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useLocation, Link } from "wouter";
import { apiRequest } from "@/lib/queryClient";
import { usePageMeta } from "@/hooks/usePageMeta";
import { useTranslation } from "react-i18next";

export default function ForgetPassword() {
    const { t } = useTranslation();

    usePageMeta({
      title: t("forgotPassword.title"),
      description: "Reset your CineGraph account password.",
    });

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [isSuccess, setIsSuccess] = useState(false);
    const [resetToken, setResetToken] = useState<string | null>(null);
    const { toast } = useToast();
    const [, setLocation] = useLocation();

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');
        if (token) {
            setResetToken(token);
        }
    }, []);

    const handleRequestReset = async (e: React.FormEvent) => {
        e.preventDefault();
        setIsLoading(true);

        try {
            const response = await apiRequest("POST", "/api/auth/forget-password", { email });
            const data = await response.json();

            if (response.ok) {
                setIsSuccess(true);
                if (data.demo_reset_token) {
                    toast({
                        title: "Demo Mode",
                        description: "Redirecting to reset page with demo token...",
                        duration: 3000,
                    });
                    setTimeout(() => {
                        setLocation(data.demo_reset_link);
                        setResetToken(data.demo_reset_token);
                        setIsSuccess(false);
                    }, 2000);
                } else {
                    toast({
                        title: t("forgotPassword.checkEmail"),
                        description: t("forgotPassword.checkEmailDesc"),
                    });
                }
            } else {
                throw new Error(data.error || "Failed to send reset link");
            }
        } catch (error) {
            toast({
                title: t("common.error"),
                description: error instanceof Error ? error.message : "Something went wrong",
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    const handleResetPassword = async (e: React.FormEvent) => {
        e.preventDefault();

        if (password !== confirmPassword) {
            toast({
                title: t("common.error"),
                description: "Passwords do not match",
                variant: "destructive",
            });
            return;
        }

        setIsLoading(true);

        try {
            const response = await apiRequest("POST", "/api/auth/reset-password", {
                token: resetToken,
                password
            });
            const data = await response.json();

            if (response.ok) {
                toast({
                    title: "Success",
                    description: "Your password has been reset. Please login.",
                });
                setTimeout(() => {
                    setLocation("/login");
                }, 1500);
            } else {
                throw new Error(data.error || "Failed to reset password");
            }
        } catch (error) {
            toast({
                title: t("common.error"),
                description: error instanceof Error ? error.message : "Something went wrong",
                variant: "destructive",
            });
        } finally {
            setIsLoading(false);
        }
    };

    if (resetToken) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-background px-4">
                <Card className="w-full max-w-md">
                    <CardHeader className="text-center">
                        <CardTitle className="text-2xl font-bold">{t("forgotPassword.resetTitle")}</CardTitle>
                        <CardDescription>
                            {t("forgotPassword.resetDesc")}
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <form onSubmit={handleResetPassword} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="password">{t("forgotPassword.newPassword")}</Label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="password"
                                        type="password"
                                        placeholder={t("forgotPassword.newPasswordPlaceholder")}
                                        className="pl-10"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        required
                                        minLength={6}
                                    />
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">{t("forgotPassword.confirmPassword")}</Label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="confirmPassword"
                                        type="password"
                                        placeholder={t("forgotPassword.confirmPasswordPlaceholder")}
                                        className="pl-10"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        required
                                        minLength={6}
                                    />
                                </div>
                            </div>
                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        {t("forgotPassword.resetting")}
                                    </>
                                ) : (
                                    t("forgotPassword.resetPassword")
                                )}
                            </Button>
                        </form>
                    </CardContent>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-background px-4">
            <Card className="w-full max-w-md">
                <CardHeader className="text-center">
                    <CardTitle className="text-2xl font-bold">{t("forgotPassword.forgotTitle")}</CardTitle>
                    <CardDescription>
                        {t("forgotPassword.forgotDesc")}
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {isSuccess ? (
                        <div className="text-center py-6 space-y-4">
                            <div className="flex justify-center">
                                <div className="bg-green-100 dark:bg-green-900/30 p-3 rounded-full">
                                    <CheckCircle2 className="h-8 w-8 text-green-600 dark:text-green-400" />
                                </div>
                            </div>
                            <h3 className="text-lg font-medium">{t("forgotPassword.checkEmail")}</h3>
                            <p className="text-muted-foreground text-sm max-w-xs mx-auto">
                                {t("forgotPassword.checkEmailDesc")}
                            </p>
                            <Button variant="outline" onClick={() => setLocation("/login")}>
                                {t("forgotPassword.backToLogin")}
                            </Button>
                        </div>
                    ) : (
                        <form onSubmit={handleRequestReset} className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="email">{t("forgotPassword.email")}</Label>
                                <div className="relative">
                                    <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                                    <Input
                                        id="email"
                                        type="email"
                                        placeholder={t("forgotPassword.emailPlaceholder")}
                                        className="pl-10"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        required
                                    />
                                </div>
                            </div>
                            <Button type="submit" className="w-full" disabled={isLoading}>
                                {isLoading ? (
                                    <>
                                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                        {t("forgotPassword.sending")}
                                    </>
                                ) : (
                                    t("forgotPassword.sendResetLink")
                                )}
                            </Button>
                            <div className="text-center">
                                <Link href="/login" className="text-sm text-muted-foreground hover:text-primary flex items-center justify-center gap-1">
                                    <ArrowLeft className="h-3 w-3" />
                                    {t("forgotPassword.backToLogin")}
                                </Link>
                            </div>
                        </form>
                    )}
                </CardContent>
            </Card>
        </div>
    );
}
