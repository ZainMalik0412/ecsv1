import { useQuery } from '@tanstack/react-query'
import { getStudentStats } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart3, TrendingUp, CheckCircle, Clock, XCircle } from 'lucide-react'

interface ModuleStats {
  module_id: number
  module_code: string
  module_name: string
  total_sessions: number
  attended_sessions: number
  late_sessions: number
  absent_sessions: number
  attendance_rate: number
}

interface StudentStats {
  overall_rate: number
  total_sessions: number
  present_count: number
  late_count: number
  absent_count: number
  modules: ModuleStats[]
}

export default function StudentStatsPage() {
  const { data: stats, isLoading } = useQuery<StudentStats>({
    queryKey: ['student-stats'],
    queryFn: getStudentStats,
  })

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">My Attendance Statistics</h1>
          <p className="text-muted-foreground">Loading your attendance data...</p>
        </div>
        <div className="grid gap-4 md:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="pt-6">
                <div className="h-8 w-16 rounded bg-muted mb-2" />
                <div className="h-4 w-24 rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold">My Attendance Statistics</h1>
          <p className="text-muted-foreground">No attendance data available yet.</p>
        </div>
      </div>
    )
  }

  const getRateColor = (rate: number) => {
    if (rate >= 80) return 'text-green-600'
    if (rate >= 60) return 'text-yellow-600'
    return 'text-red-600'
  }

  const getRateBarColor = (rate: number) => {
    if (rate >= 80) return 'bg-green-500'
    if (rate >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">My Attendance Statistics</h1>
        <p className="text-muted-foreground">
          Track your attendance across all enrolled modules
        </p>
      </div>

      {/* Overall Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Rate</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-3xl font-bold ${getRateColor(stats.overall_rate)}`}>
              {stats.overall_rate}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.total_sessions} total sessions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Present</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{stats.present_count}</div>
            <p className="text-xs text-muted-foreground">
              On-time attendance
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Late</CardTitle>
            <Clock className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-yellow-600">{stats.late_count}</div>
            <p className="text-xs text-muted-foreground">
              Arrived after threshold
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Absent</CardTitle>
            <XCircle className="h-4 w-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-600">{stats.absent_count}</div>
            <p className="text-xs text-muted-foreground">
              Missed sessions
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" />
            Attendance Breakdown
          </CardTitle>
          <CardDescription>
            Visual representation of your attendance
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex h-8 overflow-hidden rounded-full bg-muted">
              {stats.total_sessions > 0 && (
                <>
                  <div
                    className="bg-green-500 transition-all"
                    style={{ width: `${(stats.present_count / stats.total_sessions) * 100}%` }}
                    title={`Present: ${stats.present_count}`}
                  />
                  <div
                    className="bg-yellow-500 transition-all"
                    style={{ width: `${(stats.late_count / stats.total_sessions) * 100}%` }}
                    title={`Late: ${stats.late_count}`}
                  />
                  <div
                    className="bg-red-500 transition-all"
                    style={{ width: `${(stats.absent_count / stats.total_sessions) * 100}%` }}
                    title={`Absent: ${stats.absent_count}`}
                  />
                </>
              )}
            </div>
            <div className="flex justify-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-green-500" />
                <span>Present ({stats.present_count})</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-yellow-500" />
                <span>Late ({stats.late_count})</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-500" />
                <span>Absent ({stats.absent_count})</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Per-Module Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Attendance by Module</CardTitle>
          <CardDescription>
            Your attendance rate for each enrolled module
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats.modules.length > 0 ? (
            <div className="space-y-6">
              {stats.modules.map((module) => (
                <div key={module.module_id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium">{module.module_name}</p>
                      <p className="text-sm text-muted-foreground">{module.module_code}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${getRateColor(module.attendance_rate)}`}>
                        {module.attendance_rate}%
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {module.attended_sessions}/{module.total_sessions} sessions
                      </p>
                    </div>
                  </div>
                  <div className="relative h-2 overflow-hidden rounded-full bg-muted">
                    <div
                      className={`absolute h-full transition-all ${getRateBarColor(module.attendance_rate)}`}
                      style={{ width: `${module.attendance_rate}%` }}
                    />
                  </div>
                  <div className="flex gap-4 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <CheckCircle className="h-3 w-3 text-green-500" />
                      {module.attended_sessions - module.late_sessions} present
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3 text-yellow-500" />
                      {module.late_sessions} late
                    </span>
                    <span className="flex items-center gap-1">
                      <XCircle className="h-3 w-3 text-red-500" />
                      {module.absent_sessions} absent
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <BarChart3 className="mx-auto h-10 w-10 mb-2" />
              <p>No module data available</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
