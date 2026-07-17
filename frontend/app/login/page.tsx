'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Phone, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import { authAPI, businessAPI } from '@/lib/api';

const BUSINESS_TYPES = [
  { value: 'mechanic', label: 'Auto Shop / Mechanic' },
  { value: 'salon', label: 'Salon / Spa' },
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'clinic', label: 'Clinic / Medical Office' },
  { value: 'other', label: 'Other' },
];

function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  return typeof detail === 'string' ? detail : fallback;
}

export default function LoginPage() {
  const router = useRouter();

  // Sign in state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Onboarding state
  const [bizName, setBizName] = useState('');
  const [bizPhone, setBizPhone] = useState('');
  const [bizType, setBizType] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');

  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await authAPI.login(email, password);
      authAPI.setToken(res.data.access_token);
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(errorDetail(err, 'Login failed. Is the backend running?'));
      setSubmitting(false);
    }
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!bizType) {
      setError('Please choose your business type.');
      return;
    }
    setSubmitting(true);
    try {
      // 1. Create the tenant
      const biz = await businessAPI.create({
        name: bizName,
        phone_number: bizPhone,
        business_type: bizType,
      });
      // 2. Register its first (admin) user
      const res = await authAPI.register(biz.data.id, regEmail, regPassword, regName || undefined);
      authAPI.setToken(res.data.access_token);
      router.push('/dashboard');
    } catch (err: unknown) {
      setError(errorDetail(err, 'Signup failed. Is the backend running?'));
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="flex items-center justify-center mb-6">
          <Phone className="h-10 w-10 text-blue-600" />
          <span className="ml-2 text-2xl font-bold text-gray-900">Zenith AI</span>
        </div>

        <Tabs defaultValue="signin" onValueChange={() => setError(null)}>
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="signin">Sign in</TabsTrigger>
            <TabsTrigger value="signup">Set up your business</TabsTrigger>
          </TabsList>

          <TabsContent value="signin">
            <Card>
              <CardHeader>
                <CardTitle>Welcome back</CardTitle>
                <CardDescription>Sign in to your business dashboard</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email" type="email" required autoComplete="email"
                      value={email} onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password" type="password" required autoComplete="current-password"
                      value={password} onChange={(e) => setPassword(e.target.value)}
                    />
                  </div>
                  {error && <p className="text-sm text-red-600">{error}</p>}
                  <Button type="submit" className="w-full" disabled={submitting}>
                    {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Sign in
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="signup">
            <Card>
              <CardHeader>
                <CardTitle>Set up your business</CardTitle>
                <CardDescription>
                  Create your business and its admin account in one step
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSignup} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="biz-name">Business name</Label>
                    <Input
                      id="biz-name" required placeholder="Joe's Garage"
                      value={bizName} onChange={(e) => setBizName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="biz-phone">Business phone number</Label>
                    <Input
                      id="biz-phone" required placeholder="+15551234567"
                      value={bizPhone} onChange={(e) => setBizPhone(e.target.value)}
                    />
                    <p className="text-xs text-gray-500">
                      The number your customers call — incoming calls route to your AI agent by this number.
                    </p>
                  </div>
                  <div className="space-y-2">
                    <Label>Business type</Label>
                    <Select value={bizType} onValueChange={setBizType}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a type" />
                      </SelectTrigger>
                      <SelectContent>
                        {BUSINESS_TYPES.map((t) => (
                          <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <hr />
                  <div className="space-y-2">
                    <Label htmlFor="reg-name">Your name</Label>
                    <Input
                      id="reg-name" placeholder="Optional"
                      value={regName} onChange={(e) => setRegName(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-email">Email</Label>
                    <Input
                      id="reg-email" type="email" required autoComplete="email"
                      value={regEmail} onChange={(e) => setRegEmail(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="reg-password">Password</Label>
                    <Input
                      id="reg-password" type="password" required minLength={8} autoComplete="new-password"
                      value={regPassword} onChange={(e) => setRegPassword(e.target.value)}
                    />
                  </div>
                  {error && <p className="text-sm text-red-600">{error}</p>}
                  <Button type="submit" className="w-full" disabled={submitting}>
                    {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Create account
                  </Button>
                </form>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
