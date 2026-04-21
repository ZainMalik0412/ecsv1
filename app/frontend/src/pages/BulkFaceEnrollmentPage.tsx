import { useState, useRef } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { getUsers, bulkEnrollFaces, clearUserFaces } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/components/ui/use-toast'
import {
  Upload,
  Trash2,
  CheckCircle2,
  XCircle,
  ImagePlus,
  User as UserIcon,
  Loader2,
  AlertCircle,
} from 'lucide-react'

interface User {
  id: number
  username: string
  full_name: string
  role: string
  has_face_registered: boolean
}

interface ImageItem {
  file: File
  preview: string
  base64: string
}

interface ImageResult {
  index: number
  success: boolean
  message: string
}

interface EnrollResponse {
  user_id: number
  username: string
  full_name: string
  enrolled: number
  failed: number
  total_encodings: number
  results: ImageResult[]
}

const MAX_IMAGES = 20
const MAX_FILE_SIZE_MB = 8

const readFileAsBase64 = (file: File): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })

export default function BulkFaceEnrollmentPage() {
  const { toast } = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [images, setImages] = useState<ImageItem[]>([])
  const [replaceExisting, setReplaceExisting] = useState(false)
  const [lastResult, setLastResult] = useState<EnrollResponse | null>(null)

  const { data: users, refetch: refetchUsers } = useQuery<User[]>({
    queryKey: ['users', 'all'],
    queryFn: () => getUsers(),
  })

  const selectableUsers = (users || []).filter(
    (u) => u.role === 'student' || u.role === 'lecturer'
  )

  const selectedUser = selectableUsers.find((u) => u.id === parseInt(selectedUserId))

  const enrollMutation = useMutation({
    mutationFn: bulkEnrollFaces,
    onSuccess: (data: EnrollResponse) => {
      setLastResult(data)
      refetchUsers()
      if (data.enrolled > 0) {
        toast({
          title: 'Bulk enrollment complete',
          description: `${data.enrolled} enrolled, ${data.failed} failed. Total stored: ${data.total_encodings}.`,
        })
        setImages([])
      } else {
        toast({
          variant: 'destructive',
          title: 'No faces enrolled',
          description: `${data.failed} image(s) failed. See results below.`,
        })
      }
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Bulk enrollment failed'
      toast({ variant: 'destructive', title: 'Error', description: message })
    },
  })

  const clearMutation = useMutation({
    mutationFn: clearUserFaces,
    onSuccess: (data: any) => {
      toast({ title: 'Cleared', description: data.message })
      refetchUsers()
      setLastResult(null)
    },
    onError: (error: any) => {
      const message = error?.response?.data?.detail || 'Failed to clear registrations'
      toast({ variant: 'destructive', title: 'Error', description: message })
    },
  })

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (!files || files.length === 0) return

    const remaining = MAX_IMAGES - images.length
    if (remaining <= 0) {
      toast({
        variant: 'destructive',
        title: 'Too many images',
        description: `Maximum is ${MAX_IMAGES} images per batch.`,
      })
      return
    }

    const filesArray = Array.from(files).slice(0, remaining)
    const newImages: ImageItem[] = []
    const rejected: string[] = []

    for (const file of filesArray) {
      if (!file.type.startsWith('image/')) {
        rejected.push(`${file.name}: not an image`)
        continue
      }
      if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        rejected.push(`${file.name}: exceeds ${MAX_FILE_SIZE_MB}MB`)
        continue
      }
      try {
        const base64 = await readFileAsBase64(file)
        newImages.push({ file, preview: base64, base64 })
      } catch (err) {
        rejected.push(`${file.name}: failed to read`)
      }
    }

    if (newImages.length > 0) {
      setImages((prev) => [...prev, ...newImages])
    }
    if (rejected.length > 0) {
      toast({
        variant: 'destructive',
        title: `${rejected.length} file(s) rejected`,
        description: rejected.slice(0, 3).join('; '),
      })
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const removeImage = (idx: number) => {
    setImages((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleEnroll = () => {
    if (!selectedUserId || images.length === 0) return
    enrollMutation.mutate({
      user_id: parseInt(selectedUserId),
      images_base64: images.map((img) => img.base64),
      replace_existing: replaceExisting,
    })
  }

  const handleClear = () => {
    if (!selectedUser) return
    if (!window.confirm(`Delete ALL face encodings for ${selectedUser.full_name}? This cannot be undone.`)) {
      return
    }
    clearMutation.mutate(selectedUser.id)
  }

  const canSubmit = selectedUserId && images.length > 0 && !enrollMutation.isPending

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Bulk Face Enrollment</h1>
        <p className="text-muted-foreground">
          Upload multiple images for a user and convert them into facial embeddings.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        {/* Left: User selection + options */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserIcon className="h-5 w-5" />
                Target User
              </CardTitle>
              <CardDescription>Pick the student or lecturer to enroll.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="user">User</Label>
                <select
                  id="user"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={selectedUserId}
                  onChange={(e) => {
                    setSelectedUserId(e.target.value)
                    setLastResult(null)
                  }}
                >
                  <option value="">Select a user...</option>
                  {selectableUsers.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.username}) - {u.role}
                      {u.has_face_registered ? ' ✓' : ''}
                    </option>
                  ))}
                </select>
              </div>

              {selectedUser && (
                <div className="rounded-lg border p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{selectedUser.full_name}</span>
                    {selectedUser.has_face_registered ? (
                      <Badge variant="success">Registered</Badge>
                    ) : (
                      <Badge variant="secondary">No face</Badge>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    @{selectedUser.username} · {selectedUser.role}
                  </p>
                  {selectedUser.has_face_registered && (
                    <Button
                      variant="destructive"
                      size="sm"
                      className="w-full"
                      onClick={handleClear}
                      disabled={clearMutation.isPending}
                    >
                      <Trash2 className="mr-2 h-4 w-4" />
                      {clearMutation.isPending ? 'Clearing...' : 'Clear all encodings'}
                    </Button>
                  )}
                </div>
              )}

              <div className="flex items-start gap-2 rounded-lg border p-3">
                <input
                  id="replace"
                  type="checkbox"
                  checked={replaceExisting}
                  onChange={(e) => setReplaceExisting(e.target.checked)}
                  className="mt-1"
                />
                <Label htmlFor="replace" className="cursor-pointer text-sm leading-snug">
                  <span className="font-medium">Replace existing encodings</span>
                  <span className="block text-xs text-muted-foreground">
                    Delete prior encodings for this user before enrolling the new batch.
                  </span>
                </Label>
              </div>
            </CardContent>
          </Card>

          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <AlertCircle className="h-4 w-4" />
                Image guidance
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-sm text-muted-foreground">
              <p>- Single person per image</p>
              <p>- Face clearly visible, reasonable lighting</p>
              <p>- Front-facing works best; slight angle variations are fine</p>
              <p>- 3-10 images per user gives the best matching</p>
              <p>- Max {MAX_IMAGES} images per batch, {MAX_FILE_SIZE_MB}MB each</p>
              <p>- JPG, PNG, or WEBP</p>
            </CardContent>
          </Card>
        </div>

        {/* Right: Upload area + results */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ImagePlus className="h-5 w-5" />
                Images
                <Badge variant="secondary" className="ml-auto">
                  {images.length} / {MAX_IMAGES}
                </Badge>
              </CardTitle>
              <CardDescription>
                Drop or pick face images. Each will be run through the face detector
                and converted into a 128-dimensional embedding.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                multiple
                onChange={handleFileChange}
                className="hidden"
                id="file-upload"
              />
              <label
                htmlFor="file-upload"
                className="flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-input bg-background px-6 py-10 text-center hover:bg-muted/50 transition-colors"
              >
                <Upload className="h-10 w-10 text-muted-foreground mb-2" />
                <p className="text-sm font-medium">Click to add images</p>
                <p className="text-xs text-muted-foreground mt-1">
                  You can select multiple files
                </p>
              </label>

              {images.length > 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                  {images.map((img, idx) => (
                    <div
                      key={idx}
                      className="group relative aspect-square overflow-hidden rounded-md border"
                    >
                      <img
                        src={img.preview}
                        alt={img.file.name}
                        className="h-full w-full object-cover"
                      />
                      <button
                        type="button"
                        onClick={() => removeImage(idx)}
                        className="absolute top-1 right-1 flex h-6 w-6 items-center justify-center rounded-full bg-destructive text-destructive-foreground opacity-0 group-hover:opacity-100 transition-opacity"
                        aria-label="Remove image"
                      >
                        <XCircle className="h-4 w-4" />
                      </button>
                      <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] px-1 py-0.5 truncate">
                        {img.file.name}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setImages([])}
                  disabled={images.length === 0 || enrollMutation.isPending}
                >
                  Clear
                </Button>
                <Button
                  className="flex-1"
                  onClick={handleEnroll}
                  disabled={!canSubmit}
                >
                  {enrollMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Enrolling...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Enroll {images.length} image{images.length === 1 ? '' : 's'}
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {lastResult && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  Last batch results
                  <Badge variant="success" className="ml-auto">
                    {lastResult.enrolled} enrolled
                  </Badge>
                  {lastResult.failed > 0 && (
                    <Badge variant="destructive">{lastResult.failed} failed</Badge>
                  )}
                </CardTitle>
                <CardDescription>
                  {lastResult.full_name} (@{lastResult.username}) now has {lastResult.total_encodings} encoding
                  {lastResult.total_encodings === 1 ? '' : 's'}.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-1">
                {lastResult.results.map((r) => (
                  <div
                    key={r.index}
                    className="flex items-center gap-2 text-sm rounded border px-3 py-2"
                  >
                    {r.success ? (
                      <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                    ) : (
                      <XCircle className="h-4 w-4 text-destructive shrink-0" />
                    )}
                    <span className="font-mono text-xs text-muted-foreground">
                      #{r.index + 1}
                    </span>
                    <span className="flex-1 truncate">{r.message}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
