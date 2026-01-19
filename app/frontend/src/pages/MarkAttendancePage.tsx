import { useState, useRef, useCallback } from 'react'
import Webcam from 'react-webcam'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getSessions, verifyFaceAndMarkAttendance } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ScanFace, Camera, CheckCircle, XCircle, AlertCircle } from 'lucide-react'

interface Session {
  id: number
  module_id: number
  title: string
  scheduled_start: string
  scheduled_end: string
  status: string
}

export default function MarkAttendancePage() {
  const { user } = useAuthStore()
  const { toast } = useToast()
  const webcamRef = useRef<Webcam>(null)
  const [selectedSessionId, setSelectedSessionId] = useState<string>('')
  const [verificationResult, setVerificationResult] = useState<{
    success: boolean
    matched: boolean
    message: string
    confidence?: number
  } | null>(null)

  const { data: sessions } = useQuery<Session[]>({
    queryKey: ['sessions', 'active'],
    queryFn: () => getSessions({ status: 'active' }),
  })

  const verifyMutation = useMutation({
    mutationFn: ({ sessionId, image }: { sessionId: number; image: string }) =>
      verifyFaceAndMarkAttendance(sessionId, image),
    onSuccess: (data) => {
      setVerificationResult(data)
      if (data.matched) {
        toast({ title: 'Attendance marked!', description: data.message })
      } else {
        toast({ variant: 'destructive', title: 'Verification failed', description: data.message })
      }
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to verify face' })
    },
  })

  const handleVerify = useCallback(() => {
    if (!selectedSessionId) {
      toast({ variant: 'destructive', title: 'Please select a session' })
      return
    }
    const imageSrc = webcamRef.current?.getScreenshot()
    if (imageSrc) {
      setVerificationResult(null)
      verifyMutation.mutate({ sessionId: parseInt(selectedSessionId), image: imageSrc })
    }
  }, [selectedSessionId, verifyMutation, toast])

  if (!user?.has_face_registered) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">Mark Attendance</h1>
          <p className="text-muted-foreground">
            Use facial recognition to mark your attendance
          </p>
        </div>

        <Card className="p-8 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-yellow-500" />
          <h3 className="mt-4 font-semibold">Face Not Registered</h3>
          <p className="text-sm text-muted-foreground mt-2">
            You need to register your face before you can mark attendance.
            Please go to the Face Registration page first.
          </p>
          <Button className="mt-4" asChild>
            <a href="/face-registration">Register Face</a>
          </Button>
        </Card>
      </div>
    )
  }

  const activeSessions = sessions?.filter((s) => s.status === 'active') || []

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Mark Attendance</h1>
        <p className="text-muted-foreground">
          Use facial recognition to mark your attendance
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ScanFace className="h-5 w-5" />
              Face Verification
            </CardTitle>
            <CardDescription>
              Select a session and verify your face
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Select Active Session</label>
              <Select value={selectedSessionId} onValueChange={setSelectedSessionId}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Choose a session" />
                </SelectTrigger>
                <SelectContent>
                  {activeSessions.length > 0 ? (
                    activeSessions.map((session) => (
                      <SelectItem key={session.id} value={session.id.toString()}>
                        {session.title}
                      </SelectItem>
                    ))
                  ) : (
                    <SelectItem value="none" disabled>
                      No active sessions
                    </SelectItem>
                  )}
                </SelectContent>
              </Select>
            </div>

            <div className="relative aspect-video overflow-hidden rounded-lg bg-muted">
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: 'user' }}
                className="h-full w-full object-cover"
              />
            </div>

            <Button
              onClick={handleVerify}
              className="w-full"
              disabled={!selectedSessionId || verifyMutation.isPending || activeSessions.length === 0}
            >
              <Camera className="mr-2 h-4 w-4" />
              {verifyMutation.isPending ? 'Verifying...' : 'Verify & Mark Attendance'}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Verification Result</CardTitle>
            <CardDescription>
              Result of your face verification
            </CardDescription>
          </CardHeader>
          <CardContent>
            {verificationResult ? (
              <div className="space-y-4">
                <div className="flex items-center gap-4 rounded-lg border p-4">
                  {verificationResult.matched ? (
                    <CheckCircle className="h-10 w-10 text-green-500" />
                  ) : (
                    <XCircle className="h-10 w-10 text-red-500" />
                  )}
                  <div>
                    <p className="font-medium">
                      {verificationResult.matched ? 'Verification Successful' : 'Verification Failed'}
                    </p>
                    <p className="text-sm text-muted-foreground">
                      {verificationResult.message}
                    </p>
                  </div>
                </div>

                {verificationResult.confidence !== undefined && verificationResult.confidence !== null && (
                  <div className="rounded-lg bg-muted p-4">
                    <p className="text-sm font-medium">Confidence Score</p>
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 h-2 rounded-full bg-background">
                        <div
                          className="h-2 rounded-full bg-primary"
                          style={{ width: `${verificationResult.confidence * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">
                        {(verificationResult.confidence * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <ScanFace className="h-16 w-16 text-muted-foreground" />
                <p className="mt-4 text-muted-foreground">
                  Select a session and verify your face to see results
                </p>
              </div>
            )}

            {activeSessions.length === 0 && (
              <div className="mt-4 rounded-lg border border-yellow-200 bg-yellow-50 p-4">
                <p className="text-sm text-yellow-800">
                  <AlertCircle className="inline mr-2 h-4 w-4" />
                  No active sessions available for attendance marking.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
