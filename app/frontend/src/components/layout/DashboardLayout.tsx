import { Link, Outlet, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/stores/auth'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  LayoutDashboard,
  BookOpen,
  Calendar,
  ClipboardList,
  Users,
  Camera,
  ScanFace,
  LogOut,
  Menu,
  X,
  BarChart3,
  CalendarDays,
  AlertCircle,
} from 'lucide-react'
import { useState } from 'react'
import { cn } from '@/lib/utils'

interface NavItem {
  label: string
  path: string
  icon: React.ReactNode
  roles: string[]
}

const navItems: NavItem[] = [
  { label: 'Dashboard', path: '/', icon: <LayoutDashboard className="h-5 w-5" />, roles: ['student', 'lecturer', 'admin'] },
  { label: 'Calendar', path: '/calendar', icon: <CalendarDays className="h-5 w-5" />, roles: ['student', 'lecturer', 'admin'] },
  { label: 'Modules', path: '/modules', icon: <BookOpen className="h-5 w-5" />, roles: ['student', 'lecturer', 'admin'] },
  { label: 'Sessions', path: '/sessions', icon: <Calendar className="h-5 w-5" />, roles: ['student', 'lecturer', 'admin'] },
  { label: 'Attendance', path: '/attendance', icon: <ClipboardList className="h-5 w-5" />, roles: ['lecturer', 'admin'] },
  { label: 'My Stats', path: '/my-stats', icon: <BarChart3 className="h-5 w-5" />, roles: ['student'] },
  { label: 'Users', path: '/users', icon: <Users className="h-5 w-5" />, roles: ['admin'] },
  { label: 'Register Face', path: '/face-registration', icon: <Camera className="h-5 w-5" />, roles: ['student'] },
  { label: 'Mark Attendance', path: '/mark-attendance', icon: <ScanFace className="h-5 w-5" />, roles: ['student'] },
]

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const filteredNavItems = navItems.filter((item) => item.roles.includes(user?.role || ''))

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  const handleLogout = () => {
    logout()
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 transform bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Logo */}
          <div className="flex h-16 items-center justify-between px-4">
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <ScanFace className="h-5 w-5" />
              </div>
              <span className="text-lg font-semibold">AttendanceMS</span>
            </Link>
            <button
              className="lg:hidden"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <Separator className="bg-sidebar-accent" />

          {/* Navigation */}
          <nav className="flex-1 space-y-1 p-4">
            {filteredNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setSidebarOpen(false)}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  location.pathname === item.path
                    ? 'bg-sidebar-accent text-sidebar-foreground'
                    : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                )}
              >
                {item.icon}
                {item.label}
              </Link>
            ))}
          </nav>

          <Separator className="bg-sidebar-accent" />

          {/* User info */}
          <div className="p-4">
            <div className="flex items-center gap-3">
              <Avatar>
                <AvatarFallback className="bg-primary text-primary-foreground">
                  {getInitials(user?.full_name || 'U')}
                </AvatarFallback>
              </Avatar>
              <div className="flex-1 overflow-hidden">
                <p className="truncate text-sm font-medium">{user?.full_name}</p>
                <p className="truncate text-xs capitalize text-sidebar-foreground/70">
                  {user?.role}
                </p>
              </div>
            </div>
            <Button
              variant="ghost"
              className="mt-3 w-full justify-start text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground"
              onClick={handleLogout}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6">
          <button
            className="lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu className="h-6 w-6" />
          </button>
          <div className="flex-1" />
        </header>

        {/* Face registration prompt for students */}
        {user?.role === 'student' && !user?.has_face_registered && (
          <Alert variant="warning" className="mx-4 mt-4 lg:mx-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>
                You haven't registered your face yet. Face registration is required for attendance verification.
              </span>
              <Link to="/face-registration">
                <Button size="sm" variant="outline" className="ml-4">
                  <Camera className="mr-2 h-4 w-4" />
                  Register Now
                </Button>
              </Link>
            </AlertDescription>
          </Alert>
        )}

        {/* Page content */}
        <main className="flex-1 overflow-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
