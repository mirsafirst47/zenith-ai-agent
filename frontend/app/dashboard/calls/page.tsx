'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { dashboardAPI } from '@/lib/api';
import { useBusinessId } from '@/hooks/useBusinessId';
import { formatDuration, formatTimestamp, formatDateTime, getLanguageFlag, getLanguageName } from '@/lib/utils';
import { Phone, Eye } from 'lucide-react';

export default function CallsPage() {
  const { businessId } = useBusinessId();
  const [calls, setCalls] = useState<any[]>([]);
  const [selectedCall, setSelectedCall] = useState<any>(null);
  const [transcriptOpen, setTranscriptOpen] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (businessId) {
      loadCalls();
    }
  }, [businessId]);

  const loadCalls = async () => {
    if (!businessId) return;
    
    try {
      const response = await dashboardAPI.getRecentCalls(businessId, 100);
      setCalls(response.data || []);
    } catch (error) {
      console.error('Error loading calls:', error);
      setCalls([]);
    } finally {
      setLoading(false);
    }
  };

  const viewTranscript = async (call: any) => {
    try {
      const response = await dashboardAPI.getCallTranscript(call.id);
      setSelectedCall({ ...call, ...response.data });
      setTranscriptOpen(true);
    } catch (error) {
      console.error('Error loading transcript:', error);
      setSelectedCall({ ...call, transcript: [], summary: 'No transcript available' });
      setTranscriptOpen(true);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: any = {
      'completed': 'default',
      'in-progress': 'secondary',
      'failed': 'destructive',
    };
    return <Badge variant={variants[status] || 'outline'}>{status}</Badge>;
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Call History</h1>
          <p className="text-gray-500 mt-1">View all calls and transcripts</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Phone className="h-5 w-5" />
            All Calls ({calls.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div>Loading calls...</div>
          ) : calls.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Phone className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No calls yet. Make a test call to get started!</p>
              <p className="text-sm mt-2">Go to Settings to use the Test Call Simulator.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Caller</TableHead>
                    <TableHead>Language</TableHead>
                    <TableHead>Intent</TableHead>
                    <TableHead>Duration</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Time</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {calls.map((call) => (
                    <TableRow key={call.id}>
                      <TableCell className="font-medium">{call.caller_number}</TableCell>
                      <TableCell>
                        <span className="flex items-center gap-1">
                          {getLanguageFlag(call.detected_language)}
                          <span className="text-xs">{getLanguageName(call.detected_language)}</span>
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary">{call.intent || 'N/A'}</Badge>
                      </TableCell>
                      <TableCell>{formatDuration(call.duration_seconds)}</TableCell>
                      <TableCell>{getStatusBadge(call.status)}</TableCell>
                      <TableCell className="text-sm text-gray-500">
                        {formatTimestamp(call.started_at)}
                      </TableCell>
                      <TableCell>
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => viewTranscript(call)}
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={transcriptOpen} onOpenChange={setTranscriptOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Call Transcript</DialogTitle>
          </DialogHeader>
          {selectedCall && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm bg-gray-50 p-4 rounded-lg">
                <div><strong>Caller:</strong> {selectedCall.caller_number}</div>
                <div><strong>Language:</strong> {getLanguageFlag(selectedCall.detected_language)} {getLanguageName(selectedCall.detected_language)}</div>
                <div><strong>Intent:</strong> {selectedCall.intent || 'N/A'}</div>
                <div><strong>Duration:</strong> {formatDuration(selectedCall.duration_seconds)}</div>
                <div><strong>Status:</strong> {selectedCall.status}</div>
                <div><strong>Time:</strong> {formatDateTime(selectedCall.started_at)}</div>
              </div>

              <div className="border-t pt-4">
                <h4 className="font-semibold mb-3">Conversation</h4>
                {selectedCall.transcript && selectedCall.transcript.length > 0 ? (
                  <div className="space-y-3">
                    {selectedCall.transcript.map((msg: any, idx: number) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg ${
                          msg.role === 'user' ? 'bg-blue-50 ml-8' : 'bg-gray-50 mr-8'
                        }`}
                      >
                        <div className="text-xs font-semibold text-gray-600 mb-1">
                          {msg.role === 'user' ? '👤 Customer' : '🤖 AI Agent'}
                        </div>
                        <div className="text-sm">{msg.content}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    No transcript available for this call
                  </div>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
