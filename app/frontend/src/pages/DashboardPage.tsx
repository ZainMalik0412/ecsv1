import { useQuery } from '@tanstack/react-query'
import { getDashboardStats } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Users, BookOpen, Calendar, ClipboardCheck, Activity, TrendingUp } from 'lucide-react'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  const cards = [
    {
      title: 'Total Students',
      value: stats?.total_students ?? 0,
      icon: <Users className="h-5 w-5 text-blue-500" />,
      show: ['admin', 'lecturer'].includes(user?.role || ''),
    },
    {
      title: 'Total Lecturers',
      value: stats?.total_lecturers ?? 0,
      icon: <Users className="h-5 w-5 text-purple-500" />,
      show: user?.role === 'admin',
    },
    {
      title: 'Total Modules',
      value: stats?.total_modules ?? 0,
      icon: <BookOpen className="h-5 w-5 text-green-500" />,
      show: true,
    },
    {
      title: 'Total Sessions',
      value: stats?.total_sessions ?? 0,
      icon: <Calendar className="h-5 w-5 text-orange-500" />,
      show: true,
    },
    {
      title: 'Active Sessions',
      value: stats?.active_sessions ?? 0,
      icon: <Activity className="h-5 w-5 text-red-500" />,
      show: true,
    },
    {
      title: 'Attendance Rate',
      value: `${stats?.attendance_rate ?? 0}%`,
      icon: <TrendingUp className="h-5 w-5 text-emerald-500" />,
      show: true,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground">
            Welcome back, {user?.full_name}
          </p>
        </div>
        <Badge variant="secondary" className="capitalize">
          {user?.role}
        </Badge>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 w-24 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-16 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {cards
            .filter((card) => card.show)
            .map((card) => (
              <Card key={card.title}>
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {card.title}
                  </CardTitle>
                  {card.icon}
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold">{card.value}</p>
                </CardContent>
              </Card>
            ))}
        </div>
      )}

      {user?.role === 'student' && (
        <div className="rounded-lg border bg-card p-6">
          <div className="flex items-start gap-4">
            <ClipboardCheck className="h-8 w-8 text-primary" />
            <div>
              <h3 className="font-semibold">Quick Actions</h3>
              <p className="text-sm text-muted-foreground">
                {user.has_face_registered
                  ? 'Your face is registered. You can mark attendance for active sessions.'
                  : 'Please register your face first to mark attendance.'}
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
