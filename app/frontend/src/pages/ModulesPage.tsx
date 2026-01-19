import { useQuery } from '@tanstack/react-query'
import { getModules } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { BookOpen, Users } from 'lucide-react'

interface Module {
  id: number
  code: string
  name: string
  description: string | null
  lecturer_id: number | null
  created_at: string
}

export default function ModulesPage() {
  const { user } = useAuthStore()
  const { data: modules, isLoading } = useQuery<Module[]>({
    queryKey: ['modules'],
    queryFn: getModules,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Modules</h1>
        <p className="text-muted-foreground">
          {user?.role === 'student'
            ? 'Modules you are enrolled in'
            : user?.role === 'lecturer'
            ? 'Modules you teach'
            : 'All modules in the system'}
        </p>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-5 w-20 rounded bg-muted" />
                <div className="h-4 w-32 rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-4 w-full rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : modules && modules.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((module) => (
            <Card key={module.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <Badge variant="outline">{module.code}</Badge>
                  <BookOpen className="h-5 w-5 text-muted-foreground" />
                </div>
                <CardTitle className="text-lg">{module.name}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {module.description || 'No description available'}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center">
          <Users className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 font-semibold">No modules found</h3>
          <p className="text-sm text-muted-foreground">
            {user?.role === 'student'
              ? 'You are not enrolled in any modules yet.'
              : 'No modules have been created.'}
          </p>
        </Card>
      )}
    </div>
  )
}
