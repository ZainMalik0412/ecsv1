import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getAttendanceReport, exportAttendanceCsv, getModules, getSessions } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ClipboardList, Download, CheckCircle, XCircle, Clock, Filter, X } from 'lucide-react'
import { format } from 'date-fns'

interface AttendanceRow {
  student_id: number
  student_name: string
  student_username: string
  session_id: number
  session_title: string
  module_code: string
  module_name: string
  scheduled_start: string
  status: 'present' | 'absent' | 'late'
  marked_at: string | null
}

const statusIcons = {
  present: <CheckCircle className="h-4 w-4 text-green-500" />,
  late: <Clock className="h-4 w-4 text-yellow-500" />,
  absent: <XCircle className="h-4 w-4 text-red-500" />,
}

const statusColors: Record<string, 'success' | 'warning' | 'destructive'> = {
  present: 'success',
  late: 'warning',
  absent: 'destructive',
}

interface Module {
  id: number
  code: string
  name: string
}

interface Session {
  id: number
  title: string
  module_id: number
}

export default function AttendancePage() {
  const { toast } = useToast()
  const [moduleFilter, setModuleFilter] = useState<string>('')
  const [sessionFilter, setSessionFilter] = useState<string>('')
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [dateFrom, setDateFrom] = useState<string>('')
  const [dateTo, setDateTo] = useState<string>('')
  const [showFilters, setShowFilters] = useState(false)

  const { data: modules } = useQuery<Module[]>({
    queryKey: ['modules'],
    queryFn: getModules,
  })

  const { data: sessions } = useQuery<Session[]>({
    queryKey: ['sessions'],
    queryFn: () => getSessions(),
  })

  const { data: attendance, isLoading } = useQuery<AttendanceRow[]>({
    queryKey: ['attendance-report', moduleFilter, sessionFilter, statusFilter, dateFrom, dateTo],
    queryFn: () => getAttendanceReport({
      module_id: moduleFilter ? parseInt(moduleFilter) : undefined,
      session_id: sessionFilter ? parseInt(sessionFilter) : undefined,
      status: statusFilter || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    }),
  })

  const clearFilters = () => {
    setModuleFilter('')
    setSessionFilter('')
    setStatusFilter('')
    setDateFrom('')
    setDateTo('')
  }

  const hasFilters = moduleFilter || sessionFilter || statusFilter || dateFrom || dateTo

  const handleExport = async () => {
    try {
      const blob = await exportAttendanceCsv()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `attendance_report_${new Date().toISOString().split('T')[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast({ title: 'Report exported successfully' })
    } catch {
      toast({ variant: 'destructive', title: 'Failed to export report' })
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Attendance Records</h1>
          <p className="text-muted-foreground">
            View and export attendance data
          </p>
        </div>
        <div className="flex gap-2">
          <Button 
            onClick={() => setShowFilters(!showFilters)} 
            variant={hasFilters ? 'default' : 'outline'}
          >
            <Filter className="mr-2 h-4 w-4" />
            Filters {hasFilters && '•'}
          </Button>
          <Button onClick={handleExport} variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filter Controls */}
      {showFilters && (
        <Card>
          <CardContent className="pt-6">
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
              <div className="space-y-2">
                <Label>Module</Label>
                <Select value={moduleFilter} onValueChange={setModuleFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All modules" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All modules</SelectItem>
                    {modules?.map((m) => (
                      <SelectItem key={m.id} value={m.id.toString()}>
                        {m.code} - {m.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Session</Label>
                <Select value={sessionFilter} onValueChange={setSessionFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All sessions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All sessions</SelectItem>
                    {sessions?.filter(s => !moduleFilter || s.module_id === parseInt(moduleFilter)).map((s) => (
                      <SelectItem key={s.id} value={s.id.toString()}>
                        {s.title}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select value={statusFilter} onValueChange={setStatusFilter}>
                  <SelectTrigger>
                    <SelectValue placeholder="All statuses" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All statuses</SelectItem>
                    <SelectItem value="present">Present</SelectItem>
                    <SelectItem value="late">Late</SelectItem>
                    <SelectItem value="absent">Absent</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>From Date</Label>
                <Input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label>To Date</Label>
                <Input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                />
              </div>
            </div>

            {hasFilters && (
              <Button variant="ghost" className="mt-4" onClick={clearFilters}>
                <X className="mr-2 h-4 w-4" />
                Clear filters
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {isLoading ? (
        <Card className="animate-pulse">
          <CardContent className="p-6">
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 w-full rounded bg-muted" />
              ))}
            </div>
          </CardContent>
        </Card>
      ) : attendance && attendance.length > 0 ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b bg-muted/50">
                    <th className="px-4 py-3 text-left text-sm font-medium">Student</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Module</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Session</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Date</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                    <th className="px-4 py-3 text-left text-sm font-medium">Marked At</th>
                  </tr>
                </thead>
                <tbody>
                  {attendance.map((row, index) => (
                    <tr key={`${row.session_id}-${row.student_id}`} className={index % 2 === 0 ? 'bg-background' : 'bg-muted/30'}>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium">{row.student_name}</p>
                          <p className="text-sm text-muted-foreground">@{row.student_username}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant="outline">{row.module_code}</Badge>
                      </td>
                      <td className="px-4 py-3 text-sm">{row.session_title}</td>
                      <td className="px-4 py-3 text-sm">
                        {format(new Date(row.scheduled_start), 'PP')}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {statusIcons[row.status]}
                          <Badge variant={statusColors[row.status]}>
                            {row.status}
                          </Badge>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-muted-foreground">
                        {row.marked_at ? format(new Date(row.marked_at), 'Pp') : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card className="p-8 text-center">
          <ClipboardList className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No attendance records</h3>
          <p className="text-sm text-muted-foreground">
            No attendance has been recorded yet.
          </p>
        </Card>
      )}
    </div>
  )
}
