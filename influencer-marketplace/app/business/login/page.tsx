import { AuthShell } from "@/components/auth/auth-shell";
import { SignInForm } from "@/components/auth/forms";
export default function BusinessLoginPage() { return <AuthShell role="business" mode="login"><SignInForm role="business" /></AuthShell>; }
