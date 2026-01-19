import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getSessions, startSession, pauseSession, resumeSession, endSession } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Calendar, Play, Pause, Square, Clock, Video } from 'lucide-react'
import { format } from 'date-fns'

interface Session {
  id: number
  module_id: number
  title: string
  scheduled_start: string
  scheduled_end: string
  actual_start: string | null
  actual_end: string | null
  status: 'scheduled' | 'active' | 'paused' | 'ended'
  late_threshold_minutes: number
  created_at: string
}

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'secondary'> = {
  scheduled: 'secondary',
  active: 'success',
  paused: 'warning',
  ended: 'default',
}

export default function SessionsPage() {
  const { user } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const navigate = useNavigate()

  const { data: sessions, isLoading } = useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: () => getSessions(),
  })

  const startMutation = useMutation({
    mutationFn: startSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({ title: 'Session started' })
    },
    onError: () => toast({ variant: 'destructive', title: 'Failed to start session' }),
  })

  const pauseMutation = useMutation({
    mutationFn: pauseSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({ title: 'Session paused' })
    },
    onError: () => toast({ variant: 'destructive', title: 'Failed to pause session' }),
  })

  const resumeMutation = useMutation({
    mutationFn: resumeSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({ title: 'Session resumed' })
    },
    onError: () => toast({ variant: 'destructive', title: 'Failed to resume session' }),
  })

  const endMutation = useMutation({
    mutationFn: endSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({ title: 'Session ended' })
    },
    onError: () => toast({ variant: 'destructive', title: 'Failed to end session' }),
  })

  const canManageSessions = user?.role === 'lecturer' || user?.role === 'admin'

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Sessions</h1>
        <p className="text-muted-foreground">
          View and manage class sessions
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-5 w-32 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-48 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : sessions && sessions.length > 0 ? (
        <div className="space-y-4">
          {sessions.map((session) => (
            <Card key={session.id}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{session.title}</CardTitle>
                    <p className="text-sm text-muted-foreground flex items-center gap-1 mt-1">
                      <Clock className="h-4 w-4" />
                      {format(new Date(session.scheduled_start), 'PPp')}
                    </p>
                  </div>
                  <Badge variant={statusColors[session.status]}>
                    {session.status}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    Late threshold: {session.late_threshold_minutes} min
                  </p>
                  {canManageSessions && (
                    <div className="flex gap-2">
                      {session.status === 'scheduled' && (
                        <Button
                          size="sm"
                          onClick={() => startMutation.mutate(session.id)}
                          disabled={startMutation.isPending}
                        >
                          <Play className="mr-1 h-4 w-4" />
                          Start
                        </Button>
                      )}
                      {session.status === 'active' && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => navigate(`/live-session/${session.id}`)}
                          >
                            <Video className="mr-1 h-4 w-4" />
                            Live
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => pauseMutation.mutate(session.id)}
                            disabled={pauseMutation.isPending}
                          >
                            <Pause className="mr-1 h-4 w-4" />
                            Pause
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => endMutation.mutate(session.id)}
                            disabled={endMutation.isPending}
                          >
                            <Square className="mr-1 h-4 w-4" />
                            End
                          </Button>
                        </>
                      )}
                      {session.status === 'paused' && (
                        <>
                          <Button
                            size="sm"
                            onClick={() => resumeMutation.mutate(session.id)}
                            disabled={resumeMutation.isPending}
                          >
                            <Play className="mr-1 h-4 w-4" />
                            Resume
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => endMutation.mutate(session.id)}
                            disabled={endMutation.isPending}
                          >
                            <Square className="mr-1 h-4 w-4" />
                            End
                          </Button>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <Calendar className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No sessions found</h3>
          <p className="text-sm text-muted-foreground">
            No sessions have been scheduled yet.
          </p>
        </Card>
      )}
    </div>
  )
}
