import { useQuery } from '@tanstack/react-query'
import { getUsers } from '@/lib/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Users, CheckCircle, XCircle, Camera } from 'lucide-react'

interface User {
  id: number
  username: string
  email: string | null
  full_name: string
  role: 'student' | 'lecturer' | 'admin'
  is_active: boolean
  has_face_registered: boolean
  created_at: string
}

const roleColors: Record<string, 'default' | 'secondary' | 'destructive'> = {
  student: 'default',
  lecturer: 'secondary',
  admin: 'destructive',
}

export default function UsersPage() {
  const { data: users, isLoading } = useQuery<User[]>({
    queryKey: ['users'],
    queryFn: () => getUsers(),
  })

  const getInitials = (name: string) => {
    return name
      .split(' ')
      .map((n) => n[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Users</h1>
        <p className="text-muted-foreground">
          Manage system users
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardContent className="p-4">
                <div className="flex items-center gap-4">
                  <div className="h-10 w-10 rounded-full bg-muted" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-24 rounded bg-muted" />
                    <div className="h-3 w-32 rounded bg-muted" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : users && users.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {users.map((user) => (
            <Card key={user.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-start gap-4">
                  <Avatar>
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      {getInitials(user.full_name)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-medium truncate">{user.full_name}</p>
                      {user.is_active ? (
                        <CheckCircle className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground truncate">
                      @{user.username}
                    </p>
                    {user.email && (
                      <p className="text-sm text-muted-foreground truncate">
                        {user.email}
                      </p>
                    )}
                    <div className="mt-2 flex items-center gap-2">
                      <Badge variant={roleColors[user.role]}>
                        {user.role}
                      </Badge>
                      {user.role === 'student' && (
                        <Badge variant={user.has_face_registered ? 'success' : 'outline'}>
                          <Camera className="mr-1 h-3 w-3" />
                          {user.has_face_registered ? 'Face' : 'No Face'}
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <Users className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No users found</h3>
          <p className="text-sm text-muted-foreground">
            No users have been created yet.
          </p>
        </Card>
      )}
    </div>
  )
}
