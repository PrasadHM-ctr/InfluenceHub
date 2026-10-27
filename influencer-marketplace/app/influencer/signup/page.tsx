import { AuthShell } from "@/components/auth/auth-shell";
import { InfluencerRegistrationForm } from "@/components/auth/forms";
export default function InfluencerSignupPage() { return <AuthShell role="influencer" mode="signup"><InfluencerRegistrationForm /></AuthShell>; }
