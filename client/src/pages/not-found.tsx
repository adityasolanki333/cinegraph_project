import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertCircle, Home } from "lucide-react";
import { Link } from "wouter";
import { usePageMeta } from "@/hooks/usePageMeta";
import { useTranslation } from "react-i18next";

export default function NotFound() {
  const { t } = useTranslation();

  usePageMeta({
    title: t("notFound.title"),
    description: t("notFound.description"),
  });

  return (
    <div className="min-h-[60vh] w-full flex items-center justify-center">
      <Card className="w-full max-w-md mx-4">
        <CardContent className="pt-6 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-4" aria-hidden="true" />
          <h1 className="text-2xl font-bold mb-2">{t("notFound.title")}</h1>
          <p className="text-sm text-muted-foreground mb-6">
            {t("notFound.description")}
          </p>
          <Link href="/">
            <Button data-testid="button-go-home">
              <Home className="h-4 w-4 mr-2" aria-hidden="true" />
              {t("notFound.goHome")}
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
