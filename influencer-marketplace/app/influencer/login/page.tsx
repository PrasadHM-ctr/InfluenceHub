import { AuthShell } from "@/components/auth/auth-shell";
import { SignInForm } from "@/components/auth/forms";
export default function InfluencerLoginPage() { return <AuthShell role="influencer" mode="login"><SignInForm role="influencer" /></AuthShell>; }
