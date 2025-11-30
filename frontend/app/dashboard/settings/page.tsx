'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { voiceAPI, businessAPI } from '@/lib/api';
import { Settings, Phone, Check, X, ChevronDown } from 'lucide-react';

export default function SettingsPage() {
  const [testMessage, setTestMessage] = useState("I want to make a reservation for dinner tonight");
  const [testResult, setTestResult] = useState<any>(null);
  const [testing, setTesting] = useState(false);
  const [businesses, setBusinesses] = useState<any[]>([]);
  const [selectedBusinessId, setSelectedBusinessId] = useState<string>('');
  const [loadingBusinesses, setLoadingBusinesses] = useState(true);

  useEffect(() => {
    const loadBusinesses = async () => {
      try {
        const response = await businessAPI.list();
        if (response.data && response.data.length > 0) {
          setBusinesses(response.data);
          setSelectedBusinessId(response.data[0].id);
        }
      } catch (error) {
        console.error('Error loading businesses:', error);
      } finally {
        setLoadingBusinesses(false);
      }
    };
    loadBusinesses();
  }, []);

  const runTestCall = async () => {
    if (!selectedBusinessId) {
      setTestResult({ error: 'No business selected. Create a business first.' });
      return;
    }

    const selectedBusiness = businesses.find(b => b.id === selectedBusinessId);
    if (!selectedBusiness || !selectedBusiness.phone_number) {
      setTestResult({ error: 'Selected business has no phone number.' });
      return;
    }

    setTesting(true);
    setTestResult(null);

    try {
      const response = await voiceAPI.simulateCall(selectedBusiness.phone_number, testMessage);
      setTestResult(response.data);
    } catch (error) {
      console.error('Test call error:', error);
      setTestResult({ error: 'Failed to simulate call. Make sure backend is running.' });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-500 mt-1">Configure your AI agent</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings className="h-5 w-5" />
            System Status
          </CardTitle>
          <CardDescription>Current configuration and feature status</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm">Backend API</span>
            <Badge variant="default" className="bg-green-500">
              <Check className="h-3 w-3 mr-1" /> Connected
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">OpenAI Integration</span>
            <Badge variant="secondary">
              <X className="h-3 w-3 mr-1" /> Mock Mode
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">Twilio Integration</span>
            <Badge variant="secondary">
              <X className="h-3 w-3 mr-1" /> Mock Mode
            </Badge>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm">ElevenLabs TTS</span>
            <Badge variant="secondary">
              <X className="h-3 w-3 mr-1" /> Mock Mode
            </Badge>
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700">
            💡 Mock mode is active - perfect for testing without spending money! 
            Add real API keys to .env when ready to go live.
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            Test Call Simulator
          </CardTitle>
          <CardDescription>
            Simulate a call to test your AI agent without using real phone services
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {loadingBusinesses ? (
            <div className="text-gray-500">Loading businesses...</div>
          ) : businesses.length === 0 ? (
            <div className="p-3 bg-yellow-50 rounded text-sm text-yellow-700">
              ⚠️ No businesses found. Create one first to test calls.
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="business-select">Select Business</Label>
                <div className="relative">
                  <select
                    id="business-select"
                    value={selectedBusinessId}
                    onChange={(e) => setSelectedBusinessId(e.target.value)}
                    className="w-full px-4 py-2.5 pr-10 border border-gray-300 rounded-lg bg-white text-gray-900 appearance-none cursor-pointer hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  >
                    {businesses.map((business) => (
                      <option key={business.id} value={business.id}>
                        {business.name} ({business.phone_number})
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-600 pointer-events-none" />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="test-message">Test Message</Label>
                <Input
                  id="test-message"
                  value={testMessage}
                  onChange={(e) => setTestMessage(e.target.value)}
                  placeholder="What would the caller say?"
                />
              </div>

              <Button onClick={runTestCall} disabled={testing}>
                {testing ? 'Testing...' : 'Run Test Call'}
              </Button>
            </>
          )}

          {testResult && (
            <div className="mt-4 border rounded-lg p-4 bg-gray-50">
              <h4 className="font-semibold mb-3">Test Result</h4>
              {testResult.error ? (
                <div className="text-red-600">{testResult.error}</div>
              ) : (
                <div className="space-y-3">
                  <div className="text-sm text-gray-600">
                    Call SID: <code className="bg-gray-200 px-2 py-1 rounded">{testResult.call_sid}</code>
                  </div>
                  {testResult.conversation?.map((msg: any, idx: number) => (
                    <div
                      key={idx}
                      className={`p-3 rounded ${
                        msg.role === 'user' ? 'bg-blue-100' : 'bg-white border'
                      }`}
                    >
                      <div className="text-xs font-semibold mb-1">
                        {msg.role === 'user' ? '👤 You' : '🤖 AI Agent'}
                      </div>
                      <div className="text-sm">{msg.content}</div>
                    </div>
                  ))}
                  <div className="mt-4 p-3 bg-green-50 rounded text-sm text-green-700">
                    ✅ Test call successful! Check the Calls page to see it in the log.
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Supported Languages</CardTitle>
          <CardDescription>Languages your AI agent can understand and speak</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            <Badge variant="default">🇺🇸 English</Badge>
            <Badge variant="default">🇪🇸 Spanish</Badge>
            <Badge variant="default">🇨🇳 Chinese</Badge>
            <Badge variant="default">🇫🇷 French</Badge>
            <Badge variant="default">🇷🇺 Russian</Badge>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
