import { AuthShell } from "@/components/auth/auth-shell";
import { BusinessRegistrationForm } from "@/components/auth/forms";
export default function BusinessSignupPage() { return <AuthShell role="business" mode="signup"><BusinessRegistrationForm /></AuthShell>; }
