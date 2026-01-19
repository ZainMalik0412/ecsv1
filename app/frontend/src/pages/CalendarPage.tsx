import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getSessions } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Calendar, Clock, Play, ChevronLeft, ChevronRight } from 'lucide-react'
import { format, startOfMonth, endOfMonth, eachDayOfInterval, isToday, addMonths, subMonths } from 'date-fns'
import { useState } from 'react'

interface Session {
  id: number
  module_id: number
  title: string
  scheduled_start: string
  scheduled_end: string
  status: 'scheduled' | 'active' | 'paused' | 'ended'
  late_threshold_minutes: number
}

const statusColors: Record<string, 'default' | 'success' | 'warning' | 'secondary'> = {
  scheduled: 'secondary',
  active: 'success',
  paused: 'warning',
  ended: 'default',
}

export default function CalendarPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [currentMonth, setCurrentMonth] = useState(new Date())

  const { data: sessions, isLoading } = useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: () => getSessions(),
  })

  const monthStart = startOfMonth(currentMonth)
  const monthEnd = endOfMonth(currentMonth)
  const daysInMonth = eachDayOfInterval({ start: monthStart, end: monthEnd })

  // Group sessions by date
  const sessionsByDate = useMemo(() => {
    const map = new Map<string, Session[]>()
    sessions?.forEach((session) => {
      const dateKey = format(new Date(session.scheduled_start), 'yyyy-MM-dd')
      if (!map.has(dateKey)) {
        map.set(dateKey, [])
      }
      map.get(dateKey)!.push(session)
    })
    return map
  }, [sessions])

  // Get upcoming sessions
  const upcomingSessions = useMemo(() => {
    const now = new Date()
    return sessions
      ?.filter((s) => new Date(s.scheduled_start) >= now && s.status !== 'ended')
      .sort((a, b) => new Date(a.scheduled_start).getTime() - new Date(b.scheduled_start).getTime())
      .slice(0, 5) || []
  }, [sessions])

  const canManageSessions = user?.role === 'lecturer' || user?.role === 'admin'

  const handleGoToLiveSession = (sessionId: number) => {
    navigate(`/live-session/${sessionId}`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Calendar</h1>
        <p className="text-muted-foreground">
          {user?.role === 'student' 
            ? 'View your upcoming classes and sessions' 
            : 'View and manage your teaching schedule'}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Calendar Grid */}
        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                {format(currentMonth, 'MMMM yyyy')}
              </CardTitle>
              <div className="flex gap-1">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentMonth(subMonths(currentMonth, 1))}
                >
                  <ChevronLeft className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => setCurrentMonth(addMonths(currentMonth, 1))}
                >
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="grid grid-cols-7 gap-1">
                {Array.from({ length: 35 }).map((_, i) => (
                  <div key={i} className="aspect-square animate-pulse rounded bg-muted" />
                ))}
              </div>
            ) : (
              <>
                {/* Weekday headers */}
                <div className="grid grid-cols-7 gap-1 mb-1">
                  {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => (
                    <div key={day} className="text-center text-xs font-medium text-muted-foreground py-2">
                      {day}
                    </div>
                  ))}
                </div>
                
                {/* Calendar days */}
                <div className="grid grid-cols-7 gap-1">
                  {/* Empty cells for days before month start */}
                  {Array.from({ length: monthStart.getDay() }).map((_, i) => (
                    <div key={`empty-${i}`} className="aspect-square" />
                  ))}
                  
                  {daysInMonth.map((day) => {
                    const dateKey = format(day, 'yyyy-MM-dd')
                    const daySessions = sessionsByDate.get(dateKey) || []
                    
                    return (
                      <div
                        key={dateKey}
                        className={`
                          aspect-square rounded-lg border p-1 text-sm
                          ${isToday(day) ? 'border-primary bg-primary/5' : 'border-transparent'}
                          ${daySessions.length > 0 ? 'bg-muted/50' : ''}
                        `}
                      >
                        <div className={`text-center font-medium ${isToday(day) ? 'text-primary' : ''}`}>
                          {format(day, 'd')}
                        </div>
                        {daySessions.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-0.5 justify-center">
                            {daySessions.slice(0, 3).map((s) => (
                              <div
                                key={s.id}
                                className={`h-1.5 w-1.5 rounded-full ${
                                  s.status === 'active' ? 'bg-green-500 animate-pulse' :
                                  s.status === 'scheduled' ? 'bg-blue-500' : 'bg-gray-400'
                                }`}
                                title={s.title}
                              />
                            ))}
                            {daySessions.length > 3 && (
                              <span className="text-[8px] text-muted-foreground">+{daySessions.length - 3}</span>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        {/* Upcoming Sessions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              Upcoming Classes
            </CardTitle>
          </CardHeader>
          <CardContent>
            {upcomingSessions.length > 0 ? (
              <div className="space-y-3">
                {upcomingSessions.map((session) => (
                  <div
                    key={session.id}
                    className="rounded-lg border p-3 space-y-2"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-medium text-sm">{session.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(session.scheduled_start), 'EEE, MMM d')}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {format(new Date(session.scheduled_start), 'h:mm a')} - {format(new Date(session.scheduled_end), 'h:mm a')}
                        </p>
                      </div>
                      <Badge variant={statusColors[session.status]} className="text-xs">
                        {session.status}
                      </Badge>
                    </div>
                    
                    {canManageSessions && session.status === 'active' && (
                      <Button
                        size="sm"
                        className="w-full"
                        onClick={() => handleGoToLiveSession(session.id)}
                      >
                        <Play className="mr-1 h-3 w-3" />
                        Open Live Session
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Calendar className="mx-auto h-10 w-10 text-muted-foreground" />
                <p className="mt-2 text-sm text-muted-foreground">
                  No upcoming classes scheduled
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Today's Sessions */}
      {(() => {
        const todayKey = format(new Date(), 'yyyy-MM-dd')
        const todaySessions = sessionsByDate.get(todayKey) || []
        
        if (todaySessions.length === 0) return null
        
        return (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle>Today's Sessions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {todaySessions.map((session) => (
                  <div
                    key={session.id}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-medium">{session.title}</p>
                        <p className="text-sm text-muted-foreground">
                          {format(new Date(session.scheduled_start), 'h:mm a')} - {format(new Date(session.scheduled_end), 'h:mm a')}
                        </p>
                      </div>
                      <Badge variant={statusColors[session.status]}>
                        {session.status}
                      </Badge>
                    </div>
                    
                    {canManageSessions && (session.status === 'active' || session.status === 'paused') && (
                      <Button
                        className="w-full mt-2"
                        onClick={() => handleGoToLiveSession(session.id)}
                      >
                        <Play className="mr-2 h-4 w-4" />
                        {session.status === 'active' ? 'Open Live Session' : 'Resume Session'}
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )
      })()}
    </div>
  )
}
