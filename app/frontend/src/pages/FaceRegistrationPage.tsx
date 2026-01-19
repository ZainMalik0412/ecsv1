import { useState, useRef, useCallback } from 'react'
import Webcam from 'react-webcam'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { registerFace, clearFaceRegistrations } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/components/ui/use-toast'
import { Camera, Trash2, CheckCircle, RefreshCw } from 'lucide-react'

export default function FaceRegistrationPage() {
  const { user, fetchUser } = useAuthStore()
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const webcamRef = useRef<Webcam>(null)
  const [capturedImage, setCapturedImage] = useState<string | null>(null)

  const registerMutation = useMutation({
    mutationFn: registerFace,
    onSuccess: (data) => {
      if (data.success) {
        toast({ title: 'Face registered successfully', description: data.message })
        fetchUser()
        queryClient.invalidateQueries({ queryKey: ['auth-me'] })
        setCapturedImage(null)
      } else {
        toast({ variant: 'destructive', title: 'Registration failed', description: data.message })
      }
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to register face' })
    },
  })

  const clearMutation = useMutation({
    mutationFn: clearFaceRegistrations,
    onSuccess: () => {
      toast({ title: 'Face registrations cleared' })
      fetchUser()
      queryClient.invalidateQueries({ queryKey: ['auth-me'] })
    },
    onError: () => {
      toast({ variant: 'destructive', title: 'Failed to clear registrations' })
    },
  })

  const capture = useCallback(() => {
    const imageSrc = webcamRef.current?.getScreenshot()
    if (imageSrc) {
      setCapturedImage(imageSrc)
    }
  }, [])

  const handleRegister = () => {
    if (capturedImage) {
      registerMutation.mutate(capturedImage)
    }
  }

  const handleRetake = () => {
    setCapturedImage(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Face Registration</h1>
        <p className="text-muted-foreground">
          Register your face for attendance verification
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Camera className="h-5 w-5" />
              Capture Photo
            </CardTitle>
            <CardDescription>
              Position your face clearly in the frame and capture
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="relative aspect-video overflow-hidden rounded-lg bg-muted">
              {capturedImage ? (
                <img
                  src={capturedImage}
                  alt="Captured"
                  className="h-full w-full object-cover"
                />
              ) : (
                <Webcam
                  ref={webcamRef}
                  audio={false}
                  screenshotFormat="image/jpeg"
                  videoConstraints={{ facingMode: 'user' }}
                  className="h-full w-full object-cover"
                />
              )}
            </div>

            <div className="flex gap-2">
              {capturedImage ? (
                <>
                  <Button onClick={handleRetake} variant="outline" className="flex-1">
                    <RefreshCw className="mr-2 h-4 w-4" />
                    Retake
                  </Button>
                  <Button
                    onClick={handleRegister}
                    className="flex-1"
                    disabled={registerMutation.isPending}
                  >
                    {registerMutation.isPending ? 'Registering...' : 'Register Face'}
                  </Button>
                </>
              ) : (
                <Button onClick={capture} className="w-full">
                  <Camera className="mr-2 h-4 w-4" />
                  Capture Photo
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Registration Status</CardTitle>
            <CardDescription>
              Your current face registration status
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4 rounded-lg border p-4">
              {user?.has_face_registered ? (
                <>
                  <CheckCircle className="h-10 w-10 text-green-500" />
                  <div>
                    <p className="font-medium">Face Registered</p>
                    <p className="text-sm text-muted-foreground">
                      You can mark attendance using facial recognition
                    </p>
                  </div>
                </>
              ) : (
                <>
                  <Camera className="h-10 w-10 text-muted-foreground" />
                  <div>
                    <p className="font-medium">No Face Registered</p>
                    <p className="text-sm text-muted-foreground">
                      Please register your face to mark attendance
                    </p>
                  </div>
                </>
              )}
            </div>

            {user?.has_face_registered && (
              <Button
                variant="destructive"
                className="w-full"
                onClick={() => clearMutation.mutate()}
                disabled={clearMutation.isPending}
              >
                <Trash2 className="mr-2 h-4 w-4" />
                {clearMutation.isPending ? 'Clearing...' : 'Clear All Registrations'}
              </Button>
            )}

            <div className="rounded-lg bg-muted p-4">
              <h4 className="font-medium mb-2">Tips for best results:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>- Ensure good lighting on your face</li>
                <li>- Look directly at the camera</li>
                <li>- Remove glasses or hats if possible</li>
                <li>- Keep a neutral expression</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
