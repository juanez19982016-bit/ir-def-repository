// ============================================================
// 📧 COMPLETE EMAIL SYSTEM — RESEND + REACT EMAIL
// ============================================================
// Production email system with beautiful templates.
// Includes: Welcome, Invoice, Password Reset, Notifications
// Time saved: ~15-20 hours
// ============================================================

// ============ FILE: lib/email.ts ============
import { Resend } from "resend";
import { WelcomeEmail } from "@/emails/welcome";
import { InvoiceEmail } from "@/emails/invoice";
import { PasswordResetEmail } from "@/emails/password-reset";
import { NotificationEmail } from "@/emails/notification";

const resend = new Resend(process.env.RESEND_API_KEY);

const FROM_EMAIL = "Your App <noreply@yourdomain.com>";

export const email = {
    // Send welcome email to new users
    async sendWelcome(to: string, name: string) {
        return resend.emails.send({
            from: FROM_EMAIL,
            to,
            subject: "Welcome to Your App! 🎉",
            react: WelcomeEmail({ name }),
        });
    },

    // Send invoice/receipt after payment
    async sendInvoice(to: string, data: {
        name: string;
        amount: number;
        plan: string;
        invoiceNumber: string;
        date: string;
    }) {
        return resend.emails.send({
            from: FROM_EMAIL,
            to,
            subject: `Invoice #${data.invoiceNumber} — $${data.amount}`,
            react: InvoiceEmail(data),
        });
    },

    // Send password reset link
    async sendPasswordReset(to: string, resetUrl: string) {
        return resend.emails.send({
            from: FROM_EMAIL,
            to,
            subject: "Reset your password",
            react: PasswordResetEmail({ resetUrl }),
        });
    },

    // Send generic notification
    async sendNotification(to: string, data: {
        title: string;
        message: string;
        actionUrl?: string;
        actionText?: string;
    }) {
        return resend.emails.send({
            from: FROM_EMAIL,
            to,
            subject: data.title,
            react: NotificationEmail(data),
        });
    },

    // Batch send (up to 100 emails at once)
    async sendBatch(emails: Array<{
        to: string;
        subject: string;
        html: string;
    }>) {
        return resend.batch.send(
            emails.map((e) => ({ from: FROM_EMAIL, ...e }))
        );
    },
};

// ============ FILE: emails/welcome.tsx ============
// React Email template — Welcome
import {
    Body, Container, Head, Heading, Hr, Html,
    Link, Preview, Section, Text, Button, Img,
} from "@react-email/components";

interface WelcomeEmailProps {
    name: string;
}

export function WelcomeEmail({ name = "there" }: WelcomeEmailProps) {
    return (
        <Html>
            <Head />
            <Preview>Welcome to Your App — Let&apos;s get started!</Preview>
            <Body style={main}>
                <Container style={container}>
                    <Heading style={h1}>Welcome, {name}! 🎉</Heading>
                    <Text style={text}>
                        Thanks for joining! We&apos;re excited to have you on board.
                        Here are a few things to get you started:
                    </Text>
                    <Section style={features}>
                        <Text style={featureItem}>✅ Complete your profile</Text>
                        <Text style={featureItem}>✅ Create your first project</Text>
                        <Text style={featureItem}>✅ Invite your team members</Text>
                        <Text style={featureItem}>✅ Connect your integrations</Text>
                    </Section>
                    <Button style={button} href="https://yourapp.com/dashboard">
                        Go to Dashboard →
                    </Button>
                    <Hr style={hr} />
                    <Text style={footer}>
                        Need help? Reply to this email or visit our{" "}
                        <Link href="https://yourapp.com/docs" style={link}>documentation</Link>.
                    </Text>
                </Container>
            </Body>
        </Html>
    );
}

// Styles
const main = { backgroundColor: "#0a0a0f", fontFamily: "Inter, Arial, sans-serif" };
const container = { margin: "0 auto", padding: "40px 20px", maxWidth: "560px" };
const h1 = { color: "#f0f0f5", fontSize: "28px", fontWeight: "800", margin: "0 0 20px" };
const text = { color: "#9ca3af", fontSize: "15px", lineHeight: "1.7" };
const features = { margin: "20px 0", padding: "20px", background: "rgba(255,255,255,0.03)", borderRadius: "12px" };
const featureItem = { color: "#d1d5db", fontSize: "14px", margin: "8px 0" };
const button = { backgroundColor: "#7c3aed", color: "#fff", padding: "14px 32px", borderRadius: "10px", fontSize: "15px", fontWeight: "600", textDecoration: "none", display: "inline-block", margin: "20px 0" };
const hr = { borderColor: "rgba(255,255,255,0.06)", margin: "30px 0" };
const footer = { color: "#6b7280", fontSize: "13px" };
const link = { color: "#7c3aed" };

// ============ FILE: emails/invoice.tsx ============
import {
    Body, Container, Head, Heading, Hr, Html,
    Preview, Section, Text, Row, Column,
} from "@react-email/components";

interface InvoiceEmailProps {
    name: string;
    amount: number;
    plan: string;
    invoiceNumber: string;
    date: string;
}

export function InvoiceEmail({ name, amount, plan, invoiceNumber, date }: InvoiceEmailProps) {
    return (
        <Html>
            <Head />
            <Preview>Invoice #{invoiceNumber} — ${amount}</Preview>
            <Body style={main}>
                <Container style={container}>
                    <Heading style={h1}>Payment Receipt 💳</Heading>
                    <Text style={text}>Hi {name}, this is your receipt for your recent payment.</Text>
                    <Section style={{ ...features, marginTop: "20px" }}>
                        <Row>
                            <Column><Text style={{ color: "#6b7280", fontSize: "13px" }}>Invoice</Text></Column>
                            <Column align="right"><Text style={{ color: "#f0f0f5", fontSize: "14px", fontWeight: "600" }}>#{invoiceNumber}</Text></Column>
                        </Row>
                        <Row>
                            <Column><Text style={{ color: "#6b7280", fontSize: "13px" }}>Date</Text></Column>
                            <Column align="right"><Text style={{ color: "#f0f0f5", fontSize: "14px" }}>{date}</Text></Column>
                        </Row>
                        <Row>
                            <Column><Text style={{ color: "#6b7280", fontSize: "13px" }}>Plan</Text></Column>
                            <Column align="right"><Text style={{ color: "#f0f0f5", fontSize: "14px" }}>{plan}</Text></Column>
                        </Row>
                        <Hr style={hr} />
                        <Row>
                            <Column><Text style={{ color: "#f0f0f5", fontSize: "16px", fontWeight: "700" }}>Total</Text></Column>
                            <Column align="right"><Text style={{ color: "#7c3aed", fontSize: "20px", fontWeight: "800" }}>${amount}</Text></Column>
                        </Row>
                    </Section>
                    <Text style={footer}>Questions about your bill? Reply to this email.</Text>
                </Container>
            </Body>
        </Html>
    );
}

// ============ FILE: emails/password-reset.tsx ============
import {
    Body, Container, Head, Heading, Html,
    Preview, Text, Button,
} from "@react-email/components";

interface PasswordResetEmailProps {
    resetUrl: string;
}

export function PasswordResetEmail({ resetUrl }: PasswordResetEmailProps) {
    return (
        <Html>
            <Head />
            <Preview>Reset your password — link expires in 1 hour</Preview>
            <Body style={main}>
                <Container style={container}>
                    <Heading style={h1}>Reset your password 🔒</Heading>
                    <Text style={text}>
                        We received a request to reset your password. Click the button below
                        to choose a new one. This link expires in 1 hour.
                    </Text>
                    <Button style={button} href={resetUrl}>
                        Reset Password →
                    </Button>
                    <Text style={{ ...text, fontSize: "13px", marginTop: "20px" }}>
                        If you didn&apos;t request this, you can safely ignore this email.
                        Your password won&apos;t be changed.
                    </Text>
                </Container>
            </Body>
        </Html>
    );
}
