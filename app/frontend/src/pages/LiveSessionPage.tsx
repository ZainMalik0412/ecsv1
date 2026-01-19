import { useState, useRef, useCallback, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Webcam from 'react-webcam'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getLiveSessionState,
  getLiveAttendance,
  recognizeFrame,
  pauseSession,
  resumeSession,
  endSession,
} from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import { Progress } from '@/components/ui/progress'
import {
  Camera,
  Pause,
  Play,
  Square,
  CheckCircle,
  XCircle,
  Clock,
  Users,
  ArrowLeft,
  Loader2,
  AlertCircle,
} from 'lucide-react'

interface LiveSessionState {
  session_id: number
  status: 'scheduled' | 'active' | 'paused' | 'ended'
  title: string
  module_code: string
  module_name: string
  actual_start: string | null
  total_enrolled: number
  present_count: number
  late_count: number
  absent_count: number
}

interface LiveAttendanceStudent {
  student_id: number
  student_name: string
  username: string
  status: 'present' | 'absent' | 'late'
  marked_at: string | null
  face_confidence: number | null
  has_face_registered: boolean
}

interface RecognizedStudent {
  student_id: number
  student_name: string
  confidence: number
  status: 'present' | 'late'
  already_marked: boolean
}

const statusIcons = {
  present: <CheckCircle className="h-4 w-4 text-green-500" />,
  late: <Clock className="h-4 w-4 text-yellow-500" />,
  absent: <XCircle className="h-4 w-4 text-red-500" />,
}

const statusColors: Record<string, 'success' | 'warning' | 'destructive' | 'secondary'> = {
  present: 'success',
  late: 'warning',
  absent: 'destructive',
}

export default function LiveSessionPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const webcamRef = useRef<Webcam>(null)
  
  const [isRecognizing, setIsRecognizing] = useState(false)
  const [lastRecognized, setLastRecognized] = useState<RecognizedStudent[]>([])
  const [frameCount, setFrameCount] = useState(0)
  
  const sessionIdNum = parseInt(sessionId || '0')

  // Fetch session state
  const { data: sessionState, isLoading: stateLoading } = useQuery<LiveSessionState>({
    queryKey: ['live-session-state', sessionIdNum],
    queryFn: () => getLiveSessionState(sessionIdNum),
    refetchInterval: 3000, // Refresh every 3 seconds
    enabled: sessionIdNum > 0,
  })

  // Fetch attendance list
  const { data: attendanceData } = useQuery<{ session_id: number; students: LiveAttendanceStudent[] }>({
    queryKey: ['live-attendance', sessionIdNum],
    queryFn: () => getLiveAttendance(sessionIdNum),
    refetchInterval: 2000, // Refresh every 2 seconds
    enabled: sessionIdNum > 0,
  })

  // Recognition mutation
  const recognizeMutation = useMutation({
    mutationFn: (imageBase64: string) => recognizeFrame(sessionIdNum, imageBase64),
    onSuccess: (data) => {
      if (data.recognized_students && data.recognized_students.length > 0) {
        setLastRecognized(data.recognized_students)
        const newlyMarked = data.recognized_students.filter((s: RecognizedStudent) => !s.already_marked)
        if (newlyMarked.length > 0) {
          toast({
            title: `Recognized ${newlyMarked.length} student(s)`,
            description: newlyMarked.map((s: RecognizedStudent) => s.student_name).join(', '),
          })
        }
        queryClient.invalidateQueries({ queryKey: ['live-attendance', sessionIdNum] })
        queryClient.invalidateQueries({ queryKey: ['live-session-state', sessionIdNum] })
      }
      setFrameCount(prev => prev + 1)
    },
  })

  // Session control mutations
  const pauseMutation = useMutation({
    mutationFn: () => pauseSession(sessionIdNum),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live-session-state', sessionIdNum] })
      toast({ title: 'Recognition paused' })
    },
  })

  const resumeMutation = useMutation({
    mutationFn: () => resumeSession(sessionIdNum),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['live-session-state', sessionIdNum] })
      toast({ title: 'Recognition resumed' })
    },
  })

  const endMutation = useMutation({
    mutationFn: () => endSession(sessionIdNum),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({ title: 'Session ended' })
      navigate('/sessions')
    },
  })

  // Capture and recognize frame
  const captureAndRecognize = useCallback(() => {
    if (!webcamRef.current || recognizeMutation.isPending) return
    
    const imageSrc = webcamRef.current.getScreenshot()
    if (imageSrc) {
      recognizeMutation.mutate(imageSrc)
    }
  }, [recognizeMutation])

  // Auto-capture every 1.5 seconds when active and recognizing
  useEffect(() => {
    if (!isRecognizing || sessionState?.status !== 'active') return

    const interval = setInterval(captureAndRecognize, 1500)
    return () => clearInterval(interval)
  }, [isRecognizing, sessionState?.status, captureAndRecognize])

  if (stateLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!sessionState) {
    return (
      <div className="space-y-6">
        <Card className="p-8 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-4 font-semibold">Session not found</h3>
          <Button className="mt-4" onClick={() => navigate('/sessions')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Sessions
          </Button>
        </Card>
      </div>
    )
  }

  const attendedCount = sessionState.present_count + sessionState.late_count
  const attendanceRate = sessionState.total_enrolled > 0 
    ? Math.round((attendedCount / sessionState.total_enrolled) * 100) 
    : 0

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/sessions')}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{sessionState.title}</h1>
            <p className="text-muted-foreground">
              {sessionState.module_code} - {sessionState.module_name}
            </p>
          </div>
        </div>
        <Badge
          variant={
            sessionState.status === 'active' ? 'success' :
            sessionState.status === 'paused' ? 'warning' : 'secondary'
          }
          className="text-sm"
        >
          {sessionState.status.toUpperCase()}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Camera Feed */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Camera className="h-5 w-5" />
                Live Camera Feed
              </CardTitle>
              <div className="flex items-center gap-2">
                {sessionState.status === 'active' && (
                  <Button
                    variant={isRecognizing ? 'destructive' : 'default'}
                    size="sm"
                    onClick={() => setIsRecognizing(!isRecognizing)}
                  >
                    {isRecognizing ? (
                      <>
                        <Square className="mr-1 h-4 w-4" />
                        Stop Recognition
                      </>
                    ) : (
                      <>
                        <Play className="mr-1 h-4 w-4" />
                        Start Recognition
                      </>
                    )}
                  </Button>
                )}
              </div>
            </div>
            <CardDescription>
              {isRecognizing 
                ? `Processing frames... (${frameCount} processed)` 
                : 'Click Start Recognition to begin detecting faces'}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative aspect-video overflow-hidden rounded-lg bg-muted">
              <Webcam
                ref={webcamRef}
                audio={false}
                screenshotFormat="image/jpeg"
                videoConstraints={{ facingMode: 'user', width: 640, height: 480 }}
                className="h-full w-full object-cover"
              />
              {isRecognizing && sessionState.status === 'active' && (
                <div className="absolute top-2 right-2 flex items-center gap-2 rounded-full bg-red-500 px-3 py-1 text-xs text-white">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-white" />
                  LIVE
                </div>
              )}
              {sessionState.status === 'paused' && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <div className="text-center text-white">
                    <Pause className="mx-auto h-12 w-12" />
                    <p className="mt-2 font-medium">Recognition Paused</p>
                  </div>
                </div>
              )}
            </div>

            {/* Session Controls */}
            <div className="flex gap-2">
              {sessionState.status === 'active' && (
                <Button
                  variant="outline"
                  onClick={() => pauseMutation.mutate()}
                  disabled={pauseMutation.isPending}
                >
                  <Pause className="mr-2 h-4 w-4" />
                  Pause Session
                </Button>
              )}
              {sessionState.status === 'paused' && (
                <Button
                  onClick={() => resumeMutation.mutate()}
                  disabled={resumeMutation.isPending}
                >
                  <Play className="mr-2 h-4 w-4" />
                  Resume Session
                </Button>
              )}
              {(sessionState.status === 'active' || sessionState.status === 'paused') && (
                <Button
                  variant="destructive"
                  onClick={() => endMutation.mutate()}
                  disabled={endMutation.isPending}
                >
                  <Square className="mr-2 h-4 w-4" />
                  End Session
                </Button>
              )}
            </div>

            {/* Last Recognized */}
            {lastRecognized.length > 0 && (
              <div className="rounded-lg border bg-muted/50 p-4">
                <h4 className="font-medium mb-2">Last Recognized</h4>
                <div className="flex flex-wrap gap-2">
                  {lastRecognized.map((student) => (
                    <Badge
                      key={student.student_id}
                      variant={student.already_marked ? 'secondary' : 'success'}
                    >
                      {student.student_name}
                      <span className="ml-1 opacity-70">
                        ({Math.round(student.confidence * 100)}%)
                      </span>
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Attendance Stats & List */}
        <div className="space-y-6">
          {/* Stats */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2">
                <Users className="h-5 w-5" />
                Attendance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Attendance Rate</span>
                  <span className="font-medium">{attendanceRate}%</span>
                </div>
                <Progress value={attendanceRate} />
              </div>
              
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-lg bg-green-50 p-3 dark:bg-green-950">
                  <p className="text-2xl font-bold text-green-600">{sessionState.present_count}</p>
                  <p className="text-xs text-muted-foreground">Present</p>
                </div>
                <div className="rounded-lg bg-yellow-50 p-3 dark:bg-yellow-950">
                  <p className="text-2xl font-bold text-yellow-600">{sessionState.late_count}</p>
                  <p className="text-xs text-muted-foreground">Late</p>
                </div>
                <div className="rounded-lg bg-red-50 p-3 dark:bg-red-950">
                  <p className="text-2xl font-bold text-red-600">{sessionState.absent_count}</p>
                  <p className="text-xs text-muted-foreground">Absent</p>
                </div>
              </div>
              
              <p className="text-sm text-muted-foreground text-center">
                {attendedCount} of {sessionState.total_enrolled} students
              </p>
            </CardContent>
          </Card>

          {/* Student List */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Student List</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="max-h-[400px] overflow-y-auto space-y-2">
                {attendanceData?.students.map((student) => (
                  <div
                    key={student.student_id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex items-center gap-2">
                      {statusIcons[student.status]}
                      <div>
                        <p className="font-medium text-sm">{student.student_name}</p>
                        <p className="text-xs text-muted-foreground">@{student.username}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {!student.has_face_registered && (
                        <Badge variant="outline" className="text-xs">No Face</Badge>
                      )}
                      <Badge variant={statusColors[student.status]} className="text-xs">
                        {student.status}
                      </Badge>
                    </div>
                  </div>
                ))}
                {(!attendanceData?.students || attendanceData.students.length === 0) && (
                  <p className="text-sm text-muted-foreground text-center py-4">
                    No students enrolled
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
